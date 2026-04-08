from .models import Wishlist

def wishlist_counter(request):
    if 'admin' in request.path:
        return {}

    wishlist_count = 0
    if request.user.is_authenticated:
        wishlist_count = Wishlist.objects.filter(user=request.user).count()

    return {'wishlist_count': wishlist_count}