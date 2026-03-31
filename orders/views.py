from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
import datetime

from carts.models import Cart, CartItem
from accounts.models import UserAddress
from .models import Payment, Order, OrderProduct


# ─────────────────────────────────────────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────────────────────────────────────────

def _get_cart_id(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


# ─────────────────────────────────────────────────────────────────────────────
# CHECKOUT
# ─────────────────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def checkout(request):
    try:
        cart       = Cart.objects.get(cart_id=_get_cart_id(request))
        cart_items = CartItem.objects.filter(cart=cart, is_active=True)
    except Cart.DoesNotExist:
        cart_items = CartItem.objects.none()

    if not cart_items.exists():
        messages.warning(request, 'Your cart is empty.')
        return redirect('cart')

    total       = sum(item.sub_total() for item in cart_items)
    tax         = round(total * 18 / 100, 2)
    grand_total = round(total + tax, 2)

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


# ─────────────────────────────────────────────────────────────────────────────
# PLACE ORDER
# ─────────────────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def place_order(request):
    if request.method != 'POST':
        return redirect('checkout')

    address_id = request.POST.get('address_id')
    if not address_id:
        messages.error(request, 'Please select a delivery address.')
        return redirect('checkout')

    try:
        address = UserAddress.objects.get(id=address_id, user=request.user)
    except UserAddress.DoesNotExist:
        messages.error(request, 'Invalid address.')
        return redirect('checkout')

    try:
        cart       = Cart.objects.get(cart_id=_get_cart_id(request))
        cart_items = CartItem.objects.filter(cart=cart, is_active=True)
    except Cart.DoesNotExist:
        messages.warning(request, 'Your cart is empty.')
        return redirect('cart')

    if not cart_items.exists():
        messages.warning(request, 'Your cart is empty.')
        return redirect('cart')

    total       = sum(item.sub_total() for item in cart_items)
    tax         = round(total * 18 / 100, 2)
    grand_total = round(total + tax, 2)

    # Create Payment
    payment = Payment.objects.create(
        user           = request.user,
        payment_method = 'COD',
        amount_paid    = str(grand_total),
        status         = 'Pending',
        transaction_id = '',
    )

    # Unique order number: ORB + YYYYMMDD + user_id + payment_id
    today        = datetime.date.today().strftime('%Y%m%d')
    order_number = f"ORB{today}{request.user.id:04d}{payment.id:03d}"

    # Create Order
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

    # Create OrderProducts + reduce stock
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
        item.variant.stock -= item.quantity
        item.variant.save()

    cart_items.delete()

    return redirect('order_complete', order_number=order_number)


# ─────────────────────────────────────────────────────────────────────────────
# ORDER COMPLETE (success page)
# ─────────────────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def order_complete(request, order_number):
    try:
        order = Order.objects.get(order_number=order_number, user=request.user)
    except Order.DoesNotExist:
        return redirect('home')

    order_items = OrderProduct.objects.filter(order=order)
    return render(request, 'orders/order_complete.html', {
        'order'       : order,
        'order_items' : order_items,
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
    order_items = OrderProduct.objects.filter(order=order)
    return render(request, 'orders/order_detail.html', {
        'order'       : order,
        'order_items' : order_items,
    })


# ─────────────────────────────────────────────────────────────────────────────
# CANCEL ORDER
# ─────────────────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def cancel_order(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)

    if request.method != 'POST':
        return redirect('order_detail', order_number=order_number)

    if order.status not in ['New', 'Accepted']:
        messages.error(request, 'This order cannot be cancelled.')
        return redirect('order_detail', order_number=order_number)

    # Restore stock
    for item in order.items.all():
        if item.variant:
            item.variant.stock += item.quantity
            item.variant.save()

    order.status = 'Cancelled'
    order.save()

    messages.success(request, f'Order #{order_number} cancelled. Stock has been restored.')
    return redirect('my_orders')


# ─────────────────────────────────────────────────────────────────────────────
# RETURN ORDER
# ─────────────────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def return_order(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)

    if request.method != 'POST':
        return redirect('order_detail', order_number=order_number)

    if order.status != 'Delivered':
        messages.error(request, 'Only delivered orders can be returned.')
        return redirect('order_detail', order_number=order_number)

    reason = request.POST.get('return_reason', '').strip()
    if not reason:
        messages.error(request, 'Please provide a reason for return.')
        return redirect('order_detail', order_number=order_number)

    order.status = 'Return Requested'
    order.save()

    messages.success(request, 'Return request submitted successfully.')
    return redirect('order_detail', order_number=order_number)


# ─────────────────────────────────────────────────────────────────────────────
# DOWNLOAD INVOICE PDF
# ─────────────────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def download_invoice(request, order_number):
    order       = get_object_or_404(Order, order_number=order_number, user=request.user)
    order_items = OrderProduct.objects.filter(order=order)

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