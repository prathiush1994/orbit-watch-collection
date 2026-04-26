
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from wallet.models import Wallet
from orders.models import Coupon, CouponUsage
from django.utils import timezone
from accounts.models import UserAddress


@login_required(login_url="login")
def dashboard_wallet(request):
    wallet, _ = Wallet.objects.get_or_create(user=request.user)

    transactions = wallet.transactions.select_related("order").all()[:50]

    # Stats
    total_credited = sum(
        t.amount for t in wallet.transactions.filter(txn_type="credit")
    )
    total_debited = sum(t.amount for t in wallet.transactions.filter(txn_type="debit"))

    context = {
        "wallet": wallet,
        "transactions": transactions,
        "total_credited": total_credited,
        "total_debited": total_debited,
    }
    return render(request, "dashboard/wallet.html", context)


@login_required(login_url="login")
def dashboard_coupons(request):
    now = timezone.now()

    # All active, not expired coupons
    available = Coupon.objects.filter(
        is_active=True,
        valid_from__lte=now,
    ).filter(
        # valid_until is null (no expiry) OR still in future
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


@login_required(login_url="login")
def address(request):
    addresses = UserAddress.objects.filter(user=request.user)
    return render(request, "dashboard/address.html", {"addresses": addresses})

