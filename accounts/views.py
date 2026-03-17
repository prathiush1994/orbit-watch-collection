from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages, auth
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from django.contrib.messages import get_messages
from .models import Account
from .forms import RegistrationForm
from .email_utils import generate_otp, send_otp_email, send_welcome_email


# ── helpers ───────────────────────────────────────────────────────────────────

OTP_EXPIRY_MINUTES = 5


def _otp_remaining(otp_created_at):
    """Returns seconds remaining for OTP. 0 if expired."""
    if not otp_created_at:
        return 0
    elapsed = (timezone.now() - otp_created_at).total_seconds()
    return max(0, int(OTP_EXPIRY_MINUTES * 60 - elapsed))


def _is_otp_expired(otp_created_at):
    return _otp_remaining(otp_created_at) == 0


# ── Registration ──────────────────────────────────────────────────────────────

def register(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name  = form.cleaned_data['last_name']
            email      = form.cleaned_data['email']
            password   = form.cleaned_data['password']

            # Create inactive user
            user = Account.objects.create_user(
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=password,
            )
            user.is_active      = False
            user.email_verified = False
            user.otp            = generate_otp()
            user.otp_created_at = timezone.now()
            user.otp_purpose    = 'register'
            user.save()

            sent = send_otp_email(email, user.otp, purpose='register')
            if sent:
                messages.success(request, f'Verification code sent to {email}')
            else:
                messages.warning(request, 'Account created but email failed. Contact support.')

            return redirect('verify_email', user_id=user.id)
    else:
        form = RegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


# ── Email Verification (after registration) ───────────────────────────────────

def verify_email(request, user_id):
    user = get_object_or_404(Account, id=user_id)

    # Already verified — send them to login
    if user.is_active and user.email_verified:
        messages.info(request, 'Your email is already verified. Please login.')
        return redirect('login')

    remaining = _otp_remaining(user.otp_created_at)
    expired   = (remaining == 0)

    if request.method == 'POST':
        if expired:
            messages.error(request, 'OTP has expired. Please request a new one.')
            return render(request, 'accounts/verify_email.html', {
                'user': user, 'remaining_time': 0, 'expired': True
            })

        entered_otp = request.POST.get('otp', '').strip()

        if entered_otp == user.otp:
            user.is_active      = True
            user.email_verified = True
            user.otp            = None
            user.otp_created_at = None
            user.otp_purpose    = None
            user.save()

            send_welcome_email(user.email, user.first_name)
            messages.success(request, 'Email verified! You can now login.')
            return redirect('login')
        else:
            messages.error(request, 'Invalid OTP. Please try again.')

    return render(request, 'accounts/verify_email.html', {
        'user': user,
        'remaining_time': remaining,
        'expired': expired,
    })


def resend_otp(request, user_id):
    user = get_object_or_404(Account, id=user_id)

    if user.is_active and user.email_verified:
        return redirect('login')

    user.otp            = generate_otp()
    user.otp_created_at = timezone.now()
    user.otp_purpose    = 'register'
    user.save()

    sent = send_otp_email(user.email, user.otp, purpose='register')
    if sent:
        messages.success(request, 'New OTP sent to your email.')
    else:
        messages.error(request, 'Failed to send OTP. Please try again.')

    return redirect('verify_email', user_id=user.id)


# ── Login ─────────────────────────────────────────────────────────────────────

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

            auth.login(request, user,
                       backend='django.contrib.auth.backends.ModelBackend')
            del request.session['login_user_id']
            messages.success(request, f'Welcome back, {user.first_name}!')
            return redirect(request.GET.get('next', 'home'))
        else:
            messages.error(request, 'Invalid OTP. Please try again.')

    return render(request, 'accounts/verify_login_otp.html', {
        'user': user,
        'remaining_time': remaining,
        'expired': expired,
    })


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
    # Clear all pending messages before logout
    storage = get_messages(request)
    for _ in storage:
        pass  # iterating clears them

    auth.logout(request)
    messages.success(request, 'Logged out successfully.')
    response = redirect('login')
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma']        = 'no-cache'
    response['Expires']       = '0'
    return response


# ── Forgot Password ───────────────────────────────────────────────────────────

def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()

        try:
            user = Account.objects.get(email=email)
        except Account.DoesNotExist:
            # Show same message to avoid user enumeration
            messages.success(request, 'If that email exists, an OTP has been sent.')
            return redirect('forgot_password')

        user.otp            = generate_otp()
        user.otp_created_at = timezone.now()
        user.otp_purpose    = 'forgot'
        user.save()

        sent = send_otp_email(email, user.otp, purpose='forgot')
        if sent:
            messages.success(request, f'OTP sent to {email}.')
        else:
            messages.error(request, 'Failed to send OTP. Please try again.')
            return redirect('forgot_password')

        return redirect('verify_forgot_otp', user_id=user.id)

    return render(request, 'accounts/forgot_password.html')


def verify_forgot_otp(request, user_id):
    user = get_object_or_404(Account, id=user_id)

    # Safety: only allow if otp_purpose is 'forgot'
    if user.otp_purpose != 'forgot':
        messages.error(request, 'Invalid request.')
        return redirect('forgot_password')

    remaining = _otp_remaining(user.otp_created_at)
    expired   = (remaining == 0)

    if request.method == 'POST':
        if expired:
            messages.error(request, 'OTP has expired. Please request a new one.')
            return render(request, 'accounts/verify_forgot_otp.html', {
                'user': user, 'remaining_time': 0, 'expired': True
            })

        entered_otp = request.POST.get('otp', '').strip()

        if entered_otp == user.otp:
            # Mark OTP used but keep purpose so reset_password view can verify
            user.otp            = None
            user.otp_created_at = None
            user.otp_purpose    = 'forgot_verified'
            user.save()
            return redirect('reset_password', user_id=user.id)
        else:
            messages.error(request, 'Invalid OTP. Please try again.')

    return render(request, 'accounts/verify_forgot_otp.html', {
        'user': user,
        'remaining_time': remaining,
        'expired': expired,
    })


def resend_forgot_otp(request, user_id):
    user = get_object_or_404(Account, id=user_id)

    user.otp            = generate_otp()
    user.otp_created_at = timezone.now()
    user.otp_purpose    = 'forgot'
    user.save()

    sent = send_otp_email(user.email, user.otp, purpose='forgot')
    if sent:
        messages.success(request, 'New OTP sent to your email.')
    else:
        messages.error(request, 'Failed to send OTP. Please try again.')

    return redirect('verify_forgot_otp', user_id=user.id)


def reset_password(request, user_id):
    user = get_object_or_404(Account, id=user_id)

    # Only allow if OTP was verified
    if user.otp_purpose != 'forgot_verified':
        messages.error(request, 'Please verify your OTP first.')
        return redirect('forgot_password')

    if request.method == 'POST':
        password         = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'accounts/reset_password.html', {'user': user})

        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters.')
            return render(request, 'accounts/reset_password.html', {'user': user})

        user.set_password(password)
        user.otp_purpose = None
        user.save()

        messages.success(request, 'Password reset successfully! You can now login.')
        return redirect('login')

    return render(request, 'accounts/reset_password.html', {'user': user})