from decimal import Decimal

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect

from orders.models import Order
from wallet.models import Wallet
from orders.views.helpers import update_order_totals


@staff_member_required
def approve_return(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    if order.status != "Return Requested":
        messages.error(
            request, 'This order is not in "Return Requested" state.'
        )
        return redirect("adminpanel_order_detail", order_number=order_number)
    try:
        with transaction.atomic():

            refund_amount = Decimal("0")
            item_price = Decimal("0")
            order_subtotal = Decimal("0")

            for i in order.items.all():
                order_subtotal += i.product_price * i.quantity
            return_items = order.items.filter(item_status="Return Requested")
            for item in return_items:
                item_price += (item.pending_return_qty * item.product_price)
            if order_subtotal > 0:
                share = item_price / order_subtotal
            else:
                raise ValueError("Order subtotal cannot be zero.")

            coupon_discount = round(order.coupon_discount * share, 2)
            referral_discount = round(order.referral_discount * share, 2)
            amount_total = round(
                item_price - coupon_discount - referral_discount, 2)
            tax_amount = round(Decimal("0.18") * amount_total, 2)
            refund_amount = amount_total + tax_amount
            if refund_amount <= 0:
                raise ValueError("Invalid refund amount.")
            if refund_amount > order.order_total:
                raise ValueError("Refund amount exceeds current order total.")

            for item in return_items:
                if item.variant:
                    item.variant.inventory.add_stock(
                        qty=item.pending_return_qty,
                        reason=item.return_reason,
                        updated_by=request.user,
                    )
                item.returned_qty += item.pending_return_qty
                item.pending_return_qty = 0
                if item.active_qty() > 0:
                    item.item_status = "Active"
                else:
                    item.item_status = "Returned"
                item.save(update_fields=[
                    "returned_qty", "pending_return_qty", "item_status"
                ])
            wallet, _ = Wallet.objects.get_or_create(user=order.user)
            wallet.credit(
                amount=refund_amount,
                description=f"Return approved — Order #{order.order_number}",
                order=order,
            )
            update_order_totals(order)
            if order.all_items_returned():
                order.status = "Returned"
                order.save(update_fields=["status"])
    except Exception as e:
        messages.error(request, str(e))
        return redirect("adminpanel_order_detail", order_number=order_number)
    messages.success(
        request, f"Return approved. ₹{refund_amount} refunded to wallet."
    )
    return redirect("adminpanel_order_detail", order_number=order_number)
