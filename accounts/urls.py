from django.urls import path
from . import views

urlpatterns = [
    path("orbit-watch/login_page/", views.login, name="login"),
    path(
        "orbit-watch/verify-login-otp/",
        views.verify_login_otp,
        name="verify_login_otp"
        ),
    path(
        "orbit-watch/resend-login-otp/",
        views.resend_login_otp,
        name="resend_login_otp"
        ),
    path("logout/", views.logout, name="logout"),
    path("orbit-watch/register/", views.register, name="register"),
    path("orbit-watch/verify-email/", views.verify_email, name="verify_email"),
    path("orbit-watch/resend-otp/", views.resend_otp, name="resend_otp"),
    path(
        "orbit-watch/forgot-password/",
        views.forgot_password,
        name="forgot_password"
        ),
    path(
        "orbit-watch/verify-forgot-otp/",
        views.verify_forgot_otp,
        name="verify_forgot_otp",
    ),
    path(
        "orbit-watch/resend-forgot-otp/",
        views.resend_forgot_otp,
        name="resend_forgot_otp",
    ),
    path(
        "orbit-watch/reset-password/",
        views.reset_password,
        name="reset_password"
        ),
    path("address/", views.manage_address, name="manage_address"),
    path("address/add/", views.add_address, name="add_address"),
    path(
        "address/edit/<int:address_id>/",
        views.edit_address,
        name="edit_address"
        ),
    path(
        "address/delete/<int:address_id>/",
        views.delete_address,
        name="delete_address"
        ),
    path(
        "address/set-default/<int:address_id>/",
        views.set_default_address,
        name="set_default_address",
    ),
]
