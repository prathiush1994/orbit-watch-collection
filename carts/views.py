from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from store.models import ProductVariant
from .models import Cart, CartItem


CART_MAX_TOTAL  = 10
PRODUCT_MAX_QTY = 3


# ─────────────────────────────────────────────────────────
# SESSION / CART HELPERS
# ─────────────────────────────────────────────────────────
def _cart_id(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def _get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return cart
    else:
        cart_id = _cart_id(request)
        cart, _ = Cart.objects.get_or_create(cart_id=cart_id)
        return cart


def _get_effective_price(variant):
    """
    Returns the discounted price for a variant (or original if no offer).
    Keeps the offer logic in one place.
    """
    from offers.utils import get_applicable_offer, apply_discount
    try:
        pct, _, _ = get_applicable_offer(variant.product)
        return apply_discount(variant.price, pct), pct
    except Exception:
        return variant.price, 0


# ─────────────────────────────────────────────────────────
# CART PAGE
# ─────────────────────────────────────────────────────────
def cart(request):
    cart_obj = _get_or_create_cart(request)

    cart_items = CartItem.objects.filter(
        cart=cart_obj,
        is_active=True,
    ).select_related(
        'variant', 'variant__product', 'variant__product__brand'
    ).prefetch_related('variant__product__category')

    # Annotate items with offer data (batch)
    items_list = list(cart_items)
    from offers.utils import annotate_variants_with_offers
    annotate_variants_with_offers([item.variant for item in items_list])

    total           = 0
    quantity        = 0
    has_unavailable = False

    for item in items_list:
        if item.variant.stock <= 0:
            has_unavailable = True
            continue
        # Use effective_price (discounted) for totals
        total    += item.variant.effective_price * item.quantity
        quantity += item.quantity

    tax         = round((18 * total) / 100, 2)
    grand_total = round(total + tax, 2)

    context = {
        'cart_items'     : items_list,
        'total'          : total,
        'quantity'       : quantity,
        'tax'            : tax,
        'grand_total'    : grand_total,
        'has_unavailable': has_unavailable,
    }
    return render(request, 'store/cart.html', context)


# ─────────────────────────────────────────────────────────
# ADD TO CART
# ─────────────────────────────────────────────────────────
def add_cart(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)

    if variant.stock <= 0:
        messages.error(request, 'This item is out of stock.')
        return redirect(request.META.get('HTTP_REFERER', 'store'))

    cart       = _get_or_create_cart(request)
    cart_items = CartItem.objects.filter(cart=cart, is_active=True)

    total_qty = sum(item.quantity for item in cart_items)
    if total_qty >= CART_MAX_TOTAL:
        messages.error(request, 'Maximum 10 items allowed in cart.')
        return redirect(request.META.get('HTTP_REFERER', 'store'))

    same_product_qty = sum(
        item.quantity for item in cart_items
        if item.variant.product_id == variant.product_id
    )
    if same_product_qty >= PRODUCT_MAX_QTY:
        messages.error(request, 'Max 3 of the same product allowed.')
        return redirect(request.META.get('HTTP_REFERER', 'store'))

    try:
        cart_item = CartItem.objects.get(cart=cart, variant=variant)
        if cart_item.quantity >= variant.stock:
            messages.error(request, 'Stock limit reached.')
            return redirect(request.META.get('HTTP_REFERER', 'store'))
        cart_item.quantity += 1
        cart_item.save()
    except CartItem.DoesNotExist:
        CartItem.objects.create(cart=cart, variant=variant, quantity=1)

    return redirect(request.META.get('HTTP_REFERER', 'store'))


# ─────────────────────────────────────────────────────────
# INCREMENT / DECREMENT / REMOVE
# ─────────────────────────────────────────────────────────
def increment_cart(request, variant_id):
    cart      = _get_or_create_cart(request)
    cart_item = get_object_or_404(CartItem, cart=cart, variant_id=variant_id)

    if cart_item.variant.stock <= 0:
        messages.error(request, 'Out of stock.')
        return redirect('cart')

    all_items = CartItem.objects.filter(cart=cart, is_active=True)
    if sum(i.quantity for i in all_items) >= CART_MAX_TOTAL:
        messages.error(request, 'Maximum 10 items allowed.')
        return redirect('cart')

    same_product_qty = sum(
        i.quantity for i in all_items
        if i.variant.product_id == cart_item.variant.product_id
    )
    if same_product_qty >= PRODUCT_MAX_QTY:
        messages.error(request, 'Max 3 of the same product allowed.')
        return redirect('cart')

    if cart_item.quantity >= cart_item.variant.stock:
        messages.error(request, 'Stock limit reached.')
        return redirect('cart')

    cart_item.quantity += 1
    cart_item.save()
    return redirect('cart')


def decrement_cart(request, variant_id):
    cart      = _get_or_create_cart(request)
    cart_item = get_object_or_404(CartItem, cart=cart, variant_id=variant_id)
    if cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()
    return redirect('cart')


def remove_cartitem(request, variant_id):
    cart = _get_or_create_cart(request)
    CartItem.objects.filter(cart=cart, variant_id=variant_id).delete()
    return redirect('cart')


def remove_cart(request, variant_id):
    cart      = _get_or_create_cart(request)
    cart_item = CartItem.objects.filter(cart=cart, variant_id=variant_id).first()
    if cart_item and cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()
    return redirect('cart')


def merge_cart(request):
    if not request.user.is_authenticated:
        return
    try:
        session_key  = request.session.get('old_session_key') or request.session.session_key
        if not session_key:
            return
        session_cart = Cart.objects.filter(cart_id=session_key).first()
        if not session_cart:
            return
        user_cart, _ = Cart.objects.get_or_create(user=request.user)
        existing_total = sum(
            ci.quantity for ci in CartItem.objects.filter(cart=user_cart, is_active=True)
        )
        for item in CartItem.objects.filter(cart=session_cart, is_active=True):
            if existing_total >= CART_MAX_TOTAL:
                break
            user_item, created = CartItem.objects.get_or_create(
                cart=user_cart, variant=item.variant,
            )
            if not created:
                allowed_qty = min(
                    PRODUCT_MAX_QTY - user_item.quantity,
                    item.quantity,
                    CART_MAX_TOTAL - existing_total
                )
                if allowed_qty <= 0:
                    continue
                user_item.quantity += allowed_qty
            else:
                allowed_qty = min(
                    item.quantity, PRODUCT_MAX_QTY,
                    CART_MAX_TOTAL - existing_total
                )
                if allowed_qty <= 0:
                    continue
                user_item.quantity = allowed_qty
            user_item.save()
            existing_total += allowed_qty
        session_cart.delete()
        request.session.pop('old_session_key', None)
    except Exception:
        pass