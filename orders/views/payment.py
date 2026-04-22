from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from carts.views import _get_or_create_cart
from carts.models import CartItem
from accounts.models import UserAddress
from .helpers import _compute_totals, _build_order_from_session, _razorpay_client
from ..models import Payment, Order


@login_required(login_url="login")
@csrf_exempt
def razorpay_callback(request):
    if request.method != "POST":
        return redirect("checkout")

    rz_payment_id = request.POST.get("razorpay_payment_id", "")
    rz_order_id = request.POST.get("razorpay_order_id", "")
    rz_signature = request.POST.get("razorpay_signature", "")

    print("PAYMENT ID:", rz_payment_id)
    print("ORDER ID:", rz_order_id)
    print("SIGNATURE:", rz_signature)
    try:
        rz_client = _razorpay_client()
        rz_client.utility.verify_payment_signature(
            {
                "razorpay_order_id": rz_order_id,
                "razorpay_payment_id": rz_payment_id,
                "razorpay_signature": rz_signature,
            }
        )
        signature_ok = True
    except Exception as e:
        print("SIGNATURE ERROR:", str(e))
        signature_ok = False

    if not signature_ok:
        # Store failed order id so failure page can offer retry
        request.session["failed_razorpay_order_id"] = rz_order_id
        return redirect("payment_failed")

    # ── Build order ───────────────────────────────────────
    address_id = request.session.get("pending_address_id")
    if not address_id:
        messages.error(request, "Session expired. Please try again.")
        return redirect("checkout")

    address = get_object_or_404(UserAddress, id=address_id, user=request.user)

    cart = _get_or_create_cart(request)
    cart_items = CartItem.objects.filter(cart=cart, is_active=True).select_related(
        "variant", "variant__product"
    )

    totals = _compute_totals(cart_items, request.session)

    payment = Payment.objects.create(
        user=request.user,
        payment_method="RAZORPAY",
        amount_paid=str(totals["final_total"]),
        status="Completed",
        transaction_id=rz_payment_id,
    )
    order = _build_order_from_session(request, address, payment, totals)
    return redirect("payment_success", order_number=order.order_number)


@login_required(login_url="login")
def order_complete(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    order_items = order.items.select_related("variant", "variant__product").all()
    return render(
        request,
        "orders/order_complete.html",
        {
            "order": order,
            "order_items": order_items,
        },
    )


def payment_success(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    order_items = order.items.select_related("variant", "variant__product").all()
    return render(
        request,
        "orders/payment_success.html",
        {
            "order": order,
            "order_items": order_items,
        },
    )


@login_required(login_url="login")
def payment_failed(request):
    rz_order_id = request.session.pop("failed_razorpay_order_id", "")
    return render(
        request,
        "orders/payment_failed.html",
        {
            "razorpay_key_id": settings.RAZORPAY_KEY_ID,
            "razorpay_order_id": rz_order_id,
        },
    )
