from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from item.models import item
from .models import Cart, CartItem
from django.contrib import messages
from orders.models import Order, OrderItem


def _add_item_to_cart(request, item_id, redirect_view_name):
    """Shared helper: add item to cart and redirect to the given view."""
    product = get_object_or_404(item, id=item_id)
    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, item=product)

    try:
        qty = int(request.GET.get('quantity', 1))
        qty = max(1, min(99, qty))
    except (ValueError, TypeError):
        qty = 1

    if not created:
        cart_item.quantity += qty
    else:
        cart_item.quantity = qty

    cart_item.save()
    return redirect(redirect_view_name)


@login_required
def add_to_cart(request, item_id):
    return _add_item_to_cart(request, item_id, 'cart:view_cart')


@login_required
def buy_now(request, item_id):
    return _add_item_to_cart(request, item_id, 'cart:checkout')


@login_required
def view_cart(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
    total_price = cart.total_price()
    return render(request, 'cart/view_cart.html', {'cart_items': cart_items, 'total_price': total_price})


@login_required
def remove_from_cart(request, item_id):
    cart = get_object_or_404(Cart, user=request.user)
    cart_item = get_object_or_404(CartItem, cart=cart, item_id=item_id)
    cart_item.delete()
    return redirect('cart:view_cart')


@login_required
def update_quantity(request, item_id):
    action = request.POST.get('action')
    cart_item = get_object_or_404(CartItem, item_id=item_id, cart__user=request.user)

    if action == 'increase':
        cart_item.quantity += 1
    elif action == 'decrease' and cart_item.quantity > 1:
        cart_item.quantity -= 1

    cart_item.save()
    return redirect('cart:view_cart')


@login_required
def checkout(request):
    try:
        cart = Cart.objects.get(user=request.user)
    except Cart.DoesNotExist:
        messages.warning(request, "Your cart is empty or missing.")
        return redirect('cart:view_cart')

    cart_items = CartItem.objects.filter(cart=cart)
    if not cart_items.exists():
        messages.warning(request, "Your cart is empty. Please add items before checkout.")
        return redirect('cart:view_cart')

    original_price = sum(item.total() for item in cart_items)
    discount = 0
    voucher_code = None
    voucher_message = None

    if request.method == "POST":
        action = request.POST.get('action')

        if action == 'apply_voucher':
            voucher_code = request.POST.get('voucher_code', '').strip().upper()

            valid_vouchers = {
                'BAZZAR10': 10,
                'SAVE20': 20,
                'WELCOME5': 5,
            }

            if voucher_code in valid_vouchers:
                discount_percent = valid_vouchers[voucher_code]
                discount = (original_price * discount_percent) / 100
                voucher_message = f"Voucher applied! {discount_percent}% discount"
                messages.success(request, voucher_message)
            else:
                voucher_message = "Invalid voucher code. No such voucher exists."
                messages.error(request, voucher_message)

            total_price = original_price - discount
        else:
            total_price = original_price - discount if discount else original_price
            order = Order.objects.create(
                user=request.user,
                total_price=total_price,
            )

            order_items = []
            for cart_item in cart_items:
                effective_price = cart_item.item.get_effective_price
                order_items.append(OrderItem(
                    order=order,
                    item=cart_item.item,
                    quantity=cart_item.quantity,
                    price=effective_price,
                ))
            OrderItem.objects.bulk_create(order_items)

            cart_items.delete()
            messages.success(request, "Order placed successfully! You can track it in 'My Orders'.")
            return redirect('orders:my_orders')
    else:
        total_price = original_price

    context = {
        'cart_items': cart_items,
        'total_price': total_price,
        'original_price': original_price,
        'discount': discount,
        'voucher_code': voucher_code,
    }
    return render(request, 'cart/checkout.html', context)