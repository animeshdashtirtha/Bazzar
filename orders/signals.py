from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Order
from .services.email_service import (
    send_order_received,
    send_order_confirmation,
    send_email_async
)


@receiver(pre_save, sender=Order)
def track_previous_status(sender, instance, **kwargs):
    if instance.pk:
        instance._previous_status = Order.objects.get(pk=instance.pk).status
    else:
        instance._previous_status = None


@receiver(post_save, sender=Order)
def order_email_handler(sender, instance, created, **kwargs):

    # ✅ ORDER RECEIVED (on creation)
    if created:
        send_email_async(
            send_order_received,
            instance.user.email,
            instance
        )

    # ✅ ORDER CONFIRMED (status change)
    if (
        not created and
        instance._previous_status == 'pending' and
        instance.status == 'processing'
    ):
        send_email_async(
            send_order_confirmation,
            instance.user.email,
            instance
        )
