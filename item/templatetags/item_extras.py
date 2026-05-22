from django import template
from django.utils import timezone
from django.utils.timezone import is_aware, make_aware
import datetime

register = template.Library()


@register.filter
def is_new(value, days=30):
    """Return True if `value` (datetime or model) was created within `days` days.

    Accepts either a datetime or an object with a `created_at` (or `created_on`) attribute.
    """
    if not value:
        return False
    try:
        days = int(days)
    except Exception:
        days = 30

    # Grab a datetime from whatever the caller handed us
    created_at = None
    if isinstance(value, datetime.datetime):
        created_at = value
    else:
        # Try the usual Django timestamp field names
        for attr in ('created_at', 'created_on', 'created'):
            if hasattr(value, attr):
                created_at = getattr(value, attr)
                break

    if not created_at:
        return False

    # Make sure we're comparing apples to apples (both aware or both naive)
    now = timezone.now()
    if is_aware(now) and not is_aware(created_at):
        try:
            created_at = make_aware(created_at, timezone.get_default_timezone())
        except Exception:
            pass
    if not is_aware(now) and is_aware(created_at):
        try:
            now = timezone.make_naive(now, timezone.get_default_timezone())
        except Exception:
            pass

    try:
        delta = now - created_at
    except Exception:
        return False

    return getattr(delta, 'days', 0) <= days


@register.filter
def has_sale(item):
    """Quick template check — does this item look discounted?  Looks at
    flash-deal flags, explicit ``is_on_sale``, discount fields, and price
    comparisons."""
    if item is None:
        return False
    # Active flash deal takes priority
    if getattr(item, 'is_flash_discount_valid', False):
        return True
    # Explicit sale toggle
    if getattr(item, 'is_on_sale', False):
        return True
    # Any positive numeric discount
    discount = getattr(item, 'discount', None)
    if discount:
        try:
            return float(discount) > 0
        except Exception:
            pass
    # Sale price is genuinely lower than the list price
    sale_price = getattr(item, 'sale_price', None)
    price = getattr(item, 'price', None)
    if sale_price and price:
        try:
            return float(sale_price) < float(price)
        except Exception:
            pass
    return False


@register.filter
def sub(value, arg):
    """Subtract arg from value. Usage: {{ value|sub:arg }}"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0
