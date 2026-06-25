from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from coupons.models import Coupon
from django.core.paginator import Paginator


@staff_member_required(login_url="admin_login")
def admin_coupon_list(request):
    coupons = Coupon.objects.all().order_by("-id")
    now = timezone.now()

    paginator = Paginator(coupons, 7)
    page = request.GET.get("page", 1)
    coupons = paginator.get_page(page)

    return render(
        request,
        "adminpanel/admin_coupon_list.html",
        {
            "coupons": coupons,
            "now": now,
        },
    )


@staff_member_required(login_url="admin_login")
def admin_coupon_add(request):
    if request.method == "POST":
        code = request.POST.get("code", "").strip().upper()
        discount_type = request.POST.get("discount_type", "percentage")
        discount = request.POST.get("discount", "0")
        min_order_amt = request.POST.get("min_order_amt", "0")
        usage_limit = request.POST.get("usage_limit", "1")
        is_active = request.POST.get("is_active") == "on"
        valid_from = request.POST.get("valid_from", "")
        valid_until = request.POST.get("valid_until", "").strip() or None

        # Validate
        if not code:
            messages.error(request, "Coupon code is required.")
            return render(
                request, "adminpanel/admin_coupon_form.html", {"action": "Add"}
            )

        if Coupon.objects.filter(code=code).exists():
            messages.error(request, f'Coupon "{code}" already exists.')
            return render(
                request, "adminpanel/admin_coupon_form.html", {"action": "Add"}
            )

        try:
            discount = float(discount)
            min_order_amt = float(min_order_amt)
            usage_limit = int(usage_limit)

            if discount_type == "percentage":
                min_order_amt = 0
                if discount < 1 or discount > 100:
                    raise ValueError("Percentage discount must be between 1 and 25.")

            elif discount_type == "fixed":
                if discount < 100 or discount > 5000:
                    raise ValueError("Fixed discount must be between ₹100 and ₹5000.")

                if min_order_amt <= discount:
                    raise ValueError(
                        "Minimum order amount must be greater than the fixed discount."
                    )

            if usage_limit < 1 or usage_limit > 3:
                raise ValueError("Uses per user must be between 1 and 3.")

        except ValueError as e:
            messages.error(request, str(e))
            return render(
                request,
                "adminpanel/admin_coupon_form.html",
                {
                    "action": "Add",
                },
            )

        try:
            if discount_type == "percentage":
                max_discount = 5000
            else:
                max_discount = None 
            
            coupon = Coupon.objects.create(
                code=code,
                discount_type=discount_type,
                discount=discount,
                max_discount=max_discount,
                min_order_amt=min_order_amt,
                usage_limit=usage_limit,
                is_active=is_active,
                valid_from=valid_from or timezone.now(),
                valid_until=valid_until,
            )
            messages.success(request, f'Coupon "{coupon.code}" created successfully.')
            return redirect("admin_coupon_list")
        except Exception as e:
            messages.error(request, f"Error creating coupon: {e}")

    return render(request, "adminpanel/admin_coupon_form.html", {"action": "Add"})


@staff_member_required(login_url="admin_login")
def admin_coupon_edit(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)

    if request.method == "POST":
        code = request.POST.get("code", "").strip().upper()
        discount_type = request.POST.get("discount_type", "percentage")
        discount = request.POST.get("discount", "0")
        min_order_amt = request.POST.get("min_order_amt", "0")
        usage_limit = request.POST.get("usage_limit", "1")
        is_active = request.POST.get("is_active") == "on"
        valid_from = request.POST.get("valid_from", "")
        valid_until = request.POST.get("valid_until", "").strip() or None

        if not code:
            messages.error(request, "Coupon code is required.")
            return render(
                request,
                "adminpanel/admin_coupon_form.html",
                {"action": "Edit", "coupon": coupon},
            )

        # Check uniqueness excluding self
        if Coupon.objects.filter(code=code).exclude(id=coupon_id).exists():
            messages.error(request, f'Coupon code "{code}" is already used.')
            return render(
                request,
                "adminpanel/admin_coupon_form.html",
                {"action": "Edit", "coupon": coupon},
            )

        try:
            discount = float(discount)
            min_order_amt = float(min_order_amt)
            usage_limit = int(usage_limit)

            if discount_type == "percentage":
                min_order_amt = 0
                if discount < 1 or discount > 100:
                    raise ValueError("Percentage discount must be between 1 and 100.")

            elif discount_type == "fixed":
                if discount < 100 or discount > 5000:
                    raise ValueError("Fixed discount must be between ₹100 and ₹5000.")

                if min_order_amt <= discount:
                    raise ValueError(
                        "Minimum order amount must be greater than the fixed discount."
                    )

            if usage_limit < 1 or usage_limit > 3:
                raise ValueError("Uses per user must be between 1 and 3.")

        except ValueError as e:
            messages.error(request, str(e))
            return render(
                request,
                "adminpanel/admin_coupon_form.html",
                {
                    "action": "Edit",
                    "coupon": coupon
                },
            )

        try:
            if discount_type == "percentage":
                coupon.max_discount = 5000
            else:
                coupon.max_discount = None
            coupon.code = code
            coupon.discount_type = discount_type
            coupon.discount = discount
            coupon.min_order_amt = min_order_amt
            coupon.usage_limit = usage_limit
            coupon.is_active = is_active

            if valid_from:
                coupon.valid_from = valid_from
            coupon.valid_until = valid_until
            coupon.save()
            messages.success(request, f'Coupon "{coupon.code}" updated.')
            return redirect("admin_coupon_list")
        except Exception as e:
            messages.error(request, f"Error updating coupon: {e}")

    return render(
        request,
        "adminpanel/admin_coupon_form.html",
        {"action": "Edit", "coupon": coupon},
    )


@staff_member_required(login_url="admin_login")
def admin_coupon_toggle(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)
    coupon.is_active = not coupon.is_active
    coupon.save(update_fields=["is_active"])
    state = "activated" if coupon.is_active else "deactivated"
    messages.success(request, f'Coupon "{coupon.code}" {state}.')
    return redirect("admin_coupon_list")


@staff_member_required(login_url="admin_login")
def admin_coupon_delete(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)
    if request.method == "POST":
        code = coupon.code
        coupon.delete()
        messages.success(request, f'Coupon "{code}" deleted.')
        return redirect("admin_coupon_list")
    return redirect("admin_coupon_list")
