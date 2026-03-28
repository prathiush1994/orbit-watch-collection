from django.utils import timezone

OTP_EXPIRY_MINUTES = 2

def _otp_remaining(otp_created_at):
    if not otp_created_at:
        return 0
    elapsed = (timezone.now() - otp_created_at).total_seconds()
    return max(0, int(OTP_EXPIRY_MINUTES * 60 - elapsed))

def _is_otp_expired(otp_created_at):
    return _otp_remaining(otp_created_at) == 0