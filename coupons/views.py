import json
from decimal import Decimal
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from coupons.models import Coupon, CouponUsage
from carts.views import _get_or_create_cart
from carts.models import CartItem
from orders.views.helpers import _compute_totals


@login_required(login_url="login")
def apply_coupon(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid request."})

    data = json.loads(request.body)
    code = data.get("code", "").strip().upper()
    cart = _get_or_create_cart(request)
    cart_items = CartItem.objects.filter(
        cart=cart, is_active=True).select_related(
        "variant", "variant__product"
    )
    totals = _compute_totals(cart_items, request.session)
    subtotal = totals["subtotal"]

    if request.session.get("coupon_code"):
        return JsonResponse(
            {
                "success": False,
                "message": "A coupon is already applied. Remove it first.",
            }
        )

    try:
        coupon = Coupon.objects.get(code=code)
    except Coupon.DoesNotExist:
        return JsonResponse(
            {"success": False, "message": "Invalid coupon code."})

    valid, msg = coupon.is_valid()
    if not valid:
        return JsonResponse({"success": False, "message": msg})

    if subtotal < coupon.min_order_amt:
        return JsonResponse(
            {
                "success": False,
                "message": f"Minimum order ₹{coupon.min_order_amt} required.",
            }
        )

    usage, _ = CouponUsage.objects.get_or_create(
        coupon=coupon, user=request.user)
    if usage.used_count >= coupon.usage_limit:
        return JsonResponse(
            {"success": False, "message": "You have already used this coupon."}
        )

    discount = coupon.calculate_discount(subtotal)
    after_coup = max(round(subtotal - discount, 2), Decimal("0"))

    request.session["coupon_code"] = coupon.code
    request.session["coupon_id"] = coupon.id
    request.session["coupon_discount"] = str(discount)
    request.session["coupon_cart_total"] = str(subtotal)

    totals = _compute_totals(cart_items, request.session)

    wallet_used = totals["wallet_used"]
    if wallet_used > 0:
        wallet_used = min(wallet_used, totals["grand_total"])
        request.session["wallet_used"] = str(wallet_used)

    final = totals["final_total"]

    return JsonResponse(
        {
            "success": True,
            "message": f'Coupon "{coupon.code}" applied! You saved ₹{discount}.',
            "discount": str(discount),
            "after_coup": str(after_coup),
            "tax": str(totals["tax"]),
            "grand_total": str(totals["grand_total"]),
            "final": str(final),
        }
    )


@login_required(login_url="login")
def remove_coupon(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid request."})

    request.session.pop("coupon_code", None)
    request.session.pop("coupon_id", None)
    request.session.pop("coupon_discount", None)
    request.session.pop("coupon_cart_total", None)

    cart = _get_or_create_cart(request)
    cart_items = CartItem.objects.filter(
        cart=cart, is_active=True).select_related(
        "variant", "variant__product"
    )
    totals = _compute_totals(cart_items, request.session)

    wallet_used = totals["wallet_used"]
    if wallet_used > 0:
        wallet_used = min(wallet_used, totals["grand_total"])
        request.session["wallet_used"] = str(wallet_used)

    final = totals["final_total"]

    return JsonResponse(
        {
            "success": True,
            "message": "Coupon removed.",
            "after_coup": str(totals["subtotal"]),
            "tax": str(totals["tax"]),
            "grand_total": str(totals["grand_total"]),
            "final": str(final),
        }
    )