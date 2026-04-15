from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.admin.views.decorators import staff_member_required

from orders.models import Order, OrderProduct
from wallet.models import Wallet


STATUS_CHOICES = [
    'New', 'Accepted', 'Shipped', 'Delivered',
    'Cancelled', 'Return Requested', 'Returned',
]


# ─────────────────────────────────────────────────────────────────────────────
# ORDER LIST
# ─────────────────────────────────────────────────────────────────────────────
@staff_member_required(login_url='admin_login')
def admin_order_list(request):
    orders = Order.objects.filter(is_ordered=True).select_related('user', 'payment').order_by('-created_at')

    q = request.GET.get('q', '').strip()
    if q:
        orders = orders.filter(
            Q(order_number__icontains=q) |
            Q(full_name__icontains=q)    |
            Q(user__email__icontains=q)  |
            Q(phone__icontains=q)
        )

    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        orders = orders.filter(status=status_filter)

    sort = request.GET.get('sort', '-created_at')
    VALID_SORTS = {
        'created_at':   'created_at',
        '-created_at':  '-created_at',
        'order_total':  'order_total',
        '-order_total': '-order_total',
    }
    orders = orders.order_by(VALID_SORTS.get(sort, '-created_at'))

    paginator   = Paginator(orders, 10)
    page_number = request.GET.get('page', 1)
    page_obj    = paginator.get_page(page_number)

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
# ORDER DETAIL + STATUS CHANGE
# ─────────────────────────────────────────────────────────────────────────────
@staff_member_required(login_url='admin_login')
def admin_order_detail(request, order_number):
    order       = get_object_or_404(Order, order_number=order_number)
    order_items = OrderProduct.objects.filter(order=order).select_related('variant')

    if request.method == 'POST':
        new_status = request.POST.get('status', '').strip()

        if new_status not in STATUS_CHOICES:
            messages.error(request, 'Invalid status selected.')
            return redirect('admin_order_detail', order_number=order_number)

        old_status = order.status

        # ── Restore stock when admin cancels ─────────────
        if new_status == 'Cancelled' and old_status not in ['Cancelled', 'Returned']:
            for item in order.items.select_related('variant').all():
                if item.variant:
                    item.variant.stock += item.quantity
                    item.variant.save(update_fields=['stock'])
            # Wallet refund on admin cancel
            _process_refund(request, order, reason='Admin cancelled order')

        # ── Approve return: restock + wallet refund ───────
        if new_status == 'Returned' and old_status == 'Return Requested':
            for item in order.items.select_related('variant').all():
                if item.variant:
                    item.variant.stock += item.quantity
                    item.variant.save(update_fields=['stock'])
            _process_refund(request, order, reason='Return approved by admin')

        order.status = new_status
        order.save(update_fields=['status'])

        # ── Update payment status for COD ─────────────────
        if order.payment and order.payment.payment_method == 'COD':
            if new_status == 'Delivered':
                order.payment.status = 'Completed'
            elif new_status in ['Cancelled', 'Returned']:
                order.payment.status = 'Refunded'
            else:
                order.payment.status = 'Pending'
            order.payment.save(update_fields=['status'])

        messages.success(request, f'Order #{order_number} status → "{new_status}".')
        return redirect('admin_order_detail', order_number=order_number)

    context = {
        'order'         : order,
        'order_items'   : order_items,
        'status_choices': STATUS_CHOICES,
    }
    return render(request, 'adminpanel/admin_order_detail.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL — process wallet refund
# Called on cancel (immediate) and return approval
# ─────────────────────────────────────────────────────────────────────────────
def _process_refund(request, order, reason=''):
    refund_amount = Decimal('0')
    parts         = []

    wallet_paid = order.wallet_used or Decimal('0')
    if wallet_paid > 0:
        refund_amount += wallet_paid
        parts.append(f'wallet ₹{wallet_paid}')

    payment = order.payment
    if payment and payment.payment_method in ['RAZORPAY', 'COD'] \
            and payment.status == 'Completed':
        online_paid = Decimal(str(payment.amount_paid))
        if online_paid > 0:
            refund_amount += online_paid
            parts.append(f'{payment.payment_method} ₹{online_paid}')
            payment.status = 'Refunded'
            payment.save(update_fields=['status'])

    if refund_amount > 0 and order.user:
        wallet, _ = Wallet.objects.get_or_create(user=order.user)
        desc = f'{reason} — Order #{order.order_number}'
        if parts:
            desc += f' ({", ".join(parts)})'
        wallet.credit(amount=refund_amount, description=desc, order=order)
        messages.info(
            request,
            f'₹{refund_amount} refunded to {order.user.email}\'s wallet.'
        )
