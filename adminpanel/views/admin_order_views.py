from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.admin.views.decorators import staff_member_required

from orders.models import Order, OrderProduct


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN ORDER LIST
# ─────────────────────────────────────────────────────────────────────────────

@staff_member_required(login_url='admin_login')
def admin_order_list(request):
    orders = Order.objects.filter(is_ordered=True).select_related('user', 'payment').order_by('-created_at')

    # ── Search ───────────────────────────────────────────────
    q = request.GET.get('q', '').strip()
    if q:
        orders = orders.filter(
            Q(order_number__icontains=q) |
            Q(full_name__icontains=q)    |
            Q(user__email__icontains=q)  |
            Q(phone__icontains=q)
        )

    # ── Status filter ────────────────────────────────────────
    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        orders = orders.filter(status=status_filter)

    # ── Sort ─────────────────────────────────────────────────
    sort = request.GET.get('sort', '-created_at')
    VALID_SORTS = {
        'created_at':   'created_at',
        '-created_at':  '-created_at',
        'order_total':  'order_total',
        '-order_total': '-order_total',
    }
    orders = orders.order_by(VALID_SORTS.get(sort, '-created_at'))

    # ── Pagination ───────────────────────────────────────────
    paginator   = Paginator(orders, 15)          # 15 orders per page
    page_number = request.GET.get('page', 1)
    page_obj    = paginator.get_page(page_number)

    # Status choices for filter dropdown
    STATUS_CHOICES = [
        'New', 'Accepted', 'Shipped', 'Delivered',
        'Cancelled', 'Return Requested', 'Returned',
    ]

    context = {
        'page_obj'      : page_obj,
        'q'             : q,
        'status_filter' : status_filter,
        'sort'          : sort,
        'status_choices': STATUS_CHOICES,
        'total_count'   : orders.count(),
    }
    return render(request, 'adminpanel/admin_order_list.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN ORDER DETAIL + STATUS CHANGE
# ─────────────────────────────────────────────────────────────────────────────

@staff_member_required(login_url='admin_login')
def admin_order_detail(request, order_number):
    order       = get_object_or_404(Order, order_number=order_number)
    order_items = OrderProduct.objects.filter(order=order).select_related('variant')

    STATUS_CHOICES = [
        'New', 'Accepted', 'Shipped', 'Delivered',
        'Cancelled', 'Return Requested', 'Returned',
    ]

    if request.method == 'POST':
        new_status = request.POST.get('status', '').strip()

        if new_status not in STATUS_CHOICES:
            messages.error(request, 'Invalid status selected.')
            return redirect('admin_order_detail', order_number=order_number)

        old_status = order.status

        # If cancelling from admin side — restore stock
        if new_status == 'Cancelled' and old_status not in ['Cancelled', 'Returned']:
            for item in order.items.all():
                if item.variant:
                    item.variant.stock += item.quantity
                    item.variant.save()

        order.status = new_status
        order.save()

        messages.success(request, f'Order #{order_number} status updated to "{new_status}".')
        return redirect('admin_order_detail', order_number=order_number)

    context = {
        'order'         : order,
        'order_items'   : order_items,
        'status_choices': STATUS_CHOICES,
    }
    return render(request, 'adminpanel/admin_order_detail.html', context)