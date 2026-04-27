from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from orders.models import Order, OrderProduct
from wallet.models import Wallet

STATUS_CHOICES = [
    "New",
    "Accepted",
    "Shipped",
    "Delivered",
    "Cancelled",
    "Return Requested",
    "Returned",
]


@staff_member_required(login_url="admin_login")
def admin_order_list(request):
    orders = (
        Order.objects.filter(is_ordered=True)
        .select_related("user", "payment")
        .order_by("-created_at")
    )
    q = request.GET.get("q", "").strip()
    if q:
        orders = orders.filter(
            Q(order_number__icontains=q)
            | Q(full_name__icontains=q)
            | Q(user__email__icontains=q)
            | Q(phone__icontains=q)
        )
    status_filter = request.GET.get("status", "").strip()
    if status_filter:
        orders = orders.filter(status=status_filter)

    sort = request.GET.get("sort", "-created_at")
    VALID = {
        "created_at": "created_at",
        "-created_at": "-created_at",
        "order_total": "order_total",
        "-order_total": "-order_total",
    }
    orders = orders.order_by(VALID.get(sort, "-created_at"))
    paginator = Paginator(orders, 10)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    return render(
        request,
        "adminpanel/admin_order_list.html",
        {
            "page_obj": page_obj,
            "q": q,
            "status_filter": status_filter,
            "sort": sort,
            "status_choices": STATUS_CHOICES,
            "total_count": orders.count(),
        },
    )


@staff_member_required(login_url="admin_login")
def admin_order_detail(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    order_items = OrderProduct.objects.filter(order=order).select_related(
        "variant", "variant__product"
    )

    if request.method == "POST":
        new_status = request.POST.get("status", "").strip()
        if new_status not in STATUS_CHOICES:
            messages.error(request, "Invalid status.")
            return redirect("admin_order_detail", order_number=order_number)

        old_status = order.status

        # ── Admin cancels the whole order ─────────────────
        if new_status == "Cancelled" and old_status not in ["Cancelled", "Returned"]:
            for item in order.items.filter(item_status="Active").select_related(
                "variant"
            ):
                if item.variant:
                    item.variant.stock += item.quantity
                    item.variant.save(update_fields=["stock"])
                item.item_status = "Cancelled"
                item.cancelled_qty = item.quantity
                item.cancelled_at = timezone.now()
                item.save(
                    update_fields=["item_status", "cancelled_qty", "cancelled_at"]
                )
            _process_refund(request, order, "Admin cancelled order")

        # ── Admin approves ALL pending return items ────────
        if new_status == "Returned" and old_status == "Return Requested":
            for item in order.items.filter(
                item_status="Return Requested"
            ).select_related("variant"):
                qty = item.returned_qty or item.quantity
                if item.variant:
                    item.variant.stock += qty
                    item.variant.save(update_fields=["stock"])
                item.item_status = "Returned"
                item.save(update_fields=["item_status"])
            _process_refund(request, order, "Return approved by admin")

        order.status = new_status
        order.save(update_fields=["status"])

        # ── Payment status sync ────────────────────────────
        if order.payment:
            pm = order.payment.payment_method
            if new_status == "Delivered" and pm == "COD":
                order.payment.status = "Completed"
                order.payment.save(update_fields=["status"])
            elif new_status in ["Cancelled", "Returned"]:
                order.payment.status = "Refunded"
                order.payment.save(update_fields=["status"])

        messages.success(request, f'Order #{order_number} updated to "{new_status}".')
        return redirect("admin_order_detail", order_number=order_number)

    # ── Count items needing action ─────────────────────────
    pending_returns = order_items.filter(item_status="Return Requested").count()

    return render(
        request,
        "adminpanel/admin_order_detail.html",
        {
            "order": order,
            "order_items": order_items,
            "status_choices": STATUS_CHOICES,
            "pending_returns": pending_returns,
        },
    )


@staff_member_required(login_url="admin_login")
def admin_approve_item_return(request, order_number, item_id):
    order = get_object_or_404(Order, order_number=order_number)
    item = get_object_or_404(OrderProduct, id=item_id, order=order)

    if item.item_status != "Return Requested":
        messages.error(request, f'Item "{item.product_name}" is not pending return.')
        return redirect("admin_order_detail", order_number=order_number)

    if request.method != "POST":
        return redirect("admin_order_detail", order_number=order_number)

    return_qty = item.returned_qty or item.quantity

    if item.variant and hasattr(item.variant, "inventory"):
        item.variant.inventory.add_stock(
            qty=return_qty,
            reason="order_cancel",
            updated_by=request.user,
            note=f"Return approved for order {order.order_number}",
        )

    # 2. Proportional wallet refund based on item value vs order total
    order_subtotal = sum(i.product_price * i.quantity for i in order.items.all())
    item_value = item.product_price * return_qty
    proportion = (item_value / order_subtotal) if order_subtotal > 0 else Decimal("0")

    wallet_portion = round((order.wallet_used or Decimal("0")) * proportion, 2)
    online_portion = Decimal("0")
    payment = order.payment

    if (
        payment
        and payment.payment_method in ["RAZORPAY", "COD"]
        and payment.status in ["Completed", "Pending"]
    ):
        online_portion = round(Decimal(str(payment.amount_paid)) * proportion, 2)

    total_refund = wallet_portion + online_portion

    # 3. Update item status → Returned
    item.item_status = "Returned"
    item.save(update_fields=["item_status"])

    # 4. Credit wallet
    if total_refund > 0 and order.user:
        wallet, _ = Wallet.objects.get_or_create(user=order.user)
        wallet.credit(
            amount=total_refund,
            description=f"Return approved — {return_qty}× {item.product_name} "
            f"(Order #{order.order_number})",
            order=order,
        )
        messages.success(
            request,
            f'✓ Return approved for "{item.product_name}". '
            f"₹{total_refund} refunded to {order.user.email}'s wallet.",
        )
    else:
        messages.success(request, f'✓ Return approved for "{item.product_name}".')

    # 5. Check if ALL items are now Returned or Cancelled
    #    If so → set order status to Returned
    still_active = order.items.filter(item_status="Active").exists()
    still_pending = order.items.filter(item_status="Return Requested").exists()

    if not still_active and not still_pending:
        order.status = "Returned"
        order.save(update_fields=["status"])
        if payment and payment.status not in ["Refunded"]:
            payment.status = "Refunded"
            payment.save(update_fields=["status"])
        messages.info(request, "All items returned — order marked as Returned.")

    # 6. If some items still Active (partial return) → keep order Delivered
    #    The order stays at whatever status it was (Delivered or Return Requested)
    elif still_active and not still_pending:
        # All return requests processed, some items still delivered normally
        order.status = "Delivered"
        order.save(update_fields=["status"])
        messages.info(
            request, "Partial return complete. Remaining items stay as Delivered."
        )

    return redirect("admin_order_detail", order_number=order_number)


def _process_refund(request, order, reason=""):
    refund_amount = Decimal("0")
    parts = []

    wallet_paid = order.wallet_used or Decimal("0")
    if wallet_paid > 0:
        refund_amount += wallet_paid
        parts.append(f"wallet ₹{wallet_paid}")

    payment = order.payment
    if (
        payment
        and payment.payment_method in ["RAZORPAY", "COD"]
        and payment.status in ["Completed", "Pending"]
    ):
        paid = Decimal(str(payment.amount_paid))
        if paid > 0:
            refund_amount += paid
            parts.append(f"{payment.payment_method} ₹{paid}")
            payment.status = "Refunded"
            payment.save(update_fields=["status"])

    if refund_amount > 0 and order.user:
        wallet, _ = Wallet.objects.get_or_create(user=order.user)
        desc = f"{reason} — Order #{order.order_number}"
        if parts:
            desc += f' ({", ".join(parts)})'
        wallet.credit(amount=refund_amount, description=desc, order=order)
        messages.info(
            request, f"₹{refund_amount} refunded to {order.user.email}'s wallet."
        )
