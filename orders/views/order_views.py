from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from ..models import Order


@login_required(login_url='login')
def order_detail(request, order_number):
    order       = get_object_or_404(Order, order_number=order_number, user=request.user)
    order_items = order.items.select_related('variant', 'variant__product').all()
    return render(request, 'orders/order_detail.html', {
        'order': order, 'order_items': order_items,
    })

@login_required(login_url='login')
def my_orders(request):
    orders = Order.objects.filter(
        user=request.user, is_ordered=True
    ).select_related('payment').prefetch_related('items')
    return render(request, 'dashboard/orders.html', {'orders': orders})

