from .models import Cart, CartItem
from .views import _cart_id


def cart_counter(request):
    cart_count = 0

    # Skip cart counting on admin pages
    if 'admin' in request.path:
        return {}

    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
        cart_items = CartItem.objects.filter(cart=cart, is_active=True)
        for item in cart_items:
            cart_count += item.quantity
    except Cart.DoesNotExist:
        cart_count = 0

    return {'cart_count': cart_count}