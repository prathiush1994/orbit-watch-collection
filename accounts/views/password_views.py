from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from ..models import Account
from ..email_utils import generate_otp, send_otp_email
from .otp_data import _otp_remaining
from urllib.parse import urlencode
import re 


def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        try:
            user = Account.objects.get(email=email)
            request.session["user_id"] = user.id
        except Account.DoesNotExist:
            messages.success(
                request, "No account found with this email address.",
                extra_tags="forgot_password_message"
                )
            return render(
                request, "accounts/forgot_password.html",
                status=404
                )

        user.otp = generate_otp()
        user.otp_created_at = timezone.now()
        user.otp_purpose = "forgot"
        user.save()

        sent = send_otp_email(email, user.otp, purpose="forgot")
        if not sent:
            messages.error(
                request, "Failed to send OTP. Please try again.",
                extra_tags="forgot_password_message"
                )
            return redirect("forgot_password")
        params = {
            "next": "login",
            "source": "forgot_password"
        }
        verify_forgot_otp = (
            f"/user/orbit-watch/verify_forgot_otp/?{urlencode(params)}"
            )
        return redirect(verify_forgot_otp)

    return render(request, "accounts/forgot_password.html")


def verify_forgot_otp(request):
    user_id = request.session.get("user_id")
    user = get_object_or_404(Account, id=user_id)

    if user.otp_purpose != "forgot":
        messages.error(
            request, "Invalid request.",
            extra_tags="forgot_password_message"
            )
        return redirect("forgot_password")

    remaining = _otp_remaining(user.otp_created_at)
    expired = remaining == 0

    if request.method == "POST":
        if expired:
            messages.error(
                request, "OTP has expired. Please request a new one.",
                extra_tags="verify_forgot_otp_message"
                )
            return render(
                request,
                "accounts/verify_forgot_otp.html",
                {"user": user, "remaining_time": 0, "expired": True},
                status=422
            )

        entered_otp = request.POST.get("otp", "").strip()

        if entered_otp == user.otp:
            user.otp = None
            user.otp_created_at = None
            user.otp_purpose = "forgot_verified"
            user.save()
            return redirect("reset_password")
        else:
            messages.error(
                request, "Invalid OTP. Please try again.",
                extra_tags="verify_forgot_otp_message"
                )

    return render(
        request,
        "accounts/verify_forgot_otp.html",
        {
            "user": user,
            "remaining_time": remaining,
            "expired": expired,
        },
    )


def resend_forgot_otp(request):
    user_id = request.session.get("user_id")
    user = get_object_or_404(Account, id=user_id)
    user.otp = generate_otp()
    user.otp_created_at = timezone.now()
    user.otp_purpose = "forgot"
    user.save()
    sent = send_otp_email(user.email, user.otp, purpose="forgot")
    if not sent:
        messages.error(
            request, "Failed to send OTP. Please try again.",
            extra_tags="verify_forgot_otp_message"
            )
    return redirect("verify_forgot_otp")


def reset_password(request):
    user_id = request.session.get("user_id")
    if not user_id:
        messages.error(
            request,
            "Session expired. Please start again.",
            extra_tags="forgot_password_message"
        )
        return redirect("forgot_password")
    user = get_object_or_404(Account, id=user_id)

    if user.otp_purpose != "forgot_verified":
        messages.error(
            request, "Please verify your OTP first.",
            extra_tags="forgot_password_message"
            )
        return redirect("forgot_password")

    if request.method == "POST":
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")
        if password != confirm_password:
            messages.error(
                request,
                "Passwords do not match.",
                extra_tags="reset_password_message"
            )
            return render(
                request,
                "accounts/reset_password.html",
                {"user": user},
                status=422
            )
        if password and confirm_password:
            if password != confirm_password:
                messages.error(
                    request, "Passwords do not match",
                    extra_tags="reset_password_message"
                    )
                return render(
                    request, "accounts/reset_password.html",
                    {"user": user}, status=422
                    )

            if len(password) < 8:
                messages.error(
                    request, "Password must be at least 8 characters.",
                    extra_tags="reset_password_message"
                    )
                return render(
                    request, "accounts/reset_password.html",
                    {"user": user}, status=422
                    )

            if not re.search(r"[A-Z]", password):
                messages.error(
                    request, 
                    "Password must contain at least one uppercase letter.",
                    extra_tags="reset_password_message"
                    )
                return render(
                    request, "accounts/reset_password.html", 
                    {"user": user}, status=422
                    )

            if not re.search(r"[a-z]", password):
                messages.error(
                    request,
                    "Password must contain at least one lowercase letter.",
                    extra_tags="reset_password_message"
                    )
                return render(
                    request, "accounts/reset_password.html",
                    {"user": user}, status=422
                    )

            if not re.search(r"\d", password):
                messages.error(
                    request,
                    "Password must contain at least one number.",
                    extra_tags="reset_password_message"
                    ) 
                return render(
                    request, "accounts/reset_password.html",
                    {"user": user}, status=422
                    )

            if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
                messages.error(
                    request, 
                    "Password must contain at least one special character.",
                    extra_tags="reset_password_message"
                    ) 
                return render(
                    request, "accounts/reset_password.html",
                    {"user": user}, status=422
                    )

        user.set_password(password)
        user.otp_purpose = None
        user.save()
        request.session.pop("user_id", None)

        messages.success(
            request, "Password reset successfully! You can now login.",
            extra_tags="login_message"
            )
        return redirect("login")

    return render(request, "accounts/reset_password.html", {"user": user})
