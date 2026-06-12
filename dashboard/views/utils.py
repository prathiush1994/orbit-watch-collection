from django.utils import timezone
from datetime import timedelta


OTP_EXPIRY_MINUTES = 2


def _otp_remaining(otp_created_at):
    if not otp_created_at:
        return 0
    expiry = otp_created_at + timedelta(minutes=OTP_EXPIRY_MINUTES)
    remaining = (expiry - timezone.now()).total_seconds()
    return max(int(remaining), 0)

