from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from store.models import ProductVariant
from .models import Wishlist
from carts.models import Cart, CartItem
from carts.views import _cart_id, _get_or_create_cart, PRODUCT_MAX_QTY


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

    cart = _get_or_create_cart(request)
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
    return render(request, 'store/wishlist.html', context)



def toggle_wishlist(request, variant_id):
    # Make sure the variant actually exists
    variant = get_object_or_404(ProductVariant, id=variant_id)

    if request.user.is_authenticated:
        # ── Logged-in user: use database ─────────────────
        item = Wishlist.objects.filter(user=request.user, variant=variant)
        if item.exists():
            item.delete()
            messages.success(request, 'Removed from wishlist.')
        else:
            Wishlist.objects.create(user=request.user, variant=variant)
            messages.success(request, 'Added to wishlist.')

    else:
        # ── Guest user: store in session ──────────────────
        pending = request.session.get('pending_wishlist', [])
        if variant_id in pending:
            pending.remove(variant_id)
            messages.success(request, 'Removed from wishlist.')
        else:
            pending.append(variant_id)
            messages.success(request, 'Added to wishlist. Login to save it permanently.')
        request.session['pending_wishlist'] = pending
        request.session.modified = True

    return redirect(request.META.get('HTTP_REFERER', 'store'))


# ─────────────────────────────────────────────
# Remove wishlist item
# ─────────────────────────────────────────────
@login_required(login_url='login')
def remove_wishlist(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    Wishlist.objects.filter(user=request.user, variant=variant).delete()
    messages.success(request, 'Removed from wishlist.')
    return redirect('wishlist')


# ─────────────────────────────────────────────
# Move wishlist → cart
# ─────────────────────────────────────────────
@login_required(login_url='login')
def add_to_cart_from_wishlist(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)

    def err(msg):
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
    if same_product_qty >= PRODUCT_MAX_QTY:
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

    messages.success(request, f'"{variant.product.product_name}" moved to your cart.')
    return redirect('cart')


def merge_wishlist(request):
    if not request.user.is_authenticated:
        return
    try:
        pending = request.session.pop('pending_wishlist', [])
        for variant_id in pending:
            Wishlist.objects.get_or_create(
                user       = request.user,
                variant_id = variant_id,
            )
        if pending:
            request.session.modified = True
    except Exception:
        pass   