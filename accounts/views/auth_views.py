from django.contrib import messages, auth
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.urls import reverse
from ..models import Account
from ..email_utils import generate_otp, send_otp_email
from .otp_data import _otp_remaining
from wishlist.views import _get_or_create_wishlist
from carts.views import _get_or_create_cart
from urllib.parse import urlencode


@never_cache
def login(request):
    if request.user.is_authenticated:
        return redirect("home")
    next_page = request.GET.get("next", "home")
    request.session["next_page"] = next_page

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")

        try:
            account = Account.objects.get(email=email)
        except Account.DoesNotExist:
            messages.error(
                request, "Invalid email or password.",
                extra_tags="login_message"
            )
            return render(request, "accounts/login.html", status=422)

        if not account.is_active and account.email_verified:
            messages.warning(
                request,
                "Your account has been temporarily restricted. Please contact support.",
                extra_tags="login_message",
            )
            return render(request, "accounts/login.html", status=403)

        user = auth.authenticate(email=email, password=password)

        if user is None:
            messages.error(
                request, "Invalid email or password.",
                extra_tags="login_message"
            )
            return render(request, "accounts/login.html", status=401)

        if not user.email_verified or not user.is_active:
            user.otp = generate_otp()
            user.otp_created_at = timezone.now()
            user.otp_purpose = "register"
            user.save()
            send_otp_email(user.email, user.otp, purpose="register")
            return redirect("verify_email", user_id=user.id)

        # Send login OTP
        user.otp = generate_otp()
        user.otp_created_at = timezone.now()
        user.otp_purpose = "login"
        user.save()
        send_otp_email(user.email, user.otp, purpose="login")

        # Store user id in session temporarily
        request.session["login_user_id"] = user.id
        params = {"next": next_page, "source": "login"}
        verify_login_otp = f"/user/orbit-watch/verify-login-otp/?{urlencode(params)}"
        return redirect(verify_login_otp)

    return render(request, "accounts/login.html", status=200)


# ── Verify Login OTP
def verify_login_otp(request):
    user_id = request.session.get("login_user_id")
    next_page = request.session.get("next_page", "home")
    if not user_id:
        messages.error(
            request, "Session expired. Please login again.",
            extra_tags="login_message"
        )
        next_page = request.GET.get("next", "home")
        return redirect(f"{reverse('login')}?next={next_page}")

    user = get_object_or_404(Account, id=user_id)
    remaining = _otp_remaining(user.otp_created_at)
    expired = remaining == 0

    if request.method == "POST":
        if expired:
            messages.error(
                request,
                "OTP expired. Please login again.",
                extra_tags="verify_login_otp",
            )
            return render(
                request,
                "accounts/verify_login_otp.html",
                {"remaining_time": 0, "expired": True},
                status=422,
            )

        entered_otp = request.POST.get("otp", "").strip()

        if entered_otp == user.otp:
            user.otp = None
            user.otp_created_at = None
            user.otp_purpose = None
            user.save()
            if not request.session.session_key:
                request.session.create()
            auth.login(
                request, user, 
                backend="django.contrib.auth.backends.ModelBackend"
            )
            _get_or_create_cart(request)
            _get_or_create_wishlist(request)
            request.session.pop("login_user_id", None)
            destination = request.session.pop(
                "next_page",
                "home"
            )
            return redirect(destination)

        else:
            messages.error(
                request, "Invalid OTP. Please try again.",
                extra_tags="verify_login_otp"
            )
            return render(
                request,
                "accounts/verify_login_otp.html",
                {
                    "user": user,
                    "remaining_time": remaining,
                    "expired": expired,
                },
                status=422,
            )

    return render(
        request,
        "accounts/verify_login_otp.html",
        {
            "user": user,
            "remaining_time": remaining,
            "expired": expired,
        },
    )


# ── Resend Login OTP
def resend_login_otp(request):
    user_id = request.session.get("login_user_id")
    if not user_id:
        messages.error(
            request, "Session expired. Please login again.",
            extra_tags="login_message"
        )
        next_page = request.GET.get("next", "home")
        return redirect(f"{reverse('login')}?next={next_page}")

    user = get_object_or_404(Account, id=user_id)
    user.otp = generate_otp()
    user.otp_created_at = timezone.now()
    user.otp_purpose = "login"
    user.save()

    sent = send_otp_email(user.email, user.otp, purpose="login")
    if sent:
        messages.success(
            request, "New OTP sent to your email.",
            extra_tags="verify_login_otp")
    else:
        messages.error(
            request, "Failed to send OTP. Please try again.",
            extra_tags="verify_login_otp")
    next_page = request.GET.get("next", "home")
    return redirect(f"{reverse('verify_login_otp')}?next={next_page}")


# ── Logout
@login_required(login_url="login")
def logout(request):
    auth.logout(request)
    messages.success(request, "Logged out successfully.")
    response = redirect("login")
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response
