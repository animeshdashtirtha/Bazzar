from orders.models import Order, OrderItem
from decimal import Decimal


def create_order(user, cart_items):
    """Build an Order (and its line items) from a list of item/quantity dicts,
    using each item's current effective price so flash discounts are honoured."""
    total = sum(
        item["item"].get_effective_price * item["quantity"]
        for item in cart_items
    )

    order = Order.objects.create(
        user=user,
        total_price=Decimal(str(total)),
        status='pending'
    )

    OrderItem.objects.bulk_create([
        OrderItem(
            order=order,
            item=ci["item"],
            quantity=ci["quantity"],
            price=ci["item"].get_effective_price
        )
        for ci in cart_items
    ])

    return order
