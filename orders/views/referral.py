import json
from decimal import Decimal
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required


@login_required(login_url="login")
def apply_referral(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid request."})

    from offers.models import ReferralCode, ReferralUse

    data = json.loads(request.body)
    code = data.get("code", "").strip().upper()
    grand_total = Decimal(str(data.get("grand_total", "0")))

    # Already applied in this session?
    if request.session.get("referral_code"):
        return JsonResponse(
            {
                "success": False,
                "message": "A referral code is already applied. Remove it first.",
            }
        )

    # Also block if coupon is applied (one discount type at a time is fine,
    # but referral stacks with coupon — both can apply together)

    # Fetch code
    try:
        ref_code = ReferralCode.objects.select_related("user").get(code=code)
    except ReferralCode.DoesNotExist:
        return JsonResponse({"success": False, "message": "Invalid referral code."})

    # Must be active
    if not ref_code.is_active:
        return JsonResponse(
            {"success": False, "message": "This referral code is no longer active."}
        )

    # Cannot use your own code
    if ref_code.user == request.user:
        return JsonResponse(
            {"success": False, "message": "You can't use your own referral code."}
        )

    # Has this user ALREADY used any referral code before?
    if ReferralUse.objects.filter(referee=request.user).exists():
        return JsonResponse(
            {
                "success": False,
                "message": "Referral codes can only be used on your very first order.",
            }
        )

    # Has this user already placed any orders? (first-order-only rule)
    from orders.models import Order

    if Order.objects.filter(user=request.user, is_ordered=True).exists():
        return JsonResponse(
            {
                "success": False,
                "message": "Referral codes are for new customers only (first order).",
            }
        )

    # Calculate discount — fixed ₹ amount from the code
    discount = min(ref_code.referee_discount, grand_total)
    after_ref = round(grand_total - discount, 2)

    # Save in session
    request.session["referral_code"] = ref_code.code
    request.session["referral_id"] = ref_code.id
    request.session["referral_discount"] = str(discount)

    # Recalculate wallet if already applied
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

    # Recalculate wallet
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
