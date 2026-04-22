from decimal import Decimal
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from orders.models import Order
from wallet.models import Wallet


@staff_member_required
def approve_return(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)

    if order.status != "Return Requested":
        messages.error(request, 'This order is not in "Return Requested" state.')
        return redirect("adminpanel_order_detail", order_number=order_number)

    for item in order.items.select_related("variant").all():
        if item.variant:
            item.variant.stock += item.quantity
            item.variant.save(update_fields=["stock"])

    refund_amount = Decimal("0")
    parts = []

    wallet_paid = order.wallet_used or Decimal("0")
    if wallet_paid > 0:
        refund_amount += wallet_paid
        parts.append(f"wallet ₹{wallet_paid}")

    payment = order.payment
    if payment and payment.payment_method in ["RAZORPAY", "COD"]:
        online_paid = Decimal(str(payment.amount_paid))
        if online_paid > 0:
            refund_amount += online_paid
            parts.append(f"{payment.payment_method} ₹{online_paid}")
            payment.status = "Refunded"
            payment.save(update_fields=["status"])

    if refund_amount > 0 and order.user:
        wallet, _ = Wallet.objects.get_or_create(user=order.user)
        wallet.credit(
            amount=refund_amount,
            description=f'Return approved — Order #{order.order_number} ({", ".join(parts)})',
            order=order,
        )

    # 3. Update order status
    order.status = "Returned"
    order.save(update_fields=["status"])

    messages.success(
        request,
        f"Return approved for Order #{order_number}. "
        f"₹{refund_amount} refunded to wallet and stock restored.",
    )
    return redirect("adminpanel_order_detail", order_number=order_number)
