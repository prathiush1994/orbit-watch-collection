from django.contrib.auth.decorators import login_required
from coupons.models import Coupon, CouponUsage
from django.utils import timezone
from django.shortcuts import render


@login_required(login_url="login")
def dashboard_coupons(request):
    now = timezone.now()
    available = Coupon.objects.filter(
        is_active=True,
        valid_from__lte=now,
    ).filter(
        valid_until__isnull=True
    ) | Coupon.objects.filter(
        is_active=True,
        valid_from__lte=now,
        valid_until__gt=now,
    )
    coupon_list = []
    for c in available.order_by("-id"):
        usage = CouponUsage.objects.filter(coupon=c, user=request.user).first()
        used = usage.used_count if usage else 0
        coupon_list.append(
            {
                "coupon": c,
                "used": used,
                "remaining": c.usage_limit - used,
                "exhausted": used >= c.usage_limit,
            }
        )

    context = {
        "coupon_list": coupon_list,
        "now": now,
    }
    return render(request, "dashboard/coupons.html", context)

