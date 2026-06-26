from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from decimal import Decimal
from carts.views import _get_or_create_cart
from carts.models import CartItem
from accounts.models import UserAddress
from .helpers import (
    _compute_totals,
    _get_wallet,
    _razorpay_client,
    _build_order_from_session,
)
from ..models import Payment

# ── Order value limits ───────────────────────────────────────────────────────
COD_MAX       = Decimal("20000")   # COD hard cap
RAZORPAY_MAX  = Decimal("500000")  # Razorpay cap (test cards cap at ₹25k; raise in prod)


@login_required(login_url="login")
def place_order(request):
    if request.method != "POST":
        return redirect("checkout")

    cart = _get_or_create_cart(request)
    cart_items = (
        CartItem.objects.filter(cart=cart, is_active=True)
        .select_related("variant", "variant__product")
        .prefetch_related(
            "variant__product__category",
            "variant__product__offers",
            "variant__product__category__offers",
        )
    )

    if not cart_items.exists():
        messages.error(request, "Your cart is empty.")
        return redirect("cart")

    address_id = request.POST.get("address_id")
    if not address_id:
        messages.error(request, "Please select a delivery address.")
        return redirect("checkout")
    address = get_object_or_404(UserAddress, id=address_id, user=request.user)

    totals = _compute_totals(list(cart_items), request.session)
    payment_method = request.POST.get("payment_method", "COD")
    final_total = totals["final_total"]

    # ── Payment method limits ────────────────────────────────────────────────
    if payment_method == "COD" and final_total > COD_MAX:
        messages.error(
            request,
            f"Cash on Delivery is available only for orders up to ₹{COD_MAX:,.0f}. "
            "Please choose Online Payment."
        )
        return redirect("checkout")

    if payment_method == "RAZORPAY" and final_total > RAZORPAY_MAX:
        messages.error(
            request,
            f"Online payment is available only for orders up to ₹{RAZORPAY_MAX:,.0f}. "
            "Please contact support for large orders."
        )
        return redirect("checkout")

    # ── Validate wallet balance hasn't changed ───────────────────────────────
    if totals["wallet_used"] > 0:
        wallet = _get_wallet(request.user)
        if wallet.balance < totals["wallet_used"]:
            messages.error(request, "Wallet balance changed. Please review your order.")
            return redirect("checkout")

    # ── COD / Wallet-only ────────────────────────────────────────────────────
    if payment_method == "COD":
        pay_method = "WALLET" if final_total == 0 else "COD"
        payment = Payment.objects.create(
            user=request.user,
            payment_method=pay_method,
            amount_paid=str(final_total),
            status="Completed" if final_total == 0 else "Pending",
        )
        order = _build_order_from_session(request, address, payment, totals)
        return redirect("order_complete", order_number=order.order_number)

    # ── Razorpay ─────────────────────────────────────────────────────────────
    if payment_method == "RAZORPAY":
        # Convert Decimal → int paise safely (avoid float rounding errors)
        amount_paise = int(final_total * 100)
        rz_client = _razorpay_client()

        rz_order = rz_client.order.create({
            "amount":          amount_paise,
            "currency":        "INR",
            "payment_capture": 1,
            "notes": {
                "user_id":           str(request.user.id),
                "address_id":        str(address_id),
                "coupon_discount":   str(totals["coupon_discount"]),
                "coupon_code":       str(totals["coupon_code"]),
                "coupon_id":         str(totals["coupon_id"] or ""),
                "referral_discount": str(totals["referral_discount"]),
                "referral_code":     str(totals["referral_code"]),
                "referral_id":       str(totals["referral_id"] or ""),
                "wallet_used":       str(totals["wallet_used"]),
                "wallet_applied":    str(totals["wallet_applied"]),
            },
        })

        request.session["pending_address_id"]        = address_id
        request.session["pending_razorpay_order_id"] = rz_order["id"]

        data = {
            "razorpay_key_id":   settings.RAZORPAY_KEY_ID,
            "razorpay_order_id": rz_order["id"],
            "amount_paise":      amount_paise,
            "final_total":       final_total,
            "order_currency":    "INR",
            "user_name": (
                f"{request.user.first_name} {request.user.last_name}".strip()
                or request.user.email
            ),
            "user_email":  request.user.email,
            "user_phone":  getattr(request.user, "phone_number", ""),
        }
        return render(request, "orders/razorpay_payment.html", data)

    messages.error(request, "Invalid payment method.")
    return redirect("checkout")