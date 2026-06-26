import json
from decimal import Decimal
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import ReferralCode, ReferralUse
from orders.models import Order
from carts.views import _get_or_create_cart
from carts.models import CartItem
from orders.views.helpers import _compute_totals

@login_required(login_url="login")
def apply_referral(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid request."})

    data = json.loads(request.body)
    code = data.get("code", "").strip().upper()

    cart = _get_or_create_cart(request)
    cart_items = CartItem.objects.filter(
        cart=cart, is_active=True
    ).select_related("variant", "variant__product")
    totals = _compute_totals(cart_items, request.session)
    grand_total = totals["after_coupon"]

    if request.session.get("referral_code"):
        return JsonResponse(
            {
                "success": False,
                "message": "A referral code is already applied. Remove it first.",
            }
        )

    try:
        ref_code = ReferralCode.objects.select_related("user").get(code=code)
    except ReferralCode.DoesNotExist:
        return JsonResponse(
            {
                "success": False,
                "message": "Invalid referral code."
            }
        )

    if not ref_code.is_active:
        return JsonResponse(
            {
                "success": False,
                "message": "This referral code is no longer active."
            }
        )

    if ref_code.user == request.user:
        return JsonResponse(
            {
                "success": False,
                "message": "You can't use your own referral code."
            }
        )

    if ReferralUse.objects.filter(referee=request.user).exists():
        return JsonResponse(
            {
                "success": False,
                "message": "Referral codes can only be used on your very first order.",
            }
        )

    if Order.objects.filter(user=request.user, is_ordered=True).exists():
        return JsonResponse(
            {
                "success": False,
                "message": "Referral codes are for new customers only (first order).",
            }
        )

    discount = min(ref_code.referee_discount, grand_total)
    after_ref = round(grand_total - discount, 2)

    request.session["referral_code"] = ref_code.code
    request.session["referral_id"] = ref_code.id
    request.session["referral_discount"] = str(discount)

    totals = _compute_totals(cart_items, request.session)
    
    wallet_used = totals["wallet_used"]
    final = totals["final_total"]

    return JsonResponse(
        {
            "success": True,
            "message": f"Referral code applied! You save ₹{discount} on this order.",
            "discount": str(discount),
            "after_referral": str(after_ref),
            "tax": str(totals["tax"]),
            "grand_total": str(totals["grand_total"]),
            "final": str(final),
        }
    )


@login_required(login_url="login")
def remove_referral(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid request."})

    data = json.loads(request.body)
    grand_total = Decimal(str(data.get("grand_total", "0")))

    request.session.pop("referral_code", None)
    request.session.pop("referral_id", None)
    request.session.pop("referral_discount", None)

    cart = _get_or_create_cart(request)
    cart_items = CartItem.objects.filter(
        cart=cart, is_active=True
    ).select_related("variant", "variant__product")
    totals = _compute_totals(cart_items, request.session)

    return JsonResponse(
        {
            "success": True,
            "message": "Referral code removed.",
            "tax": str(totals["tax"]),
            "grand_total": str(totals["grand_total"]),
            "final": str(totals["final_total"]),
        }
    )
