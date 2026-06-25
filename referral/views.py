import json
from decimal import Decimal
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import ReferralCode, ReferralUse
from orders.models import Order


@login_required(login_url="login")
def apply_referral(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid request."})

    data = json.loads(request.body)
    code = data.get("code", "").strip().upper()
    grand_total = Decimal(str(data.get("grand_total", "0")))

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

    wallet_used = Decimal(request.session.get("wallet_used", "0"))
    if wallet_used > 0:
        wallet_used = min(wallet_used, after_ref)
        request.session["wallet_used"] = str(wallet_used)

    final = max(after_ref - wallet_used, Decimal("0"))

    return JsonResponse(
        {
            "success": True,
            "message": f"Referral code applied! You save ₹{discount} on this order.",
            "discount": str(discount),
            "after_ref": str(after_ref),
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

    coupon_discount = Decimal(request.session.get("coupon_discount", "0"))
    after_coupon = round(grand_total - coupon_discount, 2)
    wallet_used = Decimal(request.session.get("wallet_used", "0"))
    if wallet_used > 0:
        wallet_used = min(wallet_used, after_coupon)
        request.session["wallet_used"] = str(wallet_used)
    final = max(after_coupon - wallet_used, Decimal("0"))

    return JsonResponse(
        {
            "success": True,
            "message": "Referral code removed.",
            "final": str(final),
        }
    )
