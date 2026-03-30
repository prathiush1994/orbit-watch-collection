from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from store.models import ProductVariant
from .models import Cart, CartItem


# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────
CART_MAX_TOTAL  = 10   # Max total items (sum of all quantities) in one cart
PRODUCT_MAX_QTY = 3    # Max quantity of a single base-product across all its variants


# ─────────────────────────────────────────────
# Session helper
# ─────────────────────────────────────────────

def _cart_id(request):
    cart = request.session.session_key
    if not cart:
        request.session.create()
        cart = request.session.session_key
    return cart


def _get_cart(request):
    """
    Safe cart getter — uses filter().first() so duplicate Cart rows
    (which can happen from admin test data) never raise MultipleObjectsReturned.
    Returns the Cart instance or None.
    """
    return Cart.objects.filter(cart_id=_cart_id(request)).first()


def _get_or_create_cart(request):
    """Return the Cart for this session, creating one if needed."""
    cart_id = _cart_id(request)
    # filter().first() is safe even if duplicates exist
    cart = Cart.objects.filter(cart_id=cart_id).first()
    if cart is None:
        cart = Cart.objects.create(cart_id=cart_id)
    return cart


# ─────────────────────────────────────────────
# Cart page view
# ─────────────────────────────────────────────

def cart(request):
    total             = 0
    quantity          = 0
    cart_items        = []
    unavailable_items = []
    tax               = 0
    grand_total       = 0

    cart_obj = _get_cart(request)

    if cart_obj:
        all_items = CartItem.objects.filter(
            cart=cart_obj,
            is_active=True,
        ).select_related(
            'variant',
            'variant__product',
            'variant__product__brand',
        )

        for item in all_items:
            brand = item.variant.product.brand

            item.brand_unavailable = (brand and brand.status != 'active')
            item.out_of_stock      = (item.variant.stock <= 0)
            item.is_blocked        = item.brand_unavailable or item.out_of_stock

            if item.is_blocked:
                unavailable_items.append(item)
            else:
                total    += item.variant.price * item.quantity
                quantity += item.quantity

        cart_items  = all_items
        tax         = round((18 * total) / 100, 2)
        grand_total = round(total + tax, 2)

    has_unavailable = len(unavailable_items) > 0

    context = {
        'total'           : total,
        'quantity'        : quantity,
        'cart_items'      : cart_items,
        'tax'             : tax,
        'grand_total'     : grand_total,
        'has_unavailable' : has_unavailable,
    }
    return render(request, 'store/cart.html', context)


# ─────────────────────────────────────────────
# AJAX: update quantity (+1 / -1)
# ─────────────────────────────────────────────

@require_POST
def update_cart_quantity(request, variant_id):
    action  = request.POST.get('action')
    variant = get_object_or_404(ProductVariant, id=variant_id)

    if variant.product.brand and variant.product.brand.status != 'active':
        return JsonResponse({'status': 'error',
                             'message': 'This brand is currently unavailable.'}, status=400)

    if not variant.is_available:
        return JsonResponse({'status': 'error',
                             'message': 'This product is no longer listed.'}, status=400)

    cart_obj = _get_cart(request)
    if not cart_obj:
        return JsonResponse({'status': 'error', 'message': 'Cart not found.'}, status=404)

    try:
        cart_item = CartItem.objects.get(variant=variant, cart=cart_obj)
    except CartItem.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Item not in cart.'}, status=404)

    if action == 'increment':
        if variant.stock <= 0:
            return JsonResponse({'status': 'error',
                                 'message': 'This item is out of stock.'}, status=400)
        if cart_item.quantity >= variant.stock:
            return JsonResponse({'status': 'error',
                                 'message': f'Only {variant.stock} in stock.'}, status=400)

        all_items = CartItem.objects.filter(cart=cart_obj, is_active=True)
        total_qty = sum(ci.quantity for ci in all_items)
        if total_qty >= CART_MAX_TOTAL:
            return JsonResponse({'status': 'error',
                                 'message': f'Cart limit is {CART_MAX_TOTAL} items.'}, status=400)

        same_product_qty = sum(
            ci.quantity for ci in all_items
            if ci.variant.product_id == variant.product_id
        )
        if same_product_qty >= PRODUCT_MAX_QTY:
            return JsonResponse({'status': 'error',
                                 'message': f'Max {PRODUCT_MAX_QTY} of '
                                            f'"{variant.product.product_name}" allowed.'}, status=400)

        cart_item.quantity += 1
        cart_item.save()

    elif action == 'decrement':
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            cart_item.delete()
            totals = _calculate_totals(cart_obj)
            return JsonResponse({
                'status'          : 'ok',
                'action'          : 'removed',
                'message'         : 'Item removed from cart.',
                'new_qty'         : 0,
                'sub_total'       : 0,
                'total'           : totals['total'],
                'tax'             : totals['tax'],
                'grand_total'     : totals['grand_total'],
                'has_unavailable' : totals['has_unavailable'],
            })
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid action.'}, status=400)

    sub_total = variant.price * cart_item.quantity
    totals    = _calculate_totals(cart_obj)

    return JsonResponse({
        'status'          : 'ok',
        'action'          : action,
        'new_qty'         : cart_item.quantity,
        'sub_total'       : sub_total,
        'total'           : totals['total'],
        'tax'             : totals['tax'],
        'grand_total'     : totals['grand_total'],
        'has_unavailable' : totals['has_unavailable'],
    })


# ─────────────────────────────────────────────
# AJAX: remove entire item
# ─────────────────────────────────────────────

@require_POST
def remove_cartitem(request, variant_id):
    variant  = get_object_or_404(ProductVariant, id=variant_id)
    cart_obj = _get_cart(request)

    if cart_obj:
        CartItem.objects.filter(variant=variant, cart=cart_obj).delete()

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if is_ajax:
        totals = _calculate_totals(cart_obj) if cart_obj else {
            'total': 0, 'tax': 0, 'grand_total': 0, 'has_unavailable': False
        }
        return JsonResponse({
            'status'          : 'ok',
            'total'           : totals['total'],
            'tax'             : totals['tax'],
            'grand_total'     : totals['grand_total'],
            'has_unavailable' : totals['has_unavailable'],
        })
    return redirect('cart')


# ─────────────────────────────────────────────
# Non-AJAX add (from product detail page)
# ─────────────────────────────────────────────

def add_cart(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)

    if variant.product.brand and variant.product.brand.status != 'active':
        return redirect('store')
    if not variant.is_available:
        return redirect('store')
    if variant.stock <= 0:
        return redirect('store')

    cart_obj  = _get_or_create_cart(request)
    all_items = CartItem.objects.filter(cart=cart_obj, is_active=True)

    total_qty = sum(ci.quantity for ci in all_items)
    if total_qty >= CART_MAX_TOTAL:
        return redirect('cart')

    same_product_qty = sum(
        ci.quantity for ci in all_items
        if ci.variant.product_id == variant.product_id
    )
    if same_product_qty >= PRODUCT_MAX_QTY:
        return redirect('cart')

    try:
        cart_item = CartItem.objects.get(variant=variant, cart=cart_obj)
        if cart_item.quantity >= variant.stock:
            return redirect('cart')
        cart_item.quantity += 1
        cart_item.save()
    except CartItem.DoesNotExist:
        CartItem.objects.create(variant=variant, quantity=1, cart=cart_obj)

    return redirect('cart')


# ─────────────────────────────────────────────
# Non-AJAX decrement (legacy fallback)
# ─────────────────────────────────────────────

def remove_cart(request, variant_id):
    variant  = get_object_or_404(ProductVariant, id=variant_id)
    cart_obj = _get_cart(request)
    if not cart_obj:
        return redirect('cart')

    try:
        cart_item = CartItem.objects.get(variant=variant, cart=cart_obj)
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            cart_item.delete()
    except CartItem.DoesNotExist:
        pass
    return redirect('cart')


# ─────────────────────────────────────────────
# Internal helper: recalculate totals
# ─────────────────────────────────────────────

def _calculate_totals(cart_obj):
    total           = 0
    has_unavailable = False

    if not cart_obj:
        return {'total': 0, 'tax': 0, 'grand_total': 0, 'has_unavailable': False}

    items = CartItem.objects.filter(
        cart=cart_obj, is_active=True
    ).select_related('variant', 'variant__product', 'variant__product__brand')

    for item in items:
        brand     = item.variant.product.brand
        brand_bad = (brand and brand.status != 'active')
        stock_bad = (item.variant.stock <= 0)

        if brand_bad or stock_bad:
            has_unavailable = True
        else:
            total += item.variant.price * item.quantity

    tax         = round((18 * total) / 100, 2)
    grand_total = round(total + tax, 2)

    return {
        'total'          : total,
        'tax'            : tax,
        'grand_total'    : grand_total,
        'has_unavailable': has_unavailable,
    }