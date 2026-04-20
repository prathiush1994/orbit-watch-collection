from django.http import HttpResponse
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from reportlab.platypus import Paragraph
from ..models import Order, OrderProduct

@login_required(login_url='login')
def download_invoice(request, order_number):
    order       = get_object_or_404(Order, order_number=order_number, user=request.user)
    order_items = OrderProduct.objects.filter(order=order)

    # Case 1: Fully cancelled order
    if order.status == 'Cancelled':
        messages.error(request, 'Invoice not available for cancelled orders.')
        return redirect('order_detail', order_number=order_number)

    # Case 2: Fully returned order
    if order.status == 'Returned':
        messages.error(request, 'Invoice not available for returned orders.')
        return redirect('order_detail', order_number=order_number)

    # Case 3: Partial return / cancel (item-level)
    if order.items.filter(item_status__in=['Return Requested', 'Returned', 'Cancelled']).exists():
        messages.error(request, 'Invoice not available because some items are returned or cancelled.')
        return redirect('order_detail', order_number=order_number)

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        import io

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            rightMargin=2*cm, leftMargin=2*cm,
            topMargin=2*cm, bottomMargin=2*cm
        )

        styles = getSampleStyleSheet()
        story = []

        # ───────────────── TITLE ─────────────────
        title_style = ParagraphStyle(
            'title', parent=styles['Heading1'],
            fontSize=20, textColor=colors.HexColor('#3167eb'),
            spaceAfter=4
        )
        story.append(Paragraph('Orbit Watch Collection', title_style))
        story.append(Paragraph('Invoice', styles['Heading2']))
        story.append(Spacer(1, 0.3*cm))

        # ───────────────── ORDER INFO ─────────────────
        info_data = [
            ['Order Number:', f'#{order.order_number}'],
            ['Date:', order.created_at.strftime('%d %B %Y')],
            ['Payment:', order.payment.payment_method if order.payment else 'COD'],
            ['Status:', order.status],
        ]

        info_table = Table(info_data, colWidths=[4*cm, 10*cm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.4*cm))

        # ───────────────── ADDRESS ─────────────────
        story.append(Paragraph('<b>Deliver To:</b>', styles['Normal']))
        story.append(Paragraph(
            f"{order.full_name} | +91 {order.phone}<br/>"
            f"{order.address_line}, {order.city}, {order.state} — {order.pincode}",
            styles['Normal']
        ))
        story.append(Spacer(1, 0.5*cm))

        # ───────────────── ITEMS TABLE (WRAP FIXED) ─────────────────
        headers = [['#', 'Product', 'Color', 'Price', 'Qty', 'Total']]
        item_rows = []

        for idx, item in enumerate(order_items, 1):
            item_rows.append([
                Paragraph(str(idx), styles['Normal']),
                Paragraph(item.product_name, styles['Normal']),
                Paragraph(item.color_name or '-', styles['Normal']),
                Paragraph(f'Rs.{item.product_price}', styles['Normal']),
                Paragraph(str(item.quantity), styles['Normal']),
                Paragraph(f'Rs.{item.sub_total()}', styles['Normal']),
            ])

        item_table = Table(
            headers + item_rows,
            colWidths=[1*cm, 6*cm, 3*cm, 2.5*cm, 1.5*cm, 2.5*cm]
        )

        item_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#3167eb')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('ROWBACKGROUNDS', (0,1), (-1,-1),
                [colors.white, colors.HexColor('#f4f6ff')]),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#dee2e6')),
            ('ALIGN', (3,0), (-1,-1), 'RIGHT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('WORDWRAP', (0,0), (-1,-1), 'CJK'),
        ]))

        story.append(item_table)
        story.append(Spacer(1, 0.4*cm))

        # ───────────────── CORRECT TOTAL CALCULATION ─────────────────
        grand_total = float(order.order_total) + float(order.discount or 0) + float(order.wallet_used or 0)
        subtotal = grand_total - float(order.tax)

        totals_data = [
            ['', 'Subtotal:', f'Rs.{subtotal:.2f}'],
            ['', 'GST (18%):', f'Rs.{order.tax}'],
        ]

        # Coupon
        if order.discount and order.discount > 0:
            totals_data.append([
                '', f'Coupon ({order.coupon_code}):', f'- Rs.{order.discount}'
            ])

        # Wallet
        if order.wallet_used and order.wallet_used > 0:
            totals_data.append([
                '', 'Wallet Used:', f'- Rs.{order.wallet_used}'
            ])

        # Shipping
        totals_data.append(['', 'Delivery:', 'Free'])

        # Final
        totals_data.append([
            '', 'Total Payment:', f'Rs.{order.order_total}'
        ])

        totals_table = Table(totals_data, colWidths=[9*cm, 4*cm, 3.5*cm])

        last_row = len(totals_data) - 1

        totals_table.setStyle(TableStyle([
            ('FONTNAME', (1,last_row), (2,last_row), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
            ('LINEABOVE', (1,last_row), (-1,last_row), 1, colors.HexColor('#3167eb')),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ]))

        story.append(totals_table)
        story.append(Spacer(1, 1*cm))

        # ───────────────── FOOTER ─────────────────
        center_style = ParagraphStyle(
            'center', parent=styles['Normal'],
            alignment=TA_CENTER,
            textColor=colors.grey,
            fontSize=9
        )

        story.append(Paragraph(
            'Thank you for shopping with Orbit Watch Collection!',
            center_style
        ))
        story.append(Paragraph(
            'support@orbit.com | +91-859-321-1234 | Kerala, India',
            center_style
        ))

        doc.build(story)
        buffer.seek(0)

        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Invoice_{order_number}.pdf"'
        return response

    except ImportError:
        return HttpResponse("ReportLab not installed", status=500)

