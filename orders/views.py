from cart.models import Cart, CartItem
from django.contrib import messages
from django.shortcuts import render, redirect
from .models import Order, OrderItem 
from django.contrib.auth.decorators import login_required


@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'orders/my_orders.html', {'orders': orders})