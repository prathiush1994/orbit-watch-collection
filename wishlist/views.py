from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from store.models import ProductVariant
from .models import Wishlist, WishlistItem
from carts.models import CartItem
from carts.views import _get_or_create_cart, PRODUCT_MAX_QTY


def _wishlist_id(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def _get_or_create_wishlist(request):
    if request.user.is_authenticated:
        user_wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
        session_key = _wishlist_id(request)
        if not request.session.get("wishlist_merged", False):
            session_wishlist = Wishlist.objects.filter(
                wishlist_id=session_key, user__isnull=True
            ).first()
            if session_wishlist:
                for item in WishlistItem.objects.filter(wishlist=session_wishlist):
                    WishlistItem.objects.get_or_create(
                        wishlist=user_wishlist,
                        variant=item.variant,
                    )
                session_wishlist.delete()
                request.session["wishlist_merged"] = True
        return user_wishlist
    return Wishlist.objects.get_or_create(wishlist_id=_wishlist_id(request))[0]


def wishlist(request):
    wishlist = _get_or_create_wishlist(request)
    items = WishlistItem.objects.filter(wishlist=wishlist).select_related(
        "variant",
        "variant__product",
        "variant__product__brand",
    )
    cart = _get_or_create_cart(request)
    cart_variant_ids = set(
        CartItem.objects.filter(cart=cart, is_active=True)
        .values_list("variant_id", flat=True)
    )
    for item in items:
        item.in_cart = item.variant_id in cart_variant_ids
        item.out_of_stock = item.variant.stock <= 0
        item.unavailable = not item.variant.is_available or (
            item.variant.product.brand
            and item.variant.product.brand.status != "active"
        )
    return render(request, "store/wishlist.html", {"wishlist_items": items})


def toggle_wishlist(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    wishlist = _get_or_create_wishlist(request)
    cart = _get_or_create_cart(request)
    if CartItem.objects.filter(cart=cart, variant=variant, is_active=True).exists():
        messages.warning(request, "Already in cart")
        return redirect(request.GET.get("next", "store"))
    item = WishlistItem.objects.filter(wishlist=wishlist, variant=variant)
    if item.exists():
        item.delete()
    else:
        WishlistItem.objects.create(wishlist=wishlist, variant=variant)
    next_url = request.GET.get("next")
    return redirect(next_url if next_url else request.META.get("HTTP_REFERER", "store"))


def remove_wishlist(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    wishlist = _get_or_create_wishlist(request)
    WishlistItem.objects.filter(
        wishlist=wishlist,
        variant=variant
    ).delete()
    messages.success(request, "Removed from wishlist.")
    return redirect("wishlist")


@login_required(login_url="login")
def add_to_cart_from_wishlist(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)

    def err(msg):
        messages.error(request, msg)
        return redirect("wishlist")

    if variant.product.brand and variant.product.brand.status != "active":
        return err("This brand is currently unavailable.")

    if not variant.is_available:
        return err("This product is currently unlisted.")

    if variant.stock <= 0:
        return err("This item is out of stock.")

    cart = _get_or_create_cart(request)
    cart_items = CartItem.objects.filter(cart=cart, is_active=True)

    if sum(ci.quantity for ci in cart_items) >= 10:
        return err("You can only have 10 items in your cart at a time.")

    same_product_qty = sum(
        ci.quantity for ci in cart_items
        if ci.variant.product_id == variant.product_id
    )

    if same_product_qty >= PRODUCT_MAX_QTY:
        return err(f'You can only purchase 3 of "{variant.product.product_name}".')

    try:
        cart_item = CartItem.objects.get(variant=variant, cart=cart)

        if cart_item.quantity >= variant.stock:
            return err("Not enough stock available.")

        cart_item.quantity += 1
        cart_item.save()

    except CartItem.DoesNotExist:
        CartItem.objects.create(variant=variant, quantity=1, cart=cart)

    wishlist = _get_or_create_wishlist(request)

    WishlistItem.objects.filter(
        wishlist=wishlist,
        variant=variant
    ).delete()

    messages.success(
        request,
        f'"{variant.product.product_name}" moved to your cart.'
    )

    return redirect("cart")

