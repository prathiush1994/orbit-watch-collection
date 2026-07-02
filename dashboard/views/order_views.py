from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from orders.models import Order


@login_required(login_url="login")
def orders(request):
    orders = (
        Order.objects.filter(user=request.user, is_ordered=True)
        .select_related("payment")
        .prefetch_related("items")
    )
    return render(request, "dashboard/orders.html", {"orders": orders})


@login_required(login_url="login")
def order_detail(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    order_items = order.items.select_related(
        "variant", "variant__product").all()
    subtotal = sum(
        item.product_price * item.active_qty()
        for item in order_items
    )
    active_items = sum(
        1 for item in order_items if item.active_qty() > 0
    )
    return render(
        request,
        "dashboard/order_detail.html",
        {
            "order": order,
            "order_items": order_items,
            "subtotal": subtotal,
            "active_items": active_items,
        },
    )


