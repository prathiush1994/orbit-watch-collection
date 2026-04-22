from decimal import Decimal
from django.utils import timezone
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..models import Order, OrderProduct
from .helpers import _get_wallet


@login_required(login_url="login")
def cancel_order(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)

    if order.status not in ["New", "Accepted"]:
        messages.error(request, "This order cannot be cancelled.")
        return redirect("order_detail", order_number=order_number)

    if request.method != "POST":
        return redirect("order_detail", order_number=order_number)

    reason = request.POST.get("cancel_reason", "")

    for item in order.items.select_related("variant").all():
        if item.variant:
            item.variant.stock += item.quantity
            item.variant.save(update_fields=["stock"])

    refund_amount = Decimal("0")
    now = timezone.now()

    for item in order.items.filter(item_status="Active").select_related("variant"):
        if item.variant:
            item.variant.stock += item.quantity
            item.variant.save(update_fields=["stock"])
        refund_amount += item.product_price * item.quantity
        item.item_status = "Cancelled"
        item.cancelled_qty = item.quantity
        item.cancel_reason = reason
        item.cancelled_at = now
        item.save(
            update_fields=[
                "item_status",
                "cancelled_qty",
                "cancel_reason",
                "cancelled_at",
            ]
        )
    wallet_refund = order.wallet_used or Decimal("0")
    payment = order.payment
    if (
        payment
        and payment.payment_method == "RAZORPAY"
        and payment.status == "Completed"
    ):
        online = Decimal(str(payment.amount_paid))
        if online > 0:
            wallet_refund += online
            payment.status = "Refunded"
            payment.save(update_fields=["status"])
    if wallet_refund > 0:
        wallet = _get_wallet(request.user)
        wallet.credit(
            amount=wallet_refund,
            description=f"Refund — cancelled Order #{order.order_number}",
            order=order,
        )
        messages.success(
            request, f"Order cancelled. ₹{wallet_refund} refunded to your wallet."
        )
    else:
        messages.success(request, "Order cancelled. Stock has been restored.")

    order.status = "Cancelled"
    order.cancel_reason = reason
    order.save(update_fields=["status", "cancel_reason"])

    return redirect("order_detail", order_number=order_number)


@login_required(login_url="login")
def return_order(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)

    if order.status != "Delivered":
        messages.error(request, "Only delivered orders can be returned.")
        return redirect("order_detail", order_number=order_number)

    if request.method != "POST":
        return redirect("order_detail", order_number=order_number)

    reason = request.POST.get("return_reason", "").strip()
    if not reason:
        messages.error(request, "Please select a return reason.")
        return redirect("order_detail", order_number=order_number)

    now = timezone.now()
    for item in order.items.filter(item_status="Active"):
        item.item_status = "Return Requested"
        item.return_reason = reason
        item.return_requested_at = now
        item.save(update_fields=["item_status", "return_reason", "return_requested_at"])

    order.status = "Return Requested"
    order.return_reason = reason
    order.save(update_fields=["status", "return_reason"])

    messages.success(
        request,
        "Return request submitted. Once approved, your refund will be "
        "credited to your wallet and stock will be restored automatically.",
    )
    return redirect("order_detail", order_number=order_number)


@login_required(login_url="login")
def return_item(request, order_number, item_id):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    item = get_object_or_404(OrderProduct, id=item_id, order=order)

    if order.status != "Delivered":
        messages.error(request, "Only delivered orders can have items returned.")
        return redirect("order_detail", order_number=order_number)

    if item.item_status != "Active":
        messages.error(
            request,
            "This item has already been cancelled or a return has been requested.",
        )
        return redirect("order_detail", order_number=order_number)

    if request.method != "POST":
        return redirect("order_detail", order_number=order_number)

    try:
        return_qty = int(request.POST.get("return_qty", item.active_qty()))
    except (ValueError, TypeError):
        return_qty = item.active_qty()

    active_qty = item.active_qty()
    if return_qty < 1 or return_qty > active_qty:
        messages.error(
            request, f"Invalid quantity. You can return 1 to {active_qty} unit(s)."
        )
        return redirect("order_detail", order_number=order_number)

    reason = request.POST.get("return_reason", "").strip()
    if not reason:
        messages.error(request, "Please select a reason for return.")
        return redirect("order_detail", order_number=order_number)

    item.returned_qty += return_qty
    item.return_reason = reason
    item.return_requested_at = timezone.now()
    if item.returned_qty >= item.active_qty() + return_qty:
        item.item_status = "Return Requested"
    else:
        item.item_status = "Return Requested"
    item.save(
        update_fields=[
            "returned_qty",
            "return_reason",
            "return_requested_at",
            "item_status",
        ]
    )

    active_non_returned = order.items.filter(item_status="Active").count()
    if active_non_returned == 0:
        order.status = "Return Requested"
        order.save(update_fields=["status"])

    messages.success(
        request,
        f'Return request submitted for {return_qty}x "{item.product_name}". '
        "Refund will be credited to your wallet once admin approves.",
    )
    return redirect("order_detail", order_number=order_number)


@login_required(login_url="login")
def cancel_item(request, order_number, item_id):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    item = get_object_or_404(OrderProduct, id=item_id, order=order)

    if order.status not in ["New", "Accepted"]:
        messages.error(request, "Items in this order cannot be cancelled now.")
        return redirect("order_detail", order_number=order_number)

    if item.item_status != "Active":
        messages.error(request, "This item has already been cancelled or returned.")
        return redirect("order_detail", order_number=order_number)

    if request.method != "POST":
        return redirect("order_detail", order_number=order_number)

    try:
        cancel_qty = int(request.POST.get("cancel_qty", item.active_qty()))
    except (ValueError, TypeError):
        cancel_qty = item.active_qty()

    active_qty = item.active_qty()
    if cancel_qty < 1 or cancel_qty > active_qty:
        messages.error(
            request, f"Invalid quantity. You can cancel 1 to {active_qty} unit(s)."
        )
        return redirect("order_detail", order_number=order_number)

    reason = request.POST.get("cancel_reason", "")

    if item.variant:
        item.variant.stock += cancel_qty
        item.variant.save(update_fields=["stock"])

    item_unit_refund = item.product_price * cancel_qty

    order_subtotal = sum(i.product_price * i.quantity for i in order.items.all())
    if order_subtotal > 0:
        proportion = item_unit_refund / order_subtotal
    else:
        proportion = Decimal("0")

    wallet_to_refund = round((order.wallet_used or Decimal("0")) * proportion, 2)
    payment = order.payment
    online_to_refund = Decimal("0")
    if (
        payment
        and payment.payment_method == "RAZORPAY"
        and payment.status == "Completed"
    ):
        online_to_refund = round(Decimal(str(payment.amount_paid)) * proportion, 2)

    total_refund = wallet_to_refund + online_to_refund

    item.cancelled_qty += cancel_qty
    item.cancel_reason = reason
    item.cancelled_at = timezone.now()
    if item.cancelled_qty >= item.quantity:
        item.item_status = "Cancelled"
    item.save(
        update_fields=["cancelled_qty", "cancel_reason", "cancelled_at", "item_status"]
    )

    if total_refund > 0:
        wallet = _get_wallet(request.user)
        wallet.credit(
            amount=total_refund,
            description=f"Refund — cancelled {cancel_qty}x {item.product_name} "
            f"from Order #{order.order_number}",
            order=order,
        )
        messages.success(
            request,
            f'{cancel_qty} unit(s) of "{item.product_name}" cancelled. '
            f"₹{total_refund} refunded to your wallet.",
        )
    else:
        messages.success(
            request, f'{cancel_qty} unit(s) of "{item.product_name}" cancelled.'
        )

    if order.all_items_cancelled():
        order.status = "Cancelled"
        order.cancel_reason = "All items cancelled individually"
        order.save(update_fields=["status", "cancel_reason"])
        if (
            payment
            and payment.payment_method == "RAZORPAY"
            and payment.status == "Completed"
        ):
            payment.status = "Refunded"
            payment.save(update_fields=["status"])

    return redirect("order_detail", order_number=order_number)
