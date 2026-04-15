import json
import hmac
import hashlib
import random
import string
from decimal import Decimal
import razorpay
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
import datetime
from carts.views import _get_or_create_cart
from carts.models import Cart, CartItem
from accounts.models import UserAddress
from .models import Payment, Order, OrderProduct
from wallet.models import Wallet
from .models import Order, OrderProduct, Payment, Coupon, CouponUsage

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _generate_order_number():
    while True:
        number = 'ORB' + ''.join(random.choices(string.digits, k=8))
        if not Order.objects.filter(order_number=number).exists():
            return number


def _get_wallet(user):
    wallet, _ = Wallet.objects.get_or_create(user=user)
    return wallet


def _razorpay_client():
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )


def _compute_totals(cart_items, session):
    """
    Returns a dict with all price breakdown values.
    Re-computes everything server-side — never trust hidden form fields.
    """
    subtotal    = sum(item.variant.price * item.quantity
                      for item in cart_items if item.variant.stock > 0)
    tax         = round(Decimal('0.18') * subtotal, 2)
    grand_total = round(subtotal + tax, 2)

    coupon_discount = Decimal(session.get('coupon_discount', '0'))
    coupon_code     = session.get('coupon_code', '')
    coupon_id       = session.get('coupon_id')
    after_coupon    = round(grand_total - coupon_discount, 2)

    wallet_used  = Decimal(session.get('wallet_used', '0'))
    wallet_applied = session.get('wallet_applied', False)
    final_total  = max(round(after_coupon - wallet_used, 2), Decimal('0'))

    return {
        'subtotal'       : subtotal,
        'tax'            : tax,
        'grand_total'    : grand_total,
        'coupon_discount': coupon_discount,
        'coupon_code'    : coupon_code,
        'coupon_id'      : coupon_id,
        'after_coupon'   : after_coupon,
        'wallet_used'    : wallet_used,
        'wallet_applied' : wallet_applied,
        'final_total'    : final_total,
    }


def _build_order_from_session(request, address, payment_obj, totals):
    """
    Creates Order + OrderProducts + decrements stock.
    Returns the Order instance.
    """
    order = Order.objects.create(
        user         = request.user,
        payment      = payment_obj,
        full_name    = address.full_name,
        phone        = address.phone,
        address_line = address.address_line,
        city         = address.city,
        state        = address.state,
        pincode      = address.pincode,
        address_type = address.address_type,
        order_number = _generate_order_number(),
        order_total  = totals['final_total'],
        tax          = totals['tax'],
        discount     = totals['coupon_discount'],
        coupon_code  = totals['coupon_code'],
        wallet_used  = totals['wallet_used'],
        is_ordered   = True,
    )

    # Attach coupon FK + update usage counters
    if totals['coupon_id']:
        try:
            coupon_obj = Coupon.objects.get(id=totals['coupon_id'])
            order.coupon = coupon_obj
            order.save(update_fields=['coupon'])
            usage, _ = CouponUsage.objects.get_or_create(coupon=coupon_obj, user=request.user)
            usage.used_count += 1
            usage.save()
            coupon_obj.total_usage += 1
            coupon_obj.save(update_fields=['total_usage'])
        except Coupon.DoesNotExist:
            pass

    # Deduct wallet balance
    if totals['wallet_used'] > 0:
        wallet = _get_wallet(request.user)
        wallet.debit(
            amount      = totals['wallet_used'],
            description = f'Payment for Order #{order.order_number}',
            order       = order,
        )

    # Create order items + reduce stock
    cart = _get_or_create_cart(request)
    cart_items = CartItem.objects.filter(
        cart=cart, is_active=True
    ).select_related('variant', 'variant__product')

    for item in cart_items:
        if item.variant.stock <= 0:
            continue
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
        item.variant.stock -= item.quantity
        item.variant.save(update_fields=['stock'])

    # Clear cart
    cart_items.delete()

    # Clear session
    for key in ['coupon_code', 'coupon_id', 'coupon_discount',
                'wallet_used', 'wallet_applied',
                'pending_address_id', 'pending_razorpay_order_id']:
        request.session.pop(key, None)

    return order




# ─────────────────────────────────────────────────────────────────────────────
# APPLY COUPON  (AJAX — POST)
# body: { code: "XYZ", grand_total: "1234.00" }
# ─────────────────────────────────────────────────────────────────────────────
@login_required(login_url='login')
def apply_coupon(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request.'})

    data        = json.loads(request.body)
    code        = data.get('code', '').strip().upper()
    grand_total = Decimal(str(data.get('grand_total', '0')))

    if request.session.get('coupon_code'):
        return JsonResponse({'success': False,
                             'message': 'A coupon is already applied. Remove it first.'})

    try:
        coupon = Coupon.objects.get(code=code)
    except Coupon.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Invalid coupon code.'})

    valid, msg = coupon.is_valid()
    if not valid:
        return JsonResponse({'success': False, 'message': msg})

    if grand_total < coupon.min_order_amt:
        return JsonResponse({'success': False,
                             'message': f'Minimum order ₹{coupon.min_order_amt} required.'})

    usage, _ = CouponUsage.objects.get_or_create(coupon=coupon, user=request.user)
    if usage.used_count >= coupon.usage_limit:
        return JsonResponse({'success': False,
                             'message': 'You have already used this coupon.'})

    discount   = coupon.calculate_discount(grand_total)
    after_coup = round(grand_total - discount, 2)

    request.session['coupon_code']     = coupon.code
    request.session['coupon_id']       = coupon.id
    request.session['coupon_discount'] = str(discount)

    # Recalculate wallet if already applied
    wallet_used = Decimal(request.session.get('wallet_used', '0'))
    if wallet_used > 0:
        wallet_used = min(wallet_used, after_coup)
        request.session['wallet_used'] = str(wallet_used)

    final = max(after_coup - wallet_used, Decimal('0'))

    return JsonResponse({
        'success'   : True,
        'message'   : f'Coupon "{coupon.code}" applied! You saved ₹{discount}.',
        'discount'  : str(discount),
        'after_coup': str(after_coup),
        'final'     : str(final),
    })

# ─────────────────────────────────────────────────────────────────────────────
# REMOVE COUPON  (AJAX — POST)
# body: { grand_total: "1234.00" }
# ─────────────────────────────────────────────────────────────────────────────
@login_required(login_url='login')
def remove_coupon(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request.'})

    data        = json.loads(request.body)
    grand_total = Decimal(str(data.get('grand_total', '0')))

    request.session.pop('coupon_code', None)
    request.session.pop('coupon_id', None)
    request.session.pop('coupon_discount', None)

    wallet_used = Decimal(request.session.get('wallet_used', '0'))
    if wallet_used > 0:
        wallet_used = min(wallet_used, grand_total)
        request.session['wallet_used'] = str(wallet_used)

    final = max(grand_total - wallet_used, Decimal('0'))

    return JsonResponse({
        'success'   : True,
        'message'   : 'Coupon removed.',
        'after_coup': str(grand_total),
        'final'     : str(final),
    })




# ─────────────────────────────────────────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────────────────────────────────────────

def _get_cart_id(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


# ─────────────────────────────────────────────────────────
# CHECKOUT PAGE
# ─────────────────────────────────────────────────────────
@login_required(login_url='login')
def checkout(request):
    cart       = _get_or_create_cart(request)
    cart_items = CartItem.objects.filter(
        cart=cart, is_active=True
    ).select_related('variant', 'variant__product')

    if not cart_items.exists():
        messages.warning(request, 'Your cart is empty.')
        return redirect('cart')

    total       = sum(item.variant.price * item.quantity
                      for item in cart_items if item.variant.stock > 0)
    tax         = round(Decimal('0.18') * total, 2)
    grand_total = round(total + tax, 2)

    coupon_discount = Decimal(request.session.get('coupon_discount', '0'))
    coupon_code     = request.session.get('coupon_code', '')
    after_coupon    = round(grand_total - coupon_discount, 2)

    wallet_used    = Decimal(request.session.get('wallet_used', '0'))
    wallet_applied = request.session.get('wallet_applied', False)
    final_total    = max(round(after_coupon - wallet_used, 2), Decimal('0'))

    wallet    = _get_wallet(request.user)
    addresses = UserAddress.objects.filter(user=request.user).order_by('-is_default')

    context = {
        'cart_items'     : cart_items,
        'total'          : total,
        'tax'            : tax,
        'grand_total'    : grand_total,
        'coupon_discount': coupon_discount,
        'coupon_code'    : coupon_code,
        'after_coupon'   : after_coupon,
        'wallet_balance' : wallet.balance,
        'wallet_used'    : wallet_used,
        'wallet_applied' : wallet_applied,
        'final_total'    : final_total,
        'addresses'      : addresses,
    }
    return render(request, 'orders/checkout.html', context)





# ─────────────────────────────────────────────────────────────────────────────
# CHECKOUT PAGE
# ─────────────────────────────────────────────────────────────────────────────
@login_required(login_url='login')
def checkout(request):
    cart       = _get_or_create_cart(request)
    cart_items = CartItem.objects.filter(
        cart=cart, is_active=True
    ).select_related('variant', 'variant__product')

    if not cart_items.exists():
        messages.warning(request, 'Your cart is empty.')
        return redirect('cart')

    totals    = _compute_totals(cart_items, request.session)
    wallet    = _get_wallet(request.user)
    addresses = UserAddress.objects.filter(user=request.user).order_by('-is_default')

    context = {
        'cart_items'     : cart_items,
        'total'          : totals['subtotal'],
        'tax'            : totals['tax'],
        'grand_total'    : totals['grand_total'],
        'coupon_discount': totals['coupon_discount'],
        'coupon_code'    : totals['coupon_code'],
        'after_coupon'   : totals['after_coupon'],
        'wallet_balance' : wallet.balance,
        'wallet_used'    : totals['wallet_used'],
        'wallet_applied' : totals['wallet_applied'],
        'final_total'    : totals['final_total'],
        'addresses'      : addresses,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
    }
    return render(request, 'orders/checkout.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# PLACE ORDER
# COD  → create order immediately → redirect to order_complete (COD success page)
# Razorpay → create Razorpay order → render payment popup page
# ─────────────────────────────────────────────────────────────────────────────
@login_required(login_url='login')
def place_order(request):
    if request.method != 'POST':
        return redirect('checkout')

    cart       = _get_or_create_cart(request)
    cart_items = CartItem.objects.filter(
        cart=cart, is_active=True
    ).select_related('variant', 'variant__product')

    if not cart_items.exists():
        messages.error(request, 'Your cart is empty.')
        return redirect('cart')

    address_id = request.POST.get('address_id')
    if not address_id:
        messages.error(request, 'Please select a delivery address.')
        return redirect('checkout')
    address = get_object_or_404(UserAddress, id=address_id, user=request.user)

    totals         = _compute_totals(cart_items, request.session)
    payment_method = request.POST.get('payment_method', 'COD')

    # Validate wallet balance hasn't changed between page load and submit
    if totals['wallet_used'] > 0:
        wallet = _get_wallet(request.user)
        if wallet.balance < totals['wallet_used']:
            messages.error(request, 'Your wallet balance changed. Please review your order.')
            return redirect('checkout')

    # ── COD PATH ─────────────────────────────────────────
    if payment_method == 'COD':
        pay_method = 'WALLET' if totals['final_total'] == 0 else 'COD'
        payment = Payment.objects.create(
            user           = request.user,
            payment_method = pay_method,
            amount_paid    = str(totals['final_total']),
            status         = 'Completed' if totals['final_total'] == 0 else 'Pending',
        )
        order = _build_order_from_session(request, address, payment, totals)
        return redirect('order_complete', order_number=order.order_number)

    # ── RAZORPAY PATH ─────────────────────────────────────
    if payment_method == 'RAZORPAY':
        amount_paise = int(totals['final_total'] * 100)  # Razorpay uses paise (₹1 = 100 paise)
        print("KEY_ID:", settings.RAZORPAY_KEY_ID)
        print("KEY_SECRET:", settings.RAZORPAY_KEY_SECRET)
        rz_client    = _razorpay_client()
        rz_order     = rz_client.order.create({
            'amount'         : amount_paise,
            'currency'       : 'INR',
            'payment_capture': 1,          # auto-capture on success
        })

        # Store pending details in session — used after payment callback
        request.session['pending_address_id']        = address_id
        request.session['pending_razorpay_order_id'] = rz_order['id']

        context = {
            'razorpay_key_id'  : settings.RAZORPAY_KEY_ID,
            'razorpay_order_id': rz_order['id'],
            'amount_paise'     : amount_paise,
            'final_total'      : totals['final_total'],
            'order_currency'   : 'INR',
            'user_name'        : f'{request.user.first_name} {request.user.last_name}'.strip()
                                  or request.user.email,
            'user_email'       : request.user.email,
            'user_phone'       : getattr(request.user, 'phone_number', ''),
        }
        return render(request, 'orders/razorpay_payment.html', context)

    messages.error(request, 'Invalid payment method selected.')
    return redirect('checkout')


# ─────────────────────────────────────────────────────────────────────────────
# RAZORPAY CALLBACK  (POST from frontend after payment)
# Signature is verified server-side — never trust the frontend alone.
# ─────────────────────────────────────────────────────────────────────────────
@csrf_exempt                     # Razorpay posts without Django CSRF cookie
@login_required(login_url='login')
def razorpay_callback(request):
    if request.method != 'POST':
        return redirect('checkout')

    rz_payment_id = request.POST.get('razorpay_payment_id', '')
    rz_order_id   = request.POST.get('razorpay_order_id', '')
    rz_signature  = request.POST.get('razorpay_signature', '')

    # ── Verify signature ──────────────────────────────────
    try:
        rz_client = _razorpay_client()
        rz_client.utility.verify_payment_signature({
            'razorpay_order_id'  : rz_order_id,
            'razorpay_payment_id': rz_payment_id,
            'razorpay_signature' : rz_signature,
        })
        signature_ok = True
    except razorpay.errors.SignatureVerificationError:
        signature_ok = False

    if not signature_ok:
        # Store failed order id so failure page can offer retry
        request.session['failed_razorpay_order_id'] = rz_order_id
        return redirect('payment_failed')

    # ── Build order ───────────────────────────────────────
    address_id = request.session.get('pending_address_id')
    if not address_id:
        messages.error(request, 'Session expired. Please try again.')
        return redirect('checkout')

    address = get_object_or_404(UserAddress, id=address_id, user=request.user)

    cart       = _get_or_create_cart(request)
    cart_items = CartItem.objects.filter(
        cart=cart, is_active=True
    ).select_related('variant', 'variant__product')

    totals = _compute_totals(cart_items, request.session)

    payment = Payment.objects.create(
        user           = request.user,
        payment_method = 'RAZORPAY',
        amount_paid    = str(totals['final_total']),
        status         = 'Completed',
        transaction_id = rz_payment_id,
    )
    order = _build_order_from_session(request, address, payment, totals)
    return redirect('payment_success', order_number=order.order_number)


# ─────────────────────────────────────────────────────────────────────────────
# COD SUCCESS PAGE  (existing order_complete.html style)
# ─────────────────────────────────────────────────────────────────────────────
@login_required(login_url='login')
def order_complete(request, order_number):
    order       = get_object_or_404(Order, order_number=order_number, user=request.user)
    order_items = order.items.select_related('variant', 'variant__product').all()
    return render(request, 'orders/order_complete.html', {
        'order': order, 'order_items': order_items,
    })


# ─────────────────────────────────────────────────────────────────────────────
# RAZORPAY SUCCESS PAGE  (richer — for online payments)
# ─────────────────────────────────────────────────────────────────────────────
@login_required(login_url='login')
def payment_success(request, order_number):
    order       = get_object_or_404(Order, order_number=order_number, user=request.user)
    order_items = order.items.select_related('variant', 'variant__product').all()
    return render(request, 'orders/payment_success.html', {
        'order': order, 'order_items': order_items,
    })


# ─────────────────────────────────────────────────────────────────────────────
# PAYMENT FAILED PAGE
# ─────────────────────────────────────────────────────────────────────────────
@login_required(login_url='login')
def payment_failed(request):
    rz_order_id = request.session.pop('failed_razorpay_order_id', '')
    return render(request, 'orders/payment_failed.html', {
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'razorpay_order_id': rz_order_id,
    })



# ─────────────────────────────────────────────────────────────────────────────
# MY ORDERS LIST
# ─────────────────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def my_orders(request):
    orders = Order.objects.filter(user=request.user, is_ordered=True)

    q = request.GET.get('q', '').strip()
    if q:
        orders = orders.filter(order_number__icontains=q)

    return render(request, 'dashboard/orders.html', {
        'orders' : orders,
        'q'      : q,
    })




# ─────────────────────────────────────────────────────────────────────────────
# ORDER DETAIL
# ─────────────────────────────────────────────────────────────────────────────
@login_required(login_url='login')
def order_detail(request, order_number):
    order       = get_object_or_404(Order, order_number=order_number, user=request.user)
    order_items = order.items.select_related('variant', 'variant__product').all()
    return render(request, 'orders/order_detail.html', {
        'order': order, 'order_items': order_items,
    })



# ─────────────────────────────────────────────────────────────────────────────
# MY ORDERS LIST
# ─────────────────────────────────────────────────────────────────────────────
@login_required(login_url='login')
def my_orders(request):
    orders = Order.objects.filter(
        user=request.user, is_ordered=True
    ).select_related('payment').prefetch_related('items')
    return render(request, 'orders/my_orders.html', {'orders': orders})


# ─────────────────────────────────────────────────────────────────────────────
# CANCEL ORDER  →  stock restored + immediate wallet refund
# ─────────────────────────────────────────────────────────────────────────────
@login_required(login_url='login')
def cancel_order(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)

    if order.status not in ['New', 'Accepted']:
        messages.error(request, 'This order cannot be cancelled.')
        return redirect('order_detail', order_number=order_number)

    if request.method != 'POST':
        return redirect('order_detail', order_number=order_number)

    reason = request.POST.get('cancel_reason', '')

    # 1. Restore stock
    for item in order.items.select_related('variant').all():
        if item.variant:
            item.variant.stock += item.quantity
            item.variant.save(update_fields=['stock'])

    # 2. Calculate refund
    refund_amount = Decimal('0')
    parts         = []

    wallet_paid = order.wallet_used or Decimal('0')
    if wallet_paid > 0:
        refund_amount += wallet_paid
        parts.append(f'wallet ₹{wallet_paid}')

    payment = order.payment
    if payment and payment.payment_method == 'RAZORPAY' and payment.status == 'Completed':
        razorpay_paid = Decimal(str(payment.amount_paid))
        if razorpay_paid > 0:
            refund_amount += razorpay_paid
            parts.append(f'Razorpay ₹{razorpay_paid}')
            payment.status = 'Refunded'
            payment.save(update_fields=['status'])

    # 3. Credit wallet
    if refund_amount > 0:
        wallet = _get_wallet(request.user)
        wallet.credit(
            amount      = refund_amount,
            description = f'Refund — cancelled Order #{order.order_number} ({", ".join(parts)})',
            order       = order,
        )
        messages.success(
            request,
            f'Order cancelled. ₹{refund_amount} refunded to your wallet instantly.'
        )
    else:
        messages.success(request, 'Order cancelled. Stock has been restored.')

    # 4. Update order
    order.status        = 'Cancelled'
    order.cancel_reason = reason
    order.save(update_fields=['status', 'cancel_reason'])

    return redirect('order_detail', order_number=order_number)


# ─────────────────────────────────────────────────────────────────────────────
# RETURN ORDER  →  "Return Requested" — admin approves → wallet credit
# ─────────────────────────────────────────────────────────────────────────────
@login_required(login_url='login')
def return_order(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)

    if order.status != 'Delivered':
        messages.error(request, 'Only delivered orders can be returned.')
        return redirect('order_detail', order_number=order_number)

    if request.method != 'POST':
        return redirect('order_detail', order_number=order_number)

    reason = request.POST.get('return_reason', '').strip()
    if not reason:
        messages.error(request, 'Please select a return reason.')
        return redirect('order_detail', order_number=order_number)

    order.status        = 'Return Requested'
    order.return_reason = reason
    order.save(update_fields=['status', 'return_reason'])

    messages.success(
        request,
        'Return request submitted. Once approved, your refund will be '
        'credited to your wallet and stock will be restored automatically.'
    )
    return redirect('order_detail', order_number=order_number)




# ─────────────────────────────────────────────────────────────────────────────
# DOWNLOAD INVOICE PDF
# ─────────────────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def download_invoice(request, order_number):
    order       = get_object_or_404(Order, order_number=order_number, user=request.user)
    order_items = OrderProduct.objects.filter(order=order)

    if order.status in ['Return Requested', 'Returned', 'Cancelled']:
        messages.error(request, 'Invoice not available for cancelled or returned orders.')
        return redirect('order_detail', order_number=order_number)

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_RIGHT, TA_CENTER
        import io

        buffer = io.BytesIO()
        doc    = SimpleDocTemplate(buffer, pagesize=A4,
                                   rightMargin=2*cm, leftMargin=2*cm,
                                   topMargin=2*cm,   bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        story  = []

        # Title
        title_style = ParagraphStyle('title', parent=styles['Heading1'],
                                     fontSize=20,
                                     textColor=colors.HexColor('#3167eb'),
                                     spaceAfter=4)
        story.append(Paragraph('Orbit Watch Collection', title_style))
        story.append(Paragraph('Invoice', styles['Heading2']))
        story.append(Spacer(1, 0.3*cm))

        # Order info
        info_data = [
            ['Order Number:', f'#{order.order_number}'],
            ['Date:',         order.created_at.strftime('%d %B %Y')],
            ['Payment:',      order.payment.payment_method if order.payment else 'COD'],
            ['Status:',       order.status],
        ]
        info_table = Table(info_data, colWidths=[4*cm, 10*cm])
        info_table.setStyle(TableStyle([
            ('FONTNAME',      (0,0), (0,-1), 'Helvetica-Bold'),
            ('FONTSIZE',      (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.4*cm))

        # Delivery address
        story.append(Paragraph('<b>Deliver To:</b>', styles['Normal']))
        story.append(Paragraph(
            f"{order.full_name} | +91 {order.phone}<br/>"
            f"{order.address_line}, {order.city}, {order.state} — {order.pincode}",
            styles['Normal']
        ))
        story.append(Spacer(1, 0.5*cm))

        # Items table
        headers   = [['#', 'Product', 'Color', 'Price', 'Qty', 'Total']]
        item_rows = []
        for idx, item in enumerate(order_items, 1):
            item_rows.append([
                str(idx),
                item.product_name,
                item.color_name,
                f'Rs.{item.product_price}',
                str(item.quantity),
                f'Rs.{item.sub_total()}',
            ])
        item_table = Table(headers + item_rows,
                           colWidths=[1*cm, 6*cm, 3*cm, 2.5*cm, 1.5*cm, 2.5*cm])
        item_table.setStyle(TableStyle([
            ('BACKGROUND',    (0,0),  (-1,0),  colors.HexColor('#3167eb')),
            ('TEXTCOLOR',     (0,0),  (-1,0),  colors.white),
            ('FONTNAME',      (0,0),  (-1,0),  'Helvetica-Bold'),
            ('FONTSIZE',      (0,0),  (-1,-1), 9),
            ('ROWBACKGROUNDS',(0,1),  (-1,-1), [colors.white, colors.HexColor('#f4f6ff')]),
            ('GRID',          (0,0),  (-1,-1), 0.5, colors.HexColor('#dee2e6')),
            ('ALIGN',         (3,0),  (-1,-1), 'RIGHT'),
            ('BOTTOMPADDING', (0,0),  (-1,-1), 6),
            ('TOPPADDING',    (0,0),  (-1,-1), 6),
        ]))
        story.append(item_table)
        story.append(Spacer(1, 0.4*cm))

        # Totals
        subtotal    = float(order.order_total) - float(order.tax)
        totals_data = [
            ['', 'Subtotal:',    f'Rs.{subtotal:.2f}'],
            ['', 'Tax (18%):',   f'Rs.{order.tax}'],
            ['', 'Shipping:',    'Free'],
            ['', 'Grand Total:', f'Rs.{order.order_total}'],
        ]
        totals_table = Table(totals_data, colWidths=[9*cm, 4*cm, 3.5*cm])
        totals_table.setStyle(TableStyle([
            ('FONTNAME',      (1,3),  (2,3),  'Helvetica-Bold'),
            ('FONTSIZE',      (0,0),  (-1,-1), 10),
            ('ALIGN',         (1,0),  (-1,-1), 'RIGHT'),
            ('LINEABOVE',     (1,3),  (-1,3),  1, colors.HexColor('#3167eb')),
            ('BOTTOMPADDING', (0,0),  (-1,-1), 5),
        ]))
        story.append(totals_table)
        story.append(Spacer(1, 1*cm))

        # Footer
        center_style = ParagraphStyle('center', parent=styles['Normal'],
                                      alignment=TA_CENTER,
                                      textColor=colors.grey, fontSize=9)
        story.append(Paragraph('Thank you for shopping with Orbit Watch Collection!', center_style))
        story.append(Paragraph('support@orbit.com  |  +859-321-1234  |  Thrissur, Guruvayoor', center_style))

        doc.build(story)
        buffer.seek(0)

        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = (
            f'attachment; filename="Invoice_{order_number}.pdf"'
        )
        return response

    except ImportError:
        # Fallback plain text if reportlab not installed
        lines = [
            'ORBIT WATCH COLLECTION',
            f'Invoice — Order #{order.order_number}',
            f'Date: {order.created_at.strftime("%d %B %Y")}',
            '',
            f'Deliver To: {order.full_name} | +91 {order.phone}',
            f'{order.address_line}, {order.city}, {order.state} - {order.pincode}',
            '',
            f"{'Product':<35} {'Qty':>4} {'Price':>10} {'Total':>10}",
            '-' * 65,
        ]
        for item in order_items:
            lines.append(
                f"{item.product_name:<35} {item.quantity:>4} "
                f"Rs.{item.product_price:>8} Rs.{item.sub_total():>8}"
            )
        subtotal = float(order.order_total) - float(order.tax)
        lines += [
            '-' * 65,
            f"{'Subtotal:':<50} Rs.{subtotal:.2f}",
            f"{'Tax (18%):':<50} Rs.{order.tax}",
            f"{'Shipping:':<50} Free",
            f"{'Grand Total:':<50} Rs.{order.order_total}",
            '',
            'Thank you for shopping with Orbit Watch Collection!',
        ]
        response = HttpResponse('\n'.join(lines), content_type='text/plain')
        response['Content-Disposition'] = (
            f'attachment; filename="Invoice_{order_number}.txt"'
        )
        return response