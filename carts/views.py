from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from store.models import ProductVariant
from .models import Cart, CartItem


def _cart_id(request):
    cart = request.session.session_key
    if not cart:
        cart = request.session.create()
    return cart


def add_cart(request, variant_id):
    # Cart stores ProductVariant — not Product
    variant = get_object_or_404(ProductVariant, id=variant_id)

    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
    except Cart.DoesNotExist:
        cart = Cart.objects.create(cart_id=_cart_id(request))

    try:
        cart_item = CartItem.objects.get(variant=variant, cart=cart)
        cart_item.quantity += 1
        cart_item.save()
    except CartItem.DoesNotExist:
        CartItem.objects.create(
            variant=variant,
            quantity=1,
            cart=cart,
        )

    return redirect('cart')


def remove_cart(request, variant_id):
    cart    = get_object_or_404(Cart, cart_id=_cart_id(request))
    variant = get_object_or_404(ProductVariant, id=variant_id)

    try:
        cart_item = CartItem.objects.get(variant=variant, cart=cart)
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            cart_item.delete()
    except CartItem.DoesNotExist:
        pass

    return redirect('cart')


def remove_cartitem(request, variant_id):
    cart    = get_object_or_404(Cart, cart_id=_cart_id(request))
    variant = get_object_or_404(ProductVariant, id=variant_id)

    CartItem.objects.filter(variant=variant, cart=cart).delete()
    return redirect('cart')


def cart(request):
    total       = 0
    quantity    = 0
    cart_items  = []
    tax         = 0
    grand_total = 0

    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
        cart_items = CartItem.objects.filter(
            cart=cart,
            is_active=True
        ).select_related('variant', 'variant__product')

        for item in cart_items:
            total    += item.variant.price * item.quantity
            quantity += item.quantity

        tax         = round((18 * total) / 100, 2)
        grand_total = round(total + tax, 2)

    except ObjectDoesNotExist:
        cart_items = []

    context = {
        'total'      : total,
        'quantity'   : quantity,
        'cart_items' : cart_items,
        'tax'        : tax,
        'grand_total': grand_total,
    }
    return render(request, 'store/cart.html', context)