import json
import hmac
import hashlib

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.conf import settings

from carts.views import _get_or_create_cart
from carts.models import CartItem
from accounts.models import UserAddress
from .helpers import (
    _compute_totals,
    _build_order_from_session,
    _razorpay_client,
)
from ..models import Payment, Order


# ─────────────────────────────────────────────
# 1. ORDER COMPLETE (COD)
# ─────────────────────────────────────────────
@login_required(login_url="login")
def order_complete(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    order_items = order.items.select_related("variant", "variant__product").all()
    return render(request, "orders/order_complete.html", {
        "order": order,
        "order_items": order_items,
    })


# ─────────────────────────────────────────────
# 2. WEBHOOK  ← Razorpay server calls this
#    No browser, no session, no login needed
# ─────────────────────────────────────────────
@csrf_exempt
@require_POST
def razorpay_webhook(request):
    """
    Razorpay's server POSTs here after every payment event.
    We verify the webhook signature and create the order.

    Flow:
        Razorpay server → POST /orders/razorpay-webhook/ → create order
    """

    # ── Step 1: Read raw body & signature header ──────────────
    webhook_body = request.body          # raw bytes, must NOT be decoded yet
    webhook_signature = request.headers.get("X-Razorpay-Signature", "")
    webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET  # set this in .env

    # ── Step 2: Verify webhook signature ─────────────────────
    # Razorpay signs the raw body with your webhook secret using HMAC-SHA256
    expected = hmac.new(
        webhook_secret.encode("utf-8"),
        webhook_body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, webhook_signature):
        # Signature mismatch — reject, could be a fake request
        return HttpResponse(status=400)

    # ── Step 3: Parse the event ───────────────────────────────
    try:
        payload = json.loads(webhook_body)
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    event = payload.get("event")

    # We only care about successful payments
    if event != "payment.captured":
        # Return 200 for other events so Razorpay doesn't retry
        return HttpResponse(status=200)

    # ── Step 4: Extract payment info from payload ─────────────
    payment_entity = payload["payload"]["payment"]["entity"]
    rz_payment_id  = payment_entity["id"]               # pay_xxxxx
    rz_order_id    = payment_entity["order_id"]          # order_xxxxx
    amount_paise   = payment_entity["amount"]            # e.g. 50000

    # ── Step 5: Check if order already created (avoid duplicate) ──
    # Webhook can fire more than once — guard against duplicate orders
    if Order.objects.filter(payment__transaction_id=rz_payment_id).exists():
        return HttpResponse(status=200)  # already processed, tell Razorpay OK

    # ── Step 6: Look up the pending Django order data ─────────
    # We stored address_id in the Razorpay order's notes when creating it
    rz_client = _razorpay_client()
    try:
        rz_order = rz_client.order.fetch(rz_order_id)
    except Exception:
        return HttpResponse(status=500)

    notes       = rz_order.get("notes", {})
    address_id  = notes.get("address_id")
    user_id     = notes.get("user_id")

    if not address_id or not user_id:
        # Notes missing — can't create order without address/user
        return HttpResponse(status=400)

    # ── Step 7: Fetch Django objects ──────────────────────────
    from django.contrib.auth import get_user_model
    User = get_user_model()

    try:
        user    = User.objects.get(id=user_id)
        address = UserAddress.objects.get(id=address_id, user=user)
    except (User.DoesNotExist, UserAddress.DoesNotExist):
        return HttpResponse(status=400)

    # ── Step 8: Rebuild totals from session data stored in notes ──
    # We stored discount/coupon/wallet info in notes too (see place_order.py)
    fake_session = {
        "coupon_discount":  notes.get("coupon_discount", "0"),
        "coupon_code":      notes.get("coupon_code", ""),
        "coupon_id":        notes.get("coupon_id"),
        "referral_discount": notes.get("referral_discount", "0"),
        "referral_code":    notes.get("referral_code", ""),
        "referral_id":      notes.get("referral_id"),
        "wallet_used":      notes.get("wallet_used", "0"),
        "wallet_applied":   notes.get("wallet_applied", False),
    }

    # Get cart items for this user
    from carts.models import Cart
    try:
        cart = Cart.objects.get(user=user)
        cart_items = list(
            CartItem.objects.filter(cart=cart, is_active=True)
            .select_related("variant", "variant__product")
        )
    except Cart.DoesNotExist:
        return HttpResponse(status=400)

    totals = _compute_totals(cart_items, fake_session)

    # ── Step 9: Create Payment + Order ───────────────────────
    payment = Payment.objects.create(
        user=user,
        payment_method="RAZORPAY",
        amount_paid=str(amount_paise / 100),  # convert paise → rupees
        status="Completed",
        transaction_id=rz_payment_id,
    )

    # _build_order_from_session needs request-like object
    # We create a simple wrapper since we have no real request here
    class FakeRequest:
        def __init__(self, user, session):
            self.user    = user
            self.session = session

    fake_request = FakeRequest(user=user, session=fake_session)

    try:
        _build_order_from_session(fake_request, address, payment, totals)
    except Exception as e:
        print("WEBHOOK ORDER CREATE ERROR:", str(e))
        return HttpResponse(status=500)

    # ── Step 10: Tell Razorpay we processed it ────────────────
    return HttpResponse(status=200)


# ─────────────────────────────────────────────
# 3. BROWSER RETURN — just redirect user to success page
#    Order is already created by webhook above
# ─────────────────────────────────────────────
@login_required(login_url="login")
@csrf_exempt
def razorpay_callback(request):
    print("METHOD:", request.method)
    print("POST:", request.POST)
    print("ALL HEADERS:", dict(request.headers))
    if request.method != "POST":
        return redirect("checkout")

    rz_payment_id = request.POST.get("razorpay_payment_id", "")
    rz_order_id   = request.POST.get("razorpay_order_id", "")
    rz_signature  = request.POST.get("razorpay_signature", "")

    # Verify signature (basic check in browser flow too)
    try:
        rz_client = _razorpay_client()
        rz_client.utility.verify_payment_signature({
            "razorpay_order_id":   rz_order_id,
            "razorpay_payment_id": rz_payment_id,
            "razorpay_signature":  rz_signature,
        })
    except Exception:
        request.session["failed_razorpay_order_id"] = rz_order_id
        return redirect("payment_failed")

    # Find the order created by webhook
    # Webhook might be slightly ahead or slightly behind browser — poll briefly
    import time
    order = None
    for _ in range(5):          # try up to 5 times, 1 second apart
        try:
            order = Order.objects.get(
                payment__transaction_id=rz_payment_id,
                user=request.user,
            )
            break
        except Order.DoesNotExist:
            time.sleep(1)

    if not order:
        # Webhook hasn't fired yet — show a "processing" page
        # Store payment_id so we can poll from the frontend
        request.session["pending_payment_id"] = rz_payment_id
        return redirect("payment_processing")

    return redirect("payment_success", order_number=order.order_number)


# ─────────────────────────────────────────────
# 4. PAYMENT PROCESSING (webhook delay fallback)
# ─────────────────────────────────────────────
@login_required(login_url="login")
def payment_processing(request):
    """
    Shown if browser arrives before webhook creates the order.
    Page auto-polls /orders/check-order-status/ every 2 seconds.
    """
    payment_id = request.session.get("pending_payment_id", "")
    return render(request, "orders/payment_processing.html", {
        "payment_id": payment_id,
    })


@login_required(login_url="login")
def check_order_status(request):
    """
    AJAX endpoint polled by payment_processing.html
    Returns JSON: {status: 'ready', order_number: 'ORBxxxxxxxx'}
               or {status: 'pending'}
    """
    payment_id = request.GET.get("payment_id", "")
    try:
        order = Order.objects.get(
            payment__transaction_id=payment_id,
            user=request.user,
        )
        return JsonResponse({"status": "ready", "order_number": order.order_number})
    except Order.DoesNotExist:
        return JsonResponse({"status": "pending"})


# ─────────────────────────────────────────────
# 5. SUCCESS & FAILED PAGES (unchanged)
# ─────────────────────────────────────────────
def payment_success(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    order_items = order.items.select_related("variant", "variant__product").all()
    return render(request, "orders/payment_success.html", {
        "order": order,
        "order_items": order_items,
    })


@login_required(login_url="login")
def payment_failed(request):
    rz_order_id = request.session.pop("failed_razorpay_order_id", "")
    return render(request, "orders/payment_failed.html", {
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
        "razorpay_order_id": rz_order_id,
    })