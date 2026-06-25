
from .account_views import (
    change_email,
    resend_change_email_otp, resend_change_password_otp,
    delete_account,
    resend_delete_account_otp,
    verify_delete_account,
    verify_change_password,
    change_password,
)
from .address_views import address
from .coupon_views import dashboard_coupons
from .wallet_views import dashboard_wallet
from .profile_views import profile, edit_profile
from .order_views import orders, transactions, returns
