from django.shortcuts import render, redirect, get_object_or_404
from offers.utils import annotate_variants_with_offers
from django.contrib import messages
from django.contrib.messages import get_messages
from carts.models import CartItem
from store.models import ProductVariant
from .models import Cart
from django.http import JsonResponse
from decimal import Decimal


CART_MAX_TOTAL = 10
PRODUCT_MAX_QTY = 3


def _cart_id(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def clear_messages(request):
    storage = get_messages(request)
    for _ in storage:
        pass


def _get_or_create_cart(request):
    if request.user.is_authenticated:
        user_cart, _ = Cart.objects.get_or_create(user=request.user)
        session_key = _cart_id(request)
        if not request.session.get("cart_merged", False):
            session_cart = Cart.objects.filter(cart_id=session_key).first()
            if session_cart and session_cart.user is None:
                _merge_carts(user_cart, session_cart)
                request.session["cart_merged"] = True
        return user_cart
    return Cart.objects.get_or_create(cart_id=_cart_id(request))[0]


def _merge_carts(user_cart, session_cart):
    if session_cart == user_cart:
        return 
    existing_total = sum(
        i.quantity for i in CartItem.objects.filter(cart=user_cart, is_active=True)
    )
    for item in CartItem.objects.filter(cart=session_cart, is_active=True):
        if existing_total >= CART_MAX_TOTAL:
            break
        user_item, created = CartItem.objects.get_or_create(
            cart=user_cart,
            variant=item.variant,
        )
        if not created:
            allowed_qty = min(
                PRODUCT_MAX_QTY - user_item.quantity,
                item.quantity,
                CART_MAX_TOTAL - existing_total,
            )
            if allowed_qty <= 0:
                continue
            user_item.quantity += allowed_qty
        else:
            allowed_qty = min(
                item.quantity,
                PRODUCT_MAX_QTY,
                CART_MAX_TOTAL - existing_total,
            )
            if allowed_qty <= 0:
                continue
            user_item.quantity = allowed_qty
        user_item.save()
        existing_total += allowed_qty
    session_cart.delete()


def _effective_price(variant):
    from offers.utils import get_applicable_offer, apply_discount

    try:
        pct, _ = get_applicable_offer(variant.product)
        return apply_discount(variant.price, pct)
    except Exception:
        from decimal import Decimal

        return Decimal(str(variant.price))


def cart(request):
    cart_obj = _get_or_create_cart(request)

    cart_items = list(
        CartItem.objects.filter(cart=cart_obj, is_active=True)
        .select_related(
            "variant",
            "variant__product",
            "variant__product__brand",
            "variant__inventory",
        )
        .prefetch_related(
            "variant__product__category",
            "variant__product__offers",
            "variant__product__category__offers",
        )
    )

    removed_any = False

    for item in cart_items:
        invalid = (
            item.variant.inventory.quantity <= 0
            or not item.variant.is_available
            or item.variant.product.brand is None
            or item.variant.product.brand.status != "active"
            or not item.variant.product.category.filter(status="active").exists()
        )

        if invalid:
            item.delete()
            removed_any = True

    if removed_any:
        messages.warning(
            request,
            "Some unavailable items were removed from your cart."
        )

    cart_items = list(
        CartItem.objects.filter(cart=cart_obj, is_active=True)
        .select_related(
            "variant",
            "variant__product",
            "variant__product__brand",
            "variant__inventory",
        )
        .prefetch_related(
            "variant__product__category",
            "variant__product__offers",
            "variant__product__category__offers",
        )
    )

    annotate_variants_with_offers([item.variant for item in cart_items])

    total = 0
    quantity = 0

    for item in cart_items:
        item.discounted_subtotal = (
            item.variant.effective_price * item.quantity
        )
        total += item.discounted_subtotal
        quantity += item.quantity

    tax = round(Decimal("0.18") * Decimal(str(total)), 2)
    grand_total = round(Decimal(str(total)) + tax, 2)

    storage = get_messages(request)
    first_message = None

    for msg in storage:
        first_message = msg
        break

    return render(
        request,
        "store/cart.html",
        {
            "cart_items": cart_items,
            "total": total,
            "quantity": quantity,
            "tax": tax,
            "grand_total": grand_total,
            "first_message": first_message,
        },
    )


def add_cart(request, variant_id):
    clear_messages(request)
    variant = get_object_or_404(ProductVariant, id=variant_id)

    if variant.inventory.quantity <= 0:
        messages.error(request, "This item is out of stock.")
        return redirect(request.META.get("HTTP_REFERER", "store"))

    cart = _get_or_create_cart(request)
    cart_items = CartItem.objects.filter(cart=cart, is_active=True)

    total_qty = sum(i.quantity for i in cart_items)
    if total_qty >= CART_MAX_TOTAL:
        messages.error(request, "Maximum 10 items allowed in cart.")
        return redirect(request.META.get("HTTP_REFERER", "store"))

    same_product_qty = sum(
        i.quantity for i in cart_items if i.variant.product_id == variant.product_id
    )
    if same_product_qty >= PRODUCT_MAX_QTY:
        messages.error(request, "Max 3 of the same product allowed.")
        return redirect(request.META.get("HTTP_REFERER", "store"))

    try:
        cart_item = CartItem.objects.get(cart=cart, variant=variant)
        if cart_item.quantity >= variant.inventory.quantity:
            messages.error(request, "Stock limit reached.")
            return redirect(request.META.get("HTTP_REFERER", "store"))
        cart_item.quantity += 1
        cart_item.save()
    except CartItem.DoesNotExist:
        CartItem.objects.create(cart=cart, variant=variant, quantity=1)
    messages.success(request, "Item added to cart.", extra_tags="cart_popup")
    return redirect(request.META.get("HTTP_REFERER", "store"))


def increment_cart(request, variant_id):
    cart = _get_or_create_cart(request)

    cart_item = get_object_or_404(
        CartItem,
        cart=cart,
        variant_id=variant_id
    )

    if cart_item.variant.inventory.quantity <= 0:
        return JsonResponse({
            "success": False,
            "message": "Out of stock."
        })

    all_items = CartItem.objects.filter(
        cart=cart,
        is_active=True
    )

    if sum(i.quantity for i in all_items) >= CART_MAX_TOTAL:
        return JsonResponse({
            "success": False,
            "message": "Maximum 10 items allowed."
        })

    same_product_qty = sum(
        i.quantity
        for i in all_items
        if i.variant.product_id == cart_item.variant.product_id
    )

    if same_product_qty >= PRODUCT_MAX_QTY:
        return JsonResponse({
            "success": False,
            "message": "Max 3 of same product allowed."
        })

    if cart_item.quantity >= cart_item.variant.inventory.quantity:
        return JsonResponse({
            "success": False,
            "message": "Stock limit reached."
        })

    cart_item.quantity += 1
    cart_item.save()

    effective_price = _effective_price(cart_item.variant)
    subtotal = effective_price * cart_item.quantity
    
    cart_items = CartItem.objects.filter(cart=cart, is_active=True)
    total = 0
    for item in cart_items:
        effective_price = _effective_price(item.variant)
        total += effective_price * item.quantity

    tax = round(Decimal("0.18") * Decimal(str(total)), 2)
    grand_total = round(Decimal(str(total)) + tax, 2)

    return JsonResponse({
        "success": True,
        "quantity": cart_item.quantity,
        "subtotal": float(subtotal),
        "cart_total": float(total),
        "tax": float(tax),
        "grand_total": float(grand_total),
    })


def decrement_cart(request, variant_id):

    cart = _get_or_create_cart(request)

    cart_item = get_object_or_404(
        CartItem,
        cart=cart,
        variant_id=variant_id
    )

    if cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()

    effective_price = _effective_price(cart_item.variant)
    subtotal = effective_price * cart_item.quantity

    cart_items = CartItem.objects.filter(cart=cart, is_active=True)
    total = 0
    for item in cart_items:
        effective_price = _effective_price(item.variant)
        total += effective_price * item.quantity

    tax = round(Decimal("0.18") * Decimal(str(total)), 2)
    grand_total = round(Decimal(str(total)) + tax, 2)

    return JsonResponse({
        "success": True,
        "quantity": cart_item.quantity,
        "subtotal": float(subtotal),
        "cart_total": float(total),
        "tax": float(tax),
        "grand_total": float(grand_total),
    })
 

def remove_cartitem(request, variant_id):
    cart = _get_or_create_cart(request)
    CartItem.objects.filter(cart=cart, variant_id=variant_id).delete()
    messages.success(request, "Item removed from cart.")
    return redirect("cart")


def remove_cart(request, variant_id):
    cart = _get_or_create_cart(request)
    cart_item = CartItem.objects.filter(
        cart=cart, variant_id=variant_id).first()
    if cart_item and cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()
    return redirect("cart")
