from django.shortcuts import render, redirect
from store.models import ProductVariant
from carts.models import CartItem
from carts.views import _cart_id, _get_or_create_cart
from wishlist.models import Wishlist


def product_detail(request, category_slug, variant_slug):
    try:
        variant = ProductVariant.objects.select_related(
            'product', 'product__brand'
        ).get(slug=variant_slug, is_available=True)
    except ProductVariant.DoesNotExist:
        return redirect('store')

    if variant.product.brand and variant.product.brand.status != 'active':
        return redirect('store')

    active_cats = variant.product.category.filter(status='active')
    if not active_cats.exists():
        return redirect('store')

    gallery_images = variant.images.all()
    all_variants   = variant.get_all_variants()

    # ✅ cart
    cart = _get_or_create_cart(request)

    in_cart = CartItem.objects.filter(
        cart=cart,
        variant=variant,
        is_active=True
    ).exists()

    # ✅ wishlist
    in_wishlist = False
    if request.user.is_authenticated:
        in_wishlist = Wishlist.objects.filter(
            user=request.user,
            variant=variant
        ).exists()

    context = {
        'variant'        : variant,
        'product'        : variant.product,
        'gallery_images' : gallery_images,
        'all_variants'   : all_variants,
        'in_cart'        : in_cart,
        'in_wishlist'    : in_wishlist,
    }

    return render(request, 'store/product_detail.html', context)