import json
import hmac
import hashlib
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from carts.models import CartItem
from ..models import Payment, Order
from accounts.models import UserAddress
from .helpers import (
    _compute_totals,
    _build_order_from_session,
    _razorpay_client,
)


@login_required(login_url="login")
def order_complete(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    order_items = order.items.select_related("variant", "variant__product").all()
    return render(request, "orders/order_complete.html", {
        "order": order,
        "order_items": order_items,
    })


@csrf_exempt
@require_POST
def razorpay_webhook(request):
    webhook_body = request.body          # raw bytes, must NOT be decoded yet
    webhook_signature = request.headers.get("X-Razorpay-Signature", "")
    webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET  # set this in .env
    expected = hmac.new(
        webhook_secret.encode("utf-8"),
        webhook_body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, webhook_signature):
        # Signature mismatch — reject, could be a fake request
        return HttpResponse(status=400)
    try:
        payload = json.loads(webhook_body)
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    event = payload.get("event")

    if event != "payment.captured":
        # Return 200 for other events so Razorpay doesn't retry
        return HttpResponse(status=200)
    payment_entity = payload["payload"]["payment"]["entity"]
    rz_payment_id  = payment_entity["id"]               
    rz_order_id    = payment_entity["order_id"]          
    amount_paise   = payment_entity["amount"]            
    if Order.objects.filter(payment__transaction_id=rz_payment_id).exists():
        return HttpResponse(status=200)  # already processed, tell Razorpay OK
    rz_client = _razorpay_client()
    try:
        rz_order = rz_client.order.fetch(rz_order_id)
    except Exception:
        return HttpResponse(status=500)
    notes       = rz_order.get("notes", {})
    address_id  = notes.get("address_id")
    user_id     = notes.get("user_id")

    if not address_id or not user_id:
        return HttpResponse(status=400)

    # ── Step 7: Fetch Django objects ──────────────────────────
    from django.contrib.auth import get_user_model
    User = get_user_model()

    try:
        user    = User.objects.get(id=user_id)
        address = UserAddress.objects.get(id=address_id, user=user)
    except (User.DoesNotExist, UserAddress.DoesNotExist):
        return HttpResponse(status=400)
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
    payment = Payment.objects.create(
        user=user,
        payment_method="RAZORPAY",
        amount_paid=str(amount_paise / 100),  # convert paise → rupees
        status="Completed",
        transaction_id=rz_payment_id,
    )

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
    return HttpResponse(status=200)


@csrf_exempt
def razorpay_callback(request):
    if request.method != "POST":
        return redirect("checkout")

    rz_payment_id = request.POST.get("razorpay_payment_id", "")
    rz_order_id   = request.POST.get("razorpay_order_id", "")
    rz_signature  = request.POST.get("razorpay_signature", "")

    print("CALLBACK HIT")
    print("PAYMENT ID:", rz_payment_id)
    print("ORDER ID:", rz_order_id)

    # Step 1: Verify signature
    try:
        rz_client = _razorpay_client()
        rz_client.utility.verify_payment_signature({
            "razorpay_order_id":   rz_order_id,
            "razorpay_payment_id": rz_payment_id,
            "razorpay_signature":  rz_signature,
        })
        print("SIGNATURE OK")
    except Exception as e:
        print("SIGNATURE FAILED:", str(e))
        return redirect("payment_failed")

    # Step 2: Get user + address from Razorpay order notes
    try:
        rz_order   = rz_client.order.fetch(rz_order_id)
        notes      = rz_order.get("notes", {})
        address_id = notes.get("address_id")
        user_id    = notes.get("user_id")
        print("NOTES:", notes)
    except Exception as e:
        print("FETCH ORDER ERROR:", str(e))
        return redirect("payment_failed")

    # Step 3: Get Django user and address
    try:
        from django.contrib.auth import get_user_model
        User    = get_user_model()
        user    = User.objects.get(id=user_id)
        address = UserAddress.objects.get(id=address_id, user=user)
    except Exception as e:
        print("USER/ADDRESS ERROR:", str(e))
        return redirect("payment_failed")

    # Step 4: Build fake session from notes
    fake_session = {
        "coupon_discount":   notes.get("coupon_discount", "0"),
        "coupon_code":       notes.get("coupon_code", ""),
        "coupon_id":         notes.get("coupon_id") or None,
        "referral_discount": notes.get("referral_discount", "0"),
        "referral_code":     notes.get("referral_code", ""),
        "referral_id":       notes.get("referral_id") or None,
        "wallet_used":       notes.get("wallet_used", "0"),
        "wallet_applied":    notes.get("wallet_applied", False),
    }

    class FakeRequest:
        def __init__(self, u, s):
            self.user = u
            self.session = type('Session', (), {
                'session_key': None,
                'get':          lambda self, k, d=None: s.get(k, d),
                'pop':          lambda self, k, d=None: s.pop(k, d),
                'create':       lambda self: None,
                '__contains__': lambda self, k: k in s,
                '__getitem__':  lambda self, k: s[k],
                '__setitem__':  lambda self, k, v: s.__setitem__(k, v),
            })()
        def __getattr__(self, name):
            return None

    fake_request = FakeRequest(user, fake_session)
    
    # Step 6: Get cart and compute totals
    try:
        from carts.models import Cart
        cart       = Cart.objects.get(user=user)
        cart_items = list(
            CartItem.objects.filter(cart=cart, is_active=True)
            .select_related("variant", "variant__product")
        )
        totals = _compute_totals(cart_items, fake_session)
        print("TOTALS:", totals["final_total"])
    except Exception as e:
        print("CART ERROR:", str(e))
        return redirect("payment_failed")

    # Step 7: Create payment + order
    try:
        payment = Payment.objects.create(
            user=user,
            payment_method="RAZORPAY",
            amount_paid=str(totals["final_total"]),
            status="Completed",
            transaction_id=rz_payment_id,
        )
        order = _build_order_from_session(fake_request, address, payment, totals)
        print("ORDER CREATED:", order.order_number)
    except Exception as e:
        print("ORDER CREATE ERROR:", str(e))
        return redirect("payment_failed")

    return redirect("payment_success", order_number=order.order_number)


@login_required(login_url="login")
def payment_processing(request):
    payment_id = request.session.get("pending_payment_id", "")
    return render(request, "orders/payment_processing.html", {
        "payment_id": payment_id,
    })


@login_required(login_url="login")
def check_order_status(request):
    payment_id = request.GET.get("payment_id", "")
    try:
        order = Order.objects.get(
            payment__transaction_id=payment_id,
            user=request.user,
        )
        return JsonResponse(
            {"status": "ready", "order_number": order.order_number}
        )
    except Order.DoesNotExist:
        return JsonResponse({"status": "pending"})


def payment_success(request, order_number):
    order = get_object_or_404(
        Order, order_number=order_number,
        user=request.user
    )
    order_items = order.items.select_related(
        "variant", "variant__product").all()
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
