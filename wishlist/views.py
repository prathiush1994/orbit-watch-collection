from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages

from store.models import ProductVariant
from .models import Wishlist
from carts.models import Cart, CartItem
from carts.views import _cart_id


# ─────────────────────────────────────────────
# Safe cart helper (no MultipleObjectsReturned)
# ─────────────────────────────────────────────

def _get_or_create_cart(request):
    cart_id = _cart_id(request)
    cart    = Cart.objects.filter(cart_id=cart_id).first()
    if cart is None:
        cart = Cart.objects.create(cart_id=cart_id)
    return cart


# ─────────────────────────────────────────────
# Wishlist page
# ─────────────────────────────────────────────

@login_required(login_url='login')
def wishlist(request):
    items = Wishlist.objects.filter(user=request.user).select_related(
        'variant',
        'variant__product',
        'variant__product__brand',
    )

    cart             = _get_or_create_cart(request)
    cart_variant_ids = set(
        CartItem.objects.filter(cart=cart, is_active=True)
        .values_list('variant_id', flat=True)
    )

    for item in items:
        item.in_cart      = item.variant_id in cart_variant_ids
        item.out_of_stock = item.variant.stock <= 0
        item.unavailable  = (
            not item.variant.is_available or
            (item.variant.product.brand and
             item.variant.product.brand.status != 'active')
        )

    context = {'wishlist_items': items}

    # ── YOUR template lives at templates/store/wishlist.html ──────────────
    return render(request, 'store/wishlist.html', context)


# ─────────────────────────────────────────────
# Toggle (AJAX + non-AJAX)
# ─────────────────────────────────────────────

@login_required(login_url='login')
def toggle_wishlist(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    obj, created = Wishlist.objects.get_or_create(
        user=request.user, variant=variant
    )
    if not created:
        obj.delete()
        action = 'removed'
    else:
        action = 'added'

    if is_ajax:
        return JsonResponse({
            'status' : 'ok',
            'action' : action,
            'message': 'Added to wishlist' if action == 'added' else 'Removed from wishlist',
        })

    messages.success(request,
        'Added to wishlist.' if action == 'added' else 'Removed from wishlist.')
    return redirect(request.META.get('HTTP_REFERER', 'wishlist'))


# ─────────────────────────────────────────────
# Explicit remove
# ─────────────────────────────────────────────

@login_required(login_url='login')
def remove_wishlist(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    Wishlist.objects.filter(user=request.user, variant=variant).delete()

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if is_ajax:
        return JsonResponse({'status': 'ok', 'action': 'removed'})

    messages.success(request, 'Removed from wishlist.')
    return redirect('wishlist')


# ─────────────────────────────────────────────
# Move wishlist → cart
# ─────────────────────────────────────────────

@login_required(login_url='login')
def add_to_cart_from_wishlist(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    def err(msg):
        if is_ajax:
            return JsonResponse({'status': 'error', 'message': msg}, status=400)
        messages.error(request, msg)
        return redirect('wishlist')

    if variant.product.brand and variant.product.brand.status != 'active':
        return err('This brand is currently unavailable.')
    if not variant.is_available:
        return err('This product is currently unlisted.')
    if variant.stock <= 0:
        return err('This item is out of stock.')

    cart       = _get_or_create_cart(request)
    cart_items = CartItem.objects.filter(cart=cart, is_active=True)

    if sum(ci.quantity for ci in cart_items) >= 10:
        return err('You can only have 10 items in your cart at a time.')

    same_product_qty = sum(
        ci.quantity for ci in cart_items
        if ci.variant.product_id == variant.product_id
    )
    if same_product_qty >= 3:
        return err(f'You can only purchase 3 of "{variant.product.product_name}".')

    try:
        cart_item = CartItem.objects.get(variant=variant, cart=cart)
        if cart_item.quantity >= variant.stock:
            return err('Not enough stock available.')
        cart_item.quantity += 1
        cart_item.save()
    except CartItem.DoesNotExist:
        CartItem.objects.create(variant=variant, quantity=1, cart=cart)

    Wishlist.objects.filter(user=request.user, variant=variant).delete()

    msg = f'"{variant}" moved to your cart.'
    if is_ajax:
        return JsonResponse({'status': 'ok', 'message': msg})
    messages.success(request, msg)
    return redirect('cart')