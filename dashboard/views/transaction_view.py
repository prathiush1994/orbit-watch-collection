from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from orders.models import Payment, Order


@login_required(login_url="login")
def transactions(request):
    user_payments = Payment.objects.filter(
        user=request.user).order_by("-created_at")
    return render(
        request,
        "dashboard/transactions.html",
        {
            "payments": user_payments,
        },
    )


@login_required(login_url="login")
def returns(request):
    returned_orders = Order.objects.filter(
        user=request.user,
        status__in=[
            "Return Requested",
            "Returned",
            "Cancelled"]
    )
    return render(
        request,
        "dashboard/returns.html",
        {
            "orders": returned_orders,
        },
    )
