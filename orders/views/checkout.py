from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from carts.views import _get_or_create_cart
from carts.models import CartItem
from accounts.models import UserAddress
from .helpers import _compute_totals, _get_wallet
from decimal import Decimal
from offers.utils import annotate_variants_with_offers
from offers.models import ReferralUse
from ..models import Order


@login_required(login_url="login")
def checkout(request):
    cart = _get_or_create_cart(request)
    cart_items = (
        CartItem.objects.filter(cart=cart, is_active=True)
        .select_related(
            "variant", "variant__product", "variant__inventory",
        )
        .prefetch_related(
            "variant__product__category",
            "variant__product__offers",
            "variant__product__category__offers",
        )
    )
    if not cart_items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect("cart")
    cart_items_list = list(cart_items)
    annotate_variants_with_offers([item.variant for item in cart_items_list])
    total = 0
    for item in cart_items_list:
        stock = item.variant.inventory.quantity
        if stock <= 0:
            messages.error(
                request,
                f"{item.variant.product.product_name} is out of stock.",
            )
            return redirect("cart")
        if item.quantity > stock:
            messages.error(
                request,
                f"Only {stock} unit(s) available for "
                f"{item.variant.product.product_name}.",
            )
            return redirect("cart")

        item.sub_total = item.variant.effective_price * item.quantity
        total += item.sub_total
    saved_total = request.session.get("coupon_cart_total")
    if saved_total and float(saved_total) != float(total):
        request.session.pop("coupon_code", None)
        request.session.pop("coupon_id", None)
        request.session.pop("coupon_discount", None)
        request.session.pop("coupon_cart_total", None)
    has_order = Order.objects.filter(
        user=request.user,
        is_ordered=True
    ).exists()
    show_referral_section = not has_order
    ref_use = (
        ReferralUse.objects.filter(
            referee=request.user
        )
        .select_related("referral_code")
        .first()
    )
    if show_referral_section and ref_use:
        request.session["referral_code"] = ref_use.referral_code.code
        request.session["referral_discount"] = str(
            ref_use.referral_code.referee_discount
        )
        request.session["referral_id"] = ref_use.referral_code.id
    else:
        request.session.pop("referral_code", None)
        request.session.pop("referral_discount", None)
        request.session.pop("referral_id", None)
    totals = _compute_totals(cart_items_list, request.session)
    totals["subtotal"] = total
    totals["tax"] = round(Decimal("0.18") * Decimal(str(total)), 2)
    totals["grand_total"] = round(Decimal(str(total)) + totals["tax"], 2)
    totals["after_coupon"] = max(
        totals["grand_total"] - totals["coupon_discount"], Decimal("0")
    )
    totals["after_referral"] = max(
        totals["after_coupon"] - totals["referral_discount"], Decimal("0")
    )
    totals["final_total"] = max(
        totals["after_referral"] - totals["wallet_used"], Decimal("0")
    )
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
        "ref_use": ref_use,
        "show_referral_section": show_referral_section,
    }

    return render(request, "orders/checkout.html", context)
