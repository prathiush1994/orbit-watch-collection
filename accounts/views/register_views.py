from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from ..models import Account
from ..forms import RegistrationForm
from ..email_utils import generate_otp, send_otp_email, send_welcome_email
from .otp_data import _otp_remaining
from urllib.parse import urlencode


def register(request):
    if request.user.is_authenticated:
        return redirect("home")
    next_page = request.GET.get("next", "login")
    request.session["next_page"] = next_page

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data["first_name"]
            last_name = form.cleaned_data["last_name"]
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            user = Account.objects.create_user(
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=password,
            )
            user.is_active = False
            user.email_verified = False
            user.otp = generate_otp()
            user.otp_created_at = timezone.now()
            user.otp_purpose = "register"
            user.save()

            sent = send_otp_email(email, user.otp, purpose="register")
            if not sent:
                messages.error(
                    request,
                    "Failed to send verification email. Please try again.",
                    extra_tags="register_message"
                )
                return render(
                    request,
                    "accounts/register.html",
                    {"form": form},
                    status=422
                )
            request.session["user_id"] = user.id
            params = {
                "next": next_page,
                "source": "register",
                "flow": "email_verification"
            }
            verify_email = (
                f"/user/orbit-watch/verify-email/?{urlencode(params)}"
            )
            return redirect(verify_email)
        else:
            return render(
                request, "accounts/register.html",
                {"form": form}, status=422
                )
    else:
        form = RegistrationForm()

    return render(request, "accounts/register.html", {"form": form})


def verify_email(request):
    user_id = request.session.get("user_id")
    user = get_object_or_404(Account, id=user_id)

    if user.is_active and user.email_verified:
        return redirect("login")

    remaining = _otp_remaining(user.otp_created_at)
    expired = remaining == 0

    if request.method == "POST":
        if expired:
            messages.error(
                request, "OTP has expired. Please request a new one.",
                extra_tags="verify_email_message"
                )
            return render(
                request,
                "accounts/verify_email.html",
                {"user": user, "remaining_time": 0, "expired": True},
                status=422
            )

        entered_otp = request.POST.get("otp", "").strip()

        if entered_otp == user.otp:
            user.is_active = True
            user.email_verified = True
            user.otp = None
            user.otp_created_at = None
            user.otp_purpose = None
            user.save()
            request.session.pop("user_id", None)
            send_welcome_email(user.email, user.first_name)
            messages.success(
                request, "Email verified! You can now login.",
                extra_tags="login_message"
                )
            return redirect("login")
        else:
            messages.error(
                request, "Invalid OTP. Please try again.",
                extra_tags="verify_email_message"
                )
    
    return render(
        request,
        "accounts/verify_email.html",
        {
            "user": user,
            "remaining_time": remaining,
            "expired": expired,
        },
    )


def resend_otp(request):
    user_id = request.session.get("user_id")
    next_page = request.session.get("next", "login")

    if not user_id:
        messages.error(
            request,
            "Verification session expired. Please register again.",
            extra_tags="register_message"
        )
        return redirect("register")
    user = get_object_or_404(Account, id=user_id)
    if user.is_active and user.email_verified:
        return redirect("login")

    user.otp = generate_otp()
    user.otp_created_at = timezone.now()
    user.otp_purpose = "register"
    user.save()

    sent = send_otp_email(user.email, user.otp, purpose="register")
    if not sent:
        messages.error(
            request, "Failed to send OTP. Please try again.",
            extra_tags="verify_email_message"
            )
    params = {
        "next": next_page,
        "source": "register",
        "flow": "resending_the_otp"
    }
    verify_email = (
        f"/user/orbit-watch/verify-email/?{urlencode(params)}"
    )
    return redirect(verify_email)