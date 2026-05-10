from orders.models import Order, OrderItem
from decimal import Decimal

def create_order(user, cart_items):
    """
    cart_items = [
        { "item": item_instance, "quantity": 2 },
        ...
    ]
    """

    total = sum(
        item["item"].price * item["quantity"]
        for item in cart_items
    )

    order = Order.objects.create(
        user=user,
        total_price=Decimal(total),
        status='pending'
    )

    OrderItem.objects.bulk_create([
        OrderItem(
            order=order,
            item=ci["item"],
            quantity=ci["quantity"],
            price=ci["item"].price
        )
        for ci in cart_items
    ])

    return order
