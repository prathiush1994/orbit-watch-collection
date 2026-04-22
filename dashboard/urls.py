from django.urls import path
from . import views
from wallet.views import wallet_dashboard

urlpatterns = [
    # Profile
    path("", views.profile, name="dashboard_profile"),
    path("edit-profile/", views.edit_profile, name="dashboard_edit_profile"),
    # Orders
    path("orders/", views.orders, name="dashboard_orders"),
    # Transactions
    path("transactions/", views.transactions, name="dashboard_transactions"),
    # Returns
    path("returns/", views.returns, name="dashboard_returns"),
    # Address
    path("address/", views.address, name="dashboard_address"),
    # Wallet
    path("wallet/", wallet_dashboard, name="dashboard_wallet"),
    # Coupons
    path("coupons/", views.dashboard_coupons, name="dashboard_coupons"),
    # Change Password
    path("change-password/", views.change_password, name="dashboard_change_password"),
    path(
        "change-password/verify/",
        views.verify_change_password,
        name="dashboard_verify_change_password",
    ),
    path(
        "change-password/resend/",
        views.resend_change_password_otp,
        name="dashboard_resend_change_password_otp",
    ),
    # Delete Account
    path("delete-account/", views.delete_account, name="dashboard_delete_account"),
    path(
        "delete-account/verify/",
        views.verify_delete_account,
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
    path("coupons/", views.dashboard_coupons, name="dashboard_coupons"),
]
