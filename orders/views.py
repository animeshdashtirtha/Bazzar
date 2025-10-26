from cart.models import Cart, CartItem
from django.contrib import messages
from django.shortcuts import render, redirect
from .models import Order, OrderItem 
from django.contrib.auth.decorators import login_required

@login_required
def checkout(request):
    cart_items = CartItem.objects.filter(cart__user=request.user)
    cart = Cart.objects.get(user=request.user)
    total_price = sum(item.total() for item in cart_items)

    if not cart_items:
        messages.warning(request, "Your cart is empty. Please add items before checkout.")
        return redirect('cart:view_cart')

    if request.method == "POST":
        # ✅ Create Order
        order = Order.objects.create(
            user=request.user,
            total_price=total_price,
        )

        # ✅ Create OrderItems
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                item=item.item,
                quantity=item.quantity,
                price=item.item.price,
            )

        # ✅ Clear Cart
        cart_items.delete()
        messages.success(request, "Order placed successfully! You can track it in 'My Orders'.")
        return redirect('orders:my_orders')

    context = {
        'cart_items': cart_items,
        'total_price': total_price,
    }
    return render(request, 'cart/checkout.html', context)


@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'orders/my_orders.html', {'orders': orders})