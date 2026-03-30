from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from store.models import ProductVariant
from .models import Cart, CartItem


# LIMITS
CART_MAX_TOTAL  = 10
PRODUCT_MAX_QTY = 3


# ─────────────────────────────
# SESSION CART
# ─────────────────────────────
def _cart_id(request):
    cart = request.session.session_key
    if not cart:
        request.session.create()
        cart = request.session.session_key
    return cart


def _get_or_create_cart(request):
    cart_id = _cart_id(request)
    cart = Cart.objects.filter(cart_id=cart_id).first()
    if not cart:
        cart = Cart.objects.create(cart_id=cart_id)
    return cart


# ─────────────────────────────
# CART PAGE
# ─────────────────────────────
def cart(request):
    cart = _get_or_create_cart(request)

    cart_items = CartItem.objects.filter(
        cart=cart,
        is_active=True
    ).select_related('variant', 'variant__product', 'variant__product__brand')

    total = 0
    quantity = 0
    has_unavailable = False

    for item in cart_items:
        if item.variant.stock <= 0:
            has_unavailable = True
            continue

        total += item.variant.price * item.quantity
        quantity += item.quantity

    tax = round((18 * total) / 100, 2)
    grand_total = round(total + tax, 2)

    context = {
        'cart_items': cart_items,
        'total': total,
        'quantity': quantity,
        'tax': tax,
        'grand_total': grand_total,
        'has_unavailable': has_unavailable,
    }

    return render(request, 'store/cart.html', context)


# ─────────────────────────────
# ADD TO CART (FIXED)
# ─────────────────────────────
def add_cart(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)

    if variant.stock <= 0:
        messages.error(request, "Out of stock")
        return redirect(request.META.get('HTTP_REFERER'))

    cart = _get_or_create_cart(request)
    cart_items = CartItem.objects.filter(cart=cart)

    # TOTAL LIMIT
    total_qty = sum(item.quantity for item in cart_items)
    if total_qty >= CART_MAX_TOTAL:
        messages.error(request, "Maximum 10 items allowed in cart")
        return redirect(request.META.get('HTTP_REFERER'))

    # PRODUCT LIMIT
    same_product_qty = sum(
        item.quantity for item in cart_items
        if item.variant.product_id == variant.product_id
    )
    if same_product_qty >= PRODUCT_MAX_QTY:
        messages.error(request, "Max 3 quantity per product")
        return redirect(request.META.get('HTTP_REFERER'))

    try:
        cart_item = CartItem.objects.get(cart=cart, variant=variant)

        if cart_item.quantity >= variant.stock:
            messages.error(request, "Stock limit reached")
            return redirect(request.META.get('HTTP_REFERER'))

        cart_item.quantity += 1
        cart_item.save()

    except CartItem.DoesNotExist:
        CartItem.objects.create(cart=cart, variant=variant, quantity=1)

    return redirect(request.META.get('HTTP_REFERER'))


# ─────────────────────────────
# INCREMENT
# ─────────────────────────────
def increment_cart(request, variant_id):
    cart = _get_or_create_cart(request)
    cart_item = get_object_or_404(CartItem, cart=cart, variant_id=variant_id)

    if cart_item.variant.stock <= 0:
        messages.error(request, "Out of stock")
        return redirect('cart')

    total_qty = sum(item.quantity for item in CartItem.objects.filter(cart=cart))
    if total_qty >= CART_MAX_TOTAL:
        messages.error(request, "Maximum 10 items allowed")
        return redirect('cart')

    same_product_qty = sum(
        item.quantity for item in CartItem.objects.filter(cart=cart)
        if item.variant.product_id == cart_item.variant.product_id
    )
    if same_product_qty >= PRODUCT_MAX_QTY:
        messages.error(request, "Max 3 quantity per product")
        return redirect('cart')

    if cart_item.quantity >= cart_item.variant.stock:
        messages.error(request, "Stock limit reached")
        return redirect('cart')

    cart_item.quantity += 1
    cart_item.save()

    return redirect('cart')


# ─────────────────────────────
# DECREMENT
# ─────────────────────────────
def decrement_cart(request, variant_id):
    cart = _get_or_create_cart(request)
    cart_item = get_object_or_404(CartItem, cart=cart, variant_id=variant_id)

    if cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()
    else:
        cart_item.delete()

    return redirect('cart')


# ─────────────────────────────
# REMOVE ONE
# ─────────────────────────────
def remove_cart(request, variant_id):
    cart = _get_or_create_cart(request)
    cart_item = CartItem.objects.filter(cart=cart, variant_id=variant_id).first()

    if cart_item:
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()

    return redirect('cart')


# ─────────────────────────────
# REMOVE FULL ITEM
# ─────────────────────────────
def remove_cartitem(request, variant_id):
    cart = _get_or_create_cart(request)
    CartItem.objects.filter(cart=cart, variant_id=variant_id).delete()
    return redirect('cart')