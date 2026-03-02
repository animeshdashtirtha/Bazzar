from orders.models import Order, OrderItem
from decimal import Decimal

def create_order(user, cart_items):
    """
    cart_items = [
        { "item": item_instance, "quantity": 2 },
        ...
    ]
    """

    # 1️⃣ Calculate total
    total = sum(
        item["item"].price * item["quantity"]
        for item in cart_items
    )

    # 2️⃣ Create order (email triggers here)
    order = Order.objects.create(
        user=user,
        total_price=Decimal(total),
        status='pending'
    )

    # 3️⃣ Create order items
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
