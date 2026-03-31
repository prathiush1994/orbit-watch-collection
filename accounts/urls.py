from django.urls import path
from . import views

urlpatterns = [
    # Registration flow
    path('register/',                       views.register,          name='register'),
    path('verify-email/<int:user_id>/',     views.verify_email,      name='verify_email'),
    path('resend-otp/<int:user_id>/',       views.resend_otp,        name='resend_otp'),

    # Login / Logout
    path('login/',                          views.login,             name='login'),
    path('logout/',                         views.logout,            name='logout'),

    # Forgot password flow (all OTP based)
    path('forgot-password/',                          views.forgot_password,      name='forgot_password'),
    path('verify-forgot-otp/<int:user_id>/',          views.verify_forgot_otp,    name='verify_forgot_otp'),
    path('resend-forgot-otp/<int:user_id>/',          views.resend_forgot_otp,    name='resend_forgot_otp'),
    path('reset-password/<int:user_id>/',             views.reset_password,       name='reset_password'),

    path('verify-login-otp/',    views.verify_login_otp, name='verify_login_otp'),
    path('resend-login-otp/',    views.resend_login_otp, name='resend_login_otp'),


    path('address/',                             views.manage_address,      name='manage_address'),
    path('address/add/',                         views.add_address,         name='add_address'),
    path('address/edit/<int:address_id>/',       views.edit_address,        name='edit_address'),
    path('address/delete/<int:address_id>/',     views.delete_address,      name='delete_address'),
    path('address/set-default/<int:address_id>/',views.set_default_address, name='set_default_address'),
]