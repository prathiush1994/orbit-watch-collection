from .models import Wishlist, WishlistItem
from .views import _get_or_create_wishlist


def wishlist_counter(request):
    if "admin" in request.path:
        return {}
    try:
        wishlist = _get_or_create_wishlist(request)

        wishlist_count = WishlistItem.objects.filter(
            wishlist=wishlist
        ).count()

    except Exception:
        wishlist_count = 0

    return {"wishlist_count": wishlist_count}