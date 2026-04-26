from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
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
            "variant__product__offer",
            "variant__product__category__offer",
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

    # Validate wallet
    if totals["wallet_used"] > 0:
        wallet = _get_wallet(request.user)
        if wallet.balance < totals["wallet_used"]:
            messages.error(request, "Wallet balance changed. Please review your order.")
            return redirect("checkout")

    if payment_method == "COD":
        pay_method = "WALLET" if totals["final_total"] == 0 else "COD"
        payment = Payment.objects.create(
            user=request.user,
            payment_method=pay_method,
            amount_paid=str(totals["final_total"]),
            status="Completed" if totals["final_total"] == 0 else "Pending",
        )
        order = _build_order_from_session(request, address, payment, totals)
        return redirect("order_complete", order_number=order.order_number)

    if payment_method == "RAZORPAY":
        amount_paise = int(totals["final_total"] * 100)
        rz_client = _razorpay_client()
        rz_order = rz_client.order.create(
            {
                "amount": amount_paise,
                "currency": "INR",
                "payment_capture": 1,
            }
        )
        request.session["pending_address_id"] = address_id
        request.session["pending_razorpay_order_id"] = rz_order["id"]
        return render(
            request,
            "orders/razorpay_payment.html",
            {
                "razorpay_key_id": settings.RAZORPAY_KEY_ID,
                "razorpay_order_id": rz_order["id"],
                "amount_paise": amount_paise,
                "final_total": totals["final_total"],
                "order_currency": "INR",
                "user_name": f"{request.user.first_name} {request.user.last_name}".strip()
                or request.user.email,
                "user_email": request.user.email,
                "user_phone": getattr(request.user, "phone_number", ""),
            },
        )

    messages.error(request, "Invalid payment method.")
    return redirect("checkout")

