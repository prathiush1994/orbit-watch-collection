from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import datetime

from carts.models import CartItem
from accounts.models import UserAddress
from .models import Payment, Order, OrderProduct


@login_required(login_url='login')
def checkout(request):
    """
    Shows:
    - User's saved addresses (selectable, default pre-selected)
    - Cart items with image, qty, subtotal
    - Price breakdown: subtotal, tax, grand total
    - Payment: COD active, Razorpay disabled
    """
    # ── Cart items ──────────────────────────────────────────────────────
    cart_items = CartItem.objects.filter(
        cart__cart_id=_get_cart_id(request),
        is_active=True
    )

    if not cart_items.exists():
        messages.warning(request, 'Your cart is empty.')
        return redirect('cart')

    # ── Price calculation ────────────────────────────────────────────────
    total = sum(item.sub_total() for item in cart_items)
    tax   = round(total * 18 / 100, 2)
    grand_total = round(total + tax, 2)

    # ── Addresses ────────────────────────────────────────────────────────
    addresses       = UserAddress.objects.filter(user=request.user)
    default_address = addresses.filter(is_default=True).first()

    context = {
        'cart_items'      : cart_items,
        'total'           : total,
        'tax'             : tax,
        'grand_total'     : grand_total,
        'addresses'       : addresses,
        'default_address' : default_address,
    }
    return render(request, 'orders/checkout.html', context)


@login_required(login_url='login')
def place_order(request):
    """
    POST only.
    1. Validates address selected
    2. Creates Payment (COD, Pending)
    3. Creates Order with address snapshot
    4. Creates OrderProduct for each cart item
    5. Reduces stock
    6. Clears cart
    7. Redirects to order_complete
    """
    if request.method != 'POST':
        return redirect('checkout')

    # ── Get address ──────────────────────────────────────────────────────
    address_id = request.POST.get('address_id')
    if not address_id:
        messages.error(request, 'Please select a delivery address.')
        return redirect('checkout')

    try:
        address = UserAddress.objects.get(id=address_id, user=request.user)
    except UserAddress.DoesNotExist:
        messages.error(request, 'Invalid address selected.')
        return redirect('checkout')

    # ── Cart items ───────────────────────────────────────────────────────
    cart_items = CartItem.objects.filter(
        cart__cart_id=_get_cart_id(request),
        is_active=True
    )

    if not cart_items.exists():
        messages.warning(request, 'Your cart is empty.')
        return redirect('cart')

    # ── Price calculation ────────────────────────────────────────────────
    total       = sum(item.sub_total() for item in cart_items)
    tax         = round(total * 18 / 100, 2)
    grand_total = round(total + tax, 2)

    # ── Create Payment ───────────────────────────────────────────────────
    payment = Payment.objects.create(
        user           = request.user,
        payment_method = 'COD',
        amount_paid    = str(grand_total),
        status         = 'Pending',
        transaction_id = '',        # Razorpay fills this later
    )

    # ── Generate order number ─────────────────────────────────────────────
    # Format: ORB + YYYYMMDD + user_id padded + last 3 of payment id
    today      = datetime.date.today().strftime('%Y%m%d')
    order_number = f"ORB{today}{request.user.id:04d}{payment.id:03d}"

    # ── Create Order ──────────────────────────────────────────────────────
    order = Order.objects.create(
        user         = request.user,
        payment      = payment,
        full_name    = address.full_name,
        phone        = address.phone,
        address_line = address.address_line,
        city         = address.city,
        state        = address.state,
        pincode      = address.pincode,
        address_type = address.address_type,
        order_number = order_number,
        order_total  = grand_total,
        tax          = tax,
        status       = 'New',
        is_ordered   = True,
    )

    # ── Create OrderProduct + reduce stock ───────────────────────────────
    for item in cart_items:
        OrderProduct.objects.create(
            order         = order,
            user          = request.user,
            variant       = item.variant,
            product_name  = item.variant.product.product_name,
            color_name    = item.variant.color_name,
            product_price = item.variant.price,
            quantity      = item.quantity,
            ordered       = True,
        )
        # Reduce stock
        item.variant.stock -= item.quantity
        item.variant.save()

    # ── Clear cart ────────────────────────────────────────────────────────
    cart_items.delete()

    return redirect('order_complete', order_number=order_number)


@login_required(login_url='login')
def order_complete(request, order_number):
    """Order success page."""
    try:
        order = Order.objects.get(order_number=order_number, user=request.user)
    except Order.DoesNotExist:
        return redirect('home')

    order_items = OrderProduct.objects.filter(order=order)

    context = {
        'order'       : order,
        'order_items' : order_items,
    }
    return render(request, 'orders/order_complete.html', context)


# ── Helper ───────────────────────────────────────────────────────────────────
def _get_cart_id(request):
    """Get cart_id from session — same logic as your carts app."""
    cart_id = request.session.session_key
    if not cart_id:
        request.session.create()
        cart_id = request.session.session_key
    return cart_id