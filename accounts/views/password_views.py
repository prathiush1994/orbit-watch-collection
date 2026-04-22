from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone

from ..models import Account
from ..email_utils import generate_otp, send_otp_email
from .otp_data import _otp_remaining


def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()

        try:
            user = Account.objects.get(email=email)
        except Account.DoesNotExist:
            # Show same message to avoid user enumeration
            messages.success(request, "If that email exists, an OTP has been sent.")
            return redirect("forgot_password")

        user.otp = generate_otp()
        user.otp_created_at = timezone.now()
        user.otp_purpose = "forgot"
        user.save()

        sent = send_otp_email(email, user.otp, purpose="forgot")
        if sent:
            messages.success(request, f"OTP sent to {email}.")
        else:
            messages.error(request, "Failed to send OTP. Please try again.")
            return redirect("forgot_password")

        return redirect("verify_forgot_otp", user_id=user.id)

    return render(request, "accounts/forgot_password.html")


def verify_forgot_otp(request, user_id):
    user = get_object_or_404(Account, id=user_id)

    # Safety: only allow if otp_purpose is 'forgot'
    if user.otp_purpose != "forgot":
        messages.error(request, "Invalid request.")
        return redirect("forgot_password")

    remaining = _otp_remaining(user.otp_created_at)
    expired = remaining == 0

    if request.method == "POST":
        if expired:
            messages.error(request, "OTP has expired. Please request a new one.")
            return render(
                request,
                "accounts/verify_forgot_otp.html",
                {"user": user, "remaining_time": 0, "expired": True},
            )

        entered_otp = request.POST.get("otp", "").strip()

        if entered_otp == user.otp:
            # Mark OTP used but keep purpose so reset_password view can verify
            user.otp = None
            user.otp_created_at = None
            user.otp_purpose = "forgot_verified"
            user.save()
            return redirect("reset_password", user_id=user.id)
        else:
            messages.error(request, "Invalid OTP. Please try again.")

    return render(
        request,
        "accounts/verify_forgot_otp.html",
        {
            "user": user,
            "remaining_time": remaining,
            "expired": expired,
        },
    )


def resend_forgot_otp(request, user_id):
    user = get_object_or_404(Account, id=user_id)

    user.otp = generate_otp()
    user.otp_created_at = timezone.now()
    user.otp_purpose = "forgot"
    user.save()

    sent = send_otp_email(user.email, user.otp, purpose="forgot")
    if sent:
        messages.success(request, "New OTP sent to your email.")
    else:
        messages.error(request, "Failed to send OTP. Please try again.")

    return redirect("verify_forgot_otp", user_id=user.id)


def reset_password(request, user_id):
    user = get_object_or_404(Account, id=user_id)

    # Only allow if OTP was verified
    if user.otp_purpose != "forgot_verified":
        messages.error(request, "Please verify your OTP first.")
        return redirect("forgot_password")

    if request.method == "POST":
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, "accounts/reset_password.html", {"user": user})

        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters.")
            return render(request, "accounts/reset_password.html", {"user": user})

        user.set_password(password)
        user.otp_purpose = None
        user.save()

        messages.success(request, "Password reset successfully! You can now login.")
        return redirect("login")

    return render(request, "accounts/reset_password.html", {"user": user})
