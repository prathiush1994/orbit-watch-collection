from django.http import HttpResponse
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..models import Order, OrderProduct
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
)


@login_required(login_url="login")
def download_invoice(request, order_number):
    order = get_object_or_404(
        Order,
        order_number=order_number,
        user=request.user,
    )
    order_items = []
        
    for item in OrderProduct.objects.filter(order=order):
        if item.active_qty() > 0:
            order_items.append(item)

    if len(order_items) == 0:
        messages.error(
            request,
            "Invoice is not available because all items have been cancelled or returned."
        )
        return redirect("order_detail", order_number=order_number)
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        styles = getSampleStyleSheet()
        story = []

        title_style = ParagraphStyle(
            "title",
            parent=styles["Heading1"],
            fontSize=20,
            textColor=colors.HexColor("#3167eb"),
            spaceAfter=4,
        )
        story.append(Paragraph("Orbit Watch Collection", title_style))
        story.append(Paragraph("Invoice", styles["Heading2"]))
        story.append(Spacer(1, 0.3 * cm))

        payment_method = []

        if order.wallet_used > 0:
            payment_method.append("Wallet")

        if order.payment and order.payment.payment_method.upper() != "WALLET":
            payment_method.append(order.payment.payment_method)

        status = order.status
        if status in ["Returned", "Return Requested"]:
            status = "Delivered"

        info_data = [
            ["Order Number:", f"#{order.order_number}"],
            ["Date:", order.created_at.strftime("%d %B %Y")],
            [
                "Payment:",
                " + ".join(payment_method) if payment_method else "COD"
            ],
            ["Status:", status],
        ]

        info_table = Table(info_data, colWidths=[4 * cm, 10 * cm])
        info_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(info_table)
        story.append(Spacer(1, 0.4 * cm))

        story.append(Paragraph("<b>Deliver To:</b>", styles["Normal"]))
        story.append(
            Paragraph(
                f"{order.full_name} | +91 {order.phone}<br/>"
                f"{order.address_line}, {order.city}, {order.state} — "
                f"{order.pincode}",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 0.5 * cm))

        headers = [["#", "Product", "Color", "Price", "Qty", "Total"]]
        item_rows = []

        for idx, item in enumerate(order_items, 1):
            item_rows.append(
                [
                    Paragraph(str(idx), styles["Normal"]),
                    Paragraph(item.product_name, styles["Normal"]),
                    Paragraph(item.color_name or "-", styles["Normal"]),
                    Paragraph(f"Rs.{item.product_price}", styles["Normal"]),
                    Paragraph(str(item.active_qty()), styles["Normal"]),
                    Paragraph(f"Rs.{item.sub_total()}", styles["Normal"]),
                ]
            )
 
        item_table = Table(
            headers + item_rows,
            colWidths=[1 * cm, 6 * cm, 3 * cm, 2.5 * cm, 1.5 * cm, 2.5 * cm],
        )

        item_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor("#3167eb"),
                    ),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#f4f6ff")],
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        colors.HexColor("#dee2e6"),
                    ),
                    ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("WORDWRAP", (0, 0), (-1, -1), "CJK"),
                ]
            )
        )

        story.append(item_table)
        story.append(Spacer(1, 0.4 * cm))

        subtotal = float(
            sum(item.product_price * item.active_qty() for item in order_items)
        )
        tax = float(order.tax or 0)
        wallet_used = float(order.wallet_used or 0)
        discount = float(order.discount or 0)
        actual_total = subtotal + tax - discount
        totals_data = [
            ["", "Subtotal:", f"Rs.{subtotal:.2f}"],
            ["", "GST (18%):", f"Rs.{tax:.2f}"],
        ]
        if order.discount and order.discount > 0:
            totals_data.append(
                [
                    "",
                    "Discount:",
                    f"- Rs.{float(order.discount):.2f}",
                ]
            )
        totals_data.append(["", "Delivery:", "Free"])
        totals_data.append(
            [
                "",
                "Grand Total:",
                f"Rs.{actual_total:.2f}",
            ]
        )

        totals_table = Table(totals_data, colWidths=[9 * cm, 4 * cm, 3.5 * cm])
        grand_total_row = 4 if discount > 0 else 3

        totals_table.setStyle(
            TableStyle(
                [
                    (
                        "FONTNAME",
                        (1, grand_total_row),
                        (2, grand_total_row),
                        "Helvetica-Bold",
                    ),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                    (
                        "LINEABOVE",
                        (1, grand_total_row),
                        (-1, grand_total_row),
                        1,
                        colors.HexColor("#3167eb"),
                    ),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )

        story.append(totals_table)
        story.append(Spacer(1, 1 * cm))

        center_style = ParagraphStyle(
            "center",
            parent=styles["Normal"],
            alignment=TA_CENTER,
            textColor=colors.grey,
            fontSize=9,
        )

        story.append(
            Paragraph(
                "Thank you for shopping with Orbit Watch Collection!",
                center_style,
            )
        )
        story.append(
            Paragraph(
                "support@orbit.com | +91-859-321-1234 | Kerala, India",
                center_style,
            )
        )

        doc.build(story)
        buffer.seek(0)

        response = HttpResponse(buffer, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="Invoice_{order_number}.pdf"'
        )
        return response

    except ImportError:
        return HttpResponse("ReportLab not installed", status=500)

