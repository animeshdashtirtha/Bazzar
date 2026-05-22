from cart.models import Cart


def cart_count_processor(request):
    """Provides cart item count to all templates for the navbar badge."""
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.filter(user=request.user).first()
            if cart:
                return {'cart_count': cart.items.count()}
        except Cart.DoesNotExist:
            pass
    return {'cart_count': 0}