from django.contrib import messages, auth
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib.messages import get_messages
from django.views.decorators.cache import never_cache

from ..models import Account
from ..email_utils import generate_otp, send_otp_email
from .otp_data import _otp_remaining
from carts.views    import merge_cart
from wishlist.views import merge_wishlist


# ── Login ─────────────────────────────────────────────────────────────────────
@never_cache
def login(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        email    = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')

        try:
            account = Account.objects.get(email=email)
        except Account.DoesNotExist:
            messages.error(request, 'Invalid email or password.')
            return render(request, 'accounts/login.html')

        # Check if user is blocked
        if not account.is_active and account.email_verified:
            messages.error(request, 'Your account has been temporarily restricted. Please contact support.')
            return render(request, 'accounts/login.html')

        user = auth.authenticate(email=email, password=password)

        if user is None:
            messages.error(request, 'Invalid email or password.')
            return render(request, 'accounts/login.html')

        # Not verified yet
        if not user.email_verified or not user.is_active:
            user.otp            = generate_otp()
            user.otp_created_at = timezone.now()
            user.otp_purpose    = 'register'
            user.save()
            send_otp_email(user.email, user.otp, purpose='register')
            messages.warning(request, 'Please verify your email first. A new OTP has been sent.')
            return redirect('verify_email', user_id=user.id)

        # Send login OTP
        user.otp            = generate_otp()
        user.otp_created_at = timezone.now()
        user.otp_purpose    = 'login'
        user.save()
        send_otp_email(user.email, user.otp, purpose='login')

        # Store user id in session temporarily
        request.session['login_user_id'] = user.id
        messages.success(request, f'OTP sent to {user.email}')
        return redirect('verify_login_otp')

    return render(request, 'accounts/login.html')


# ── Verify Login OTP ──────────────────────────────────────────────────────────
def verify_login_otp(request):
    user_id = request.session.get('login_user_id')
    if not user_id:
        messages.error(request, 'Session expired. Please login again.')
        return redirect('login')

    user      = get_object_or_404(Account, id=user_id)
    remaining = _otp_remaining(user.otp_created_at)
    expired   = (remaining == 0)

    if request.method == 'POST':
        if expired:
            messages.error(request, 'OTP expired. Please login again.')
            return render(request, 'accounts/verify_login_otp.html', {
                'remaining_time': 0, 'expired': True
            })

        entered_otp = request.POST.get('otp', '').strip()

        if entered_otp == user.otp:
            user.otp            = None
            user.otp_created_at = None
            user.otp_purpose    = None
            user.save()
            if not request.session.session_key:
                request.session.create()
            old_session_key = request.session.session_key
            auth.login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            request.session['old_session_key'] = old_session_key
            merge_cart(request)
            merge_wishlist(request)

            del request.session['login_user_id']

            messages.success(request, f'Welcome back, {user.first_name}!')
            return redirect(request.GET.get('next', 'home'))

        else:
            messages.error(request, 'Invalid OTP. Please try again.')

    return render(request, 'accounts/verify_login_otp.html', {
        'user'          : user,
        'remaining_time': remaining,
        'expired'       : expired,
    })


# ── Resend Login OTP ──────────────────────────────────────────────────────────
def resend_login_otp(request):
    user_id = request.session.get('login_user_id')
    if not user_id:
        return redirect('login')

    user = get_object_or_404(Account, id=user_id)
    user.otp            = generate_otp()
    user.otp_created_at = timezone.now()
    user.otp_purpose    = 'login'
    user.save()

    sent = send_otp_email(user.email, user.otp, purpose='login')
    if sent:
        messages.success(request, 'New OTP sent to your email.')
    else:
        messages.error(request, 'Failed to send OTP. Please try again.')

    return redirect('verify_login_otp')


# ── Logout ────────────────────────────────────────────────────────────────────
@login_required(login_url='login')
def logout(request):
    auth.logout(request)
    messages.success(request, 'Logged out successfully.')
    response = redirect('login')
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma']        = 'no-cache'
    response['Expires']       = '0'
    return response