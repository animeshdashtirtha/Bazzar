from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from item.models import item
from .models import Cart, CartItem
from django.contrib import messages
from orders.models import Order, OrderItem 

@login_required
def add_to_cart(request, item_id):
    product = get_object_or_404(item, id=item_id)
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, item=product)
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    return redirect('cart:view_cart')


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



def update_quantity(request, item_id):
    action = request.POST.get('action')

    #  FIX — filter by cart__user, not user
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

    total_price = sum(item.total() for item in cart_items)

    if request.method == "POST":
        # ✅ Create the order
        order = Order.objects.create(
            user=request.user,
            total_price=total_price,
        )

        # ✅ Create OrderItems for each cart item
        order_items = []
        for item in cart_items:
            order_items.append(OrderItem(
                order=order,
                item=item.item,
                quantity=item.quantity,
                price=item.item.price,
            ))
        OrderItem.objects.bulk_create(order_items)  # Faster & cleaner

        # ✅ Clear the cart after order is created
        cart_items.delete()

        messages.success(request, "Order placed successfully! You can track it in 'My Orders'.")
        return redirect('orders:my_orders')

    context = {
        'cart_items': cart_items,
        'total_price': total_price,
    }
    return render(request, 'cart/checkout.html', context)