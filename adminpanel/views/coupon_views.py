from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone

from orders.models import Coupon


# ─────────────────────────────────────────────────────────────────────────────
# COUPON LIST
# ─────────────────────────────────────────────────────────────────────────────
@staff_member_required(login_url='admin_login')
def admin_coupon_list(request):
    coupons = Coupon.objects.all().order_by('-id')
    now     = timezone.now()
    return render(request, 'adminpanel/admin_coupon_list.html', {
        'coupons': coupons,
        'now'    : now,
    })


# ─────────────────────────────────────────────────────────────────────────────
# ADD COUPON
# ─────────────────────────────────────────────────────────────────────────────
@staff_member_required(login_url='admin_login')
def admin_coupon_add(request):
    if request.method == 'POST':
        code            = request.POST.get('code', '').strip().upper()
        discount_type   = request.POST.get('discount_type', 'percentage')
        discount        = request.POST.get('discount', '0')
        min_order_amt   = request.POST.get('min_order_amt', '0')
        max_discount    = request.POST.get('max_discount', '').strip() or None
        usage_limit     = request.POST.get('usage_limit', '1')
        max_total_usage = request.POST.get('max_total_usage', '').strip() or None
        is_active       = request.POST.get('is_active') == 'on'
        valid_from      = request.POST.get('valid_from', '')
        valid_until     = request.POST.get('valid_until', '').strip() or None

        # Validate
        if not code:
            messages.error(request, 'Coupon code is required.')
            return render(request, 'adminpanel/admin_coupon_form.html', {'action': 'Add'})

        if Coupon.objects.filter(code=code).exists():
            messages.error(request, f'Coupon "{code}" already exists.')
            return render(request, 'adminpanel/admin_coupon_form.html', {'action': 'Add'})

        try:
            coupon = Coupon.objects.create(
                code            = code,
                discount_type   = discount_type,
                discount        = discount,
                min_order_amt   = min_order_amt,
                max_discount    = max_discount,
                usage_limit     = int(usage_limit),
                max_total_usage = int(max_total_usage) if max_total_usage else None,
                is_active       = is_active,
                valid_from      = valid_from or timezone.now(),
                valid_until     = valid_until,
            )
            messages.success(request, f'Coupon "{coupon.code}" created successfully.')
            return redirect('admin_coupon_list')
        except Exception as e:
            messages.error(request, f'Error creating coupon: {e}')

    return render(request, 'adminpanel/admin_coupon_form.html', {'action': 'Add'})


# ─────────────────────────────────────────────────────────────────────────────
# EDIT COUPON
# ─────────────────────────────────────────────────────────────────────────────
@staff_member_required(login_url='admin_login')
def admin_coupon_edit(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)

    if request.method == 'POST':
        code            = request.POST.get('code', '').strip().upper()
        discount_type   = request.POST.get('discount_type', 'percentage')
        discount        = request.POST.get('discount', '0')
        min_order_amt   = request.POST.get('min_order_amt', '0')
        max_discount    = request.POST.get('max_discount', '').strip() or None
        usage_limit     = request.POST.get('usage_limit', '1')
        max_total_usage = request.POST.get('max_total_usage', '').strip() or None
        is_active       = request.POST.get('is_active') == 'on'
        valid_from      = request.POST.get('valid_from', '')
        valid_until     = request.POST.get('valid_until', '').strip() or None

        if not code:
            messages.error(request, 'Coupon code is required.')
            return render(request, 'adminpanel/admin_coupon_form.html',
                          {'action': 'Edit', 'coupon': coupon})

        # Check uniqueness excluding self
        if Coupon.objects.filter(code=code).exclude(id=coupon_id).exists():
            messages.error(request, f'Coupon code "{code}" is already used.')
            return render(request, 'adminpanel/admin_coupon_form.html',
                          {'action': 'Edit', 'coupon': coupon})

        try:
            coupon.code            = code
            coupon.discount_type   = discount_type
            coupon.discount        = discount
            coupon.min_order_amt   = min_order_amt
            coupon.max_discount    = max_discount
            coupon.usage_limit     = int(usage_limit)
            coupon.max_total_usage = int(max_total_usage) if max_total_usage else None
            coupon.is_active       = is_active
            if valid_from:
                coupon.valid_from  = valid_from
            coupon.valid_until     = valid_until
            coupon.save()
            messages.success(request, f'Coupon "{coupon.code}" updated.')
            return redirect('admin_coupon_list')
        except Exception as e:
            messages.error(request, f'Error updating coupon: {e}')

    return render(request, 'adminpanel/admin_coupon_form.html',
                  {'action': 'Edit', 'coupon': coupon})


# ─────────────────────────────────────────────────────────────────────────────
# TOGGLE ACTIVE / INACTIVE
# ─────────────────────────────────────────────────────────────────────────────
@staff_member_required(login_url='admin_login')
def admin_coupon_toggle(request, coupon_id):
    coupon           = get_object_or_404(Coupon, id=coupon_id)
    coupon.is_active = not coupon.is_active
    coupon.save(update_fields=['is_active'])
    state = 'activated' if coupon.is_active else 'deactivated'
    messages.success(request, f'Coupon "{coupon.code}" {state}.')
    return redirect('admin_coupon_list')


# ─────────────────────────────────────────────────────────────────────────────
# DELETE COUPON
# ─────────────────────────────────────────────────────────────────────────────
@staff_member_required(login_url='admin_login')
def admin_coupon_delete(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)
    if request.method == 'POST':
        code = coupon.code
        coupon.delete()
        messages.success(request, f'Coupon "{code}" deleted.')
        return redirect('admin_coupon_list')
    return redirect('admin_coupon_list')
