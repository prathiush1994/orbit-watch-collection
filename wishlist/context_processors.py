from .models import Wishlist


def wishlist_counter(request):
    """
    Makes {{ wishlist_count }} available in every template.

    ── Setup (one-time) ────────────────────────────────────────────────────
    In settings.py, inside TEMPLATES[0]['OPTIONS']['context_processors'],
    add this line:

        'wishlist.context_processors.wishlist_counter',

    It should look like:
        'context_processors': [
            'django.template.context_processors.debug',
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
            'carts.context_processors.cart_counter',       # your existing one
            'wishlist.context_processors.wishlist_counter', # ← ADD THIS
        ],
    ────────────────────────────────────────────────────────────────────────
    """
    if 'admin' in request.path:
        return {}

    wishlist_count = 0
    if request.user.is_authenticated:
        wishlist_count = Wishlist.objects.filter(user=request.user).count()

    return {'wishlist_count': wishlist_count}