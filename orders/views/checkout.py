from django.shortcuts import render, redirect

from django.contrib.auth.decorators import login_required

from django.contrib import messages
from django.conf import settings
from carts.views import _get_or_create_cart
from carts.models import CartItem
from accounts.models import UserAddress
from .helpers import _compute_totals, _get_wallet
from decimal import Decimal
from offers.utils import get_applicable_offer, apply_discount


@login_required(login_url="login")
def checkout(request):
    cart = _get_or_create_cart(request)
    cart_items = (
        CartItem.objects.filter(cart=cart, is_active=True)
        .select_related("variant", "variant__product")
        .prefetch_related(
            "variant__product__category",
            "variant__product__offer",
            "variant__product__category__offer",
        )
    )

    if not cart_items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect("cart")

    # Annotate each item with its discounted sub_total for the template
    cart_items_list = list(cart_items)

    for item in cart_items_list:

        stock = item.variant.stock

        if stock <= 0:
            messages.error(
                request,
                f"{item.variant.product.product_name} is out of stock."
            )
            return redirect("cart")

        if item.quantity > stock:
            messages.error(
                request,
                f"Only {stock} unit(s) available for {item.variant.product.product_name}."
            )
            return redirect("cart")

        try:
            pct, label, _ = get_applicable_offer(item.variant.product)
            original_price = item.variant.price
            effective_price = apply_discount(original_price, pct)
            item.variant.has_offer = pct > 0
            item.variant.original_price = original_price
            item.variant.effective_price = effective_price
            item.variant.offer_label = label
            item.sub_total = effective_price * item.quantity
        except Exception:
            item.variant.has_offer = False
            item.variant.original_price = item.variant.price
            item.variant.effective_price = item.variant.price
            item.sub_total = item.variant.price * item.quantity

    totals = _compute_totals(cart_items_list, request.session)
    wallet = _get_wallet(request.user)
    addresses = UserAddress.objects.filter(user=request.user).order_by("-is_default")
    coupon_code = request.session.get("coupon_code", None)
    context = {
        "cart_items": cart_items_list,
        "total": totals["subtotal"],
        "tax": totals["tax"],
        "grand_total": totals["grand_total"],
        "coupon_discount": totals["coupon_discount"],
        "after_coupon": totals["after_coupon"],
        "referral_discount": totals["referral_discount"],
        "referral_code": totals["referral_code"],
        "after_referral": totals["after_referral"],
        "wallet_balance": wallet.balance,
        "wallet_used": totals["wallet_used"],
        "wallet_applied": totals["wallet_applied"],
        "final_total": totals["final_total"],
        "addresses": addresses,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
        "coupon_code": coupon_code,
    }
    return render(request, "orders/checkout.html", context)