from django.urls import path
from . import views

urlpatterns = [
    # Checkout
    path("checkout/", views.checkout, name="checkout"),
    path("place-order/", views.place_order, name="place_order"),

    # Invoice
    path(
        "invoice/<str:order_number>/",
        views.download_invoice,
        name="download_invoice"
    ),
    # Result pages
    path("complete/<str:order_number>/", views.order_complete, name="order_complete"),
    path("success/<str:order_number>/", views.payment_success, name="payment_success"),
    path("failed/", views.payment_failed, name="payment_failed"),
    # Razorpay — OLD callback (kept)
    path("razorpay/callback/", views.razorpay_callback, name="razorpay_callback"),
    # Razorpay — NEW webhook URLs ← ADD THESE
    path("razorpay/webhook/", views.razorpay_webhook, name="razorpay_webhook"),
    path("payment-processing/", views.payment_processing, name="payment_processing"),
    path("check-order-status/", views.check_order_status, name="check_order_status"),
    # Whole-order cancel / return
    path("cancel/<str:order_number>/", views.cancel_order, name="cancel_order"),
    path("return/<str:order_number>/", views.return_order, name="return_order"),
    # Item-level cancel / return
    path(
        "cancel/<str:order_number>/item/<int:item_id>/",
        views.cancel_item,
        name="cancel_item",
    ),
    path(
        "return/<str:order_number>/item/<int:item_id>/",
        views.return_item,
        name="return_item",
    ),
]
