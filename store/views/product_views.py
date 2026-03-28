from django.shortcuts import render, redirect
from store.models import ProductVariant
from carts.models import CartItem
from carts.views import _cart_id


def product_detail(request, category_slug, variant_slug):
    try:
        variant = ProductVariant.objects.select_related(
            'product', 'product__brand'
        ).get(slug=variant_slug, is_available=True)
    except ProductVariant.DoesNotExist:
        return redirect('store')

    # Redirect if brand or category is inactive
    if variant.product.brand and variant.product.brand.status != 'active':
        return redirect('store')

    active_cats = variant.product.category.filter(status='active')
    if not active_cats.exists():
        return redirect('store')

    gallery_images = variant.images.all()
    all_variants   = variant.get_all_variants()

    in_cart = CartItem.objects.filter(
        cart__cart_id=_cart_id(request),
        variant=variant
    ).exists()

    context = {
        'variant'        : variant,
        'product'        : variant.product,
        'gallery_images' : gallery_images,
        'all_variants'   : all_variants,
        'in_cart'        : in_cart,
    }
    return render(request, 'store/product_detail.html', context)