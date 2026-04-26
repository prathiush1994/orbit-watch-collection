from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required


@login_required(login_url="login")
def orders(request):
    return redirect("my_orders")


@login_required(login_url="login")
def transactions(request):
    """Shows all payments made by this user."""
    from orders.models import Payment

    user_payments = Payment.objects.filter(user=request.user).order_by("-created_at")
    return render(
        request,
        "dashboard/transactions.html",
        {
            "payments": user_payments,
        },
    )


@login_required(login_url="login")
def returns(request):
    """Shows orders with return/cancelled status."""
    from orders.models import Order

    returned_orders = Order.objects.filter(
        user=request.user, status__in=["Return Requested", "Returned", "Cancelled"]
    )
    return render(
        request,
        "dashboard/returns.html",
        {
            "orders": returned_orders,
        },
    )

