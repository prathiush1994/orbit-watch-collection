from django.urls import path
from . import views


urlpatterns = [
    path("dashboard/", views.profile, name="dashboard_profile"),
    path("edit-profile/", views.edit_profile, name="dashboard_edit_profile"),
    path("orders/", views.orders, name="dashboard_orders"),
    path("transactions/", views.transactions, name="dashboard_transactions"),
    path("returns/", views.returns, name="dashboard_returns"),
    path("address/", views.address, name="dashboard_address"),

    path("coupons/", views.dashboard_coupons, name="dashboard_coupons"),
    path(
        "change-password/",
        views.send_change_password_otp,
        name="dashboard_change_password",
    ),
    path(
        "change-password/verify/",
        views.verify_otp_and_update_password,
        name="dashboard_verify_change_password",
    ),
    path(
        "change-password/resend/",
        views.resend_password_change_otp,
        name="dashboard_resend_change_password_otp",
    ),

    path(
        "delete-account/",
        views.send_delete_account_otp,
        name="dashboard_delete_account",
    ),
    path(
        "delete-account/verify/",
        views.verify_otp_and_delete_account,
        name="dashboard_verify_delete_account",
    ),
    path(
        "delete-account/resend/",
        views.resend_delete_account_otp,
        name="dashboard_resend_delete_account_otp",
    ),
    path("change-email/", views.change_email, name="dashboard_change_email"),
    path(
        "change-email/resend/",
        views.resend_change_email_otp,
        name="dashboard_resend_change_email_otp",
    ),
    path("wallet/", views.dashboard_wallet, name="dashboard_wallet"),
]
