from .models import Cart, CartItem
from .views import _cart_id


def cart_counter(request):
    cart_count = 0

    # Skip admin paths
    if "admin" in request.path:
        return {}

    try:
        if request.user.is_authenticated:
            cart = Cart.objects.get(user=request.user)
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))

        cart_items = CartItem.objects.filter(cart=cart, is_active=True)

        cart_count = sum(item.quantity for item in cart_items)

    except Cart.DoesNotExist:
        cart_count = 0

    return {"cart_count": cart_count}