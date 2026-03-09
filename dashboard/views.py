from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages, auth
from django.utils import timezone
from datetime import timedelta
from accounts.models import Account
from accounts.email_utils import generate_otp, send_otp_email
from .models import Order, Transaction

import base64
import uuid
from django.core.files.base import ContentFile


OTP_EXPIRY_MINUTES = 2

def _otp_remaining(otp_created_at):
    """Returns seconds remaining, or 0 if expired."""
    if not otp_created_at:
        return 0
    expiry = otp_created_at + timedelta(minutes=OTP_EXPIRY_MINUTES)
    remaining = (expiry - timezone.now()).total_seconds()
    return max(int(remaining), 0)


# ── Profile ───────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def profile(request):
    return render(request, 'dashboard/profile.html')


@login_required(login_url='login')
def edit_profile(request):
    if request.method == 'POST':
        user = request.user
        user.first_name   = request.POST.get('first_name', '').strip()
        user.last_name    = request.POST.get('last_name', '').strip()
        user.phone_number = request.POST.get('phone_number', '').strip()

        # Handle photo delete
        if request.POST.get('delete_photo') == '1':
            if user.profile_photo:
                user.profile_photo.delete(save=False)
                user.profile_photo = None

        # Handle cropped photo (base64 from JS cropper)
        cropped_photo = request.POST.get('cropped_photo', '').strip()
        if cropped_photo and cropped_photo.startswith('data:image'):
            try:
                format, imgstr = cropped_photo.split(';base64,')
                ext      = format.split('/')[-1]
                filename = f"profile_{uuid.uuid4().hex}.{ext}"
                decoded  = base64.b64decode(imgstr)
                user.profile_photo.save(filename, ContentFile(decoded), save=False)
            except Exception:
                pass

        user.save()
        messages.success(request, 'Profile updated successfully.', extra_tags='edit_profile')
        return redirect('dashboard_profile')

    return render(request, 'dashboard/edit_profile.html')


# ── Change Email ──────────────────────────────────────────────────────────────

@login_required(login_url='login')
def change_email(request):
    user = request.user

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'send_otp':
            new_email = request.POST.get('new_email', '').strip().lower()

            if not new_email:
                messages.error(request, 'Please enter a valid email address.', extra_tags='change_email')
                return redirect('dashboard_change_email')

            if new_email == user.email:
                messages.error(request, 'New email is the same as your current email.', extra_tags='change_email')
                return redirect('dashboard_change_email')

            if Account.objects.filter(email=new_email).exclude(pk=user.pk).exists():
                messages.error(request, 'This email is already registered with another account.', extra_tags='change_email')
                return redirect('dashboard_change_email')

            otp = generate_otp()
            user.otp            = otp
            user.otp_created_at = timezone.now()
            user.otp_purpose    = 'change_email'
            request.session['pending_new_email'] = new_email
            user.save()

            send_otp_email(new_email, otp, purpose='change_email')
            messages.success(request, f'Verification code sent to {new_email}.', extra_tags='change_email')
            return redirect('dashboard_change_email')

        elif action == 'verify_otp':
            entered_otp   = request.POST.get('otp', '').strip()
            pending_email = request.session.get('pending_new_email', '')
            remaining     = _otp_remaining(user.otp_created_at)

            if not pending_email:
                messages.error(request, 'Session expired. Please start again.', extra_tags='change_email')
                return redirect('dashboard_change_email')

            if remaining <= 0:
                messages.error(request, 'OTP has expired. Please request a new one.', extra_tags='change_email')
                return redirect('dashboard_change_email')

            if entered_otp != user.otp or user.otp_purpose != 'change_email':
                messages.error(request, 'Invalid OTP. Please try again.', extra_tags='change_email')
                return redirect('dashboard_change_email')

            user.email          = pending_email
            user.otp            = None
            user.otp_created_at = None
            user.otp_purpose    = None
            user.save()
            del request.session['pending_new_email']

            messages.success(request, 'Your email has been updated successfully!', extra_tags='profile')
            return redirect('dashboard_profile')

    pending_email = request.session.get('pending_new_email', '')
    remaining     = _otp_remaining(user.otp_created_at) if user.otp_created_at else 0
    is_otp_step   = (
        pending_email
        and user.otp_purpose == 'change_email'
        and remaining > 0
    )

    context = {
        'step':           'verify_otp' if is_otp_step else 'enter_email',
        'pending_email':  pending_email,
        'remaining_time': remaining,
    }
    return render(request, 'dashboard/change_email.html', context)


@login_required(login_url='login')
def resend_change_email_otp(request):
    user          = request.user
    pending_email = request.session.get('pending_new_email', '')

    if not pending_email:
        messages.error(request, 'Session expired. Please start again.', extra_tags='change_email')
        return redirect('dashboard_change_email')

    otp = generate_otp()
    user.otp            = otp
    user.otp_created_at = timezone.now()
    user.otp_purpose    = 'change_email'
    user.save()

    send_otp_email(pending_email, otp, purpose='change_email')
    messages.success(request, 'New OTP sent.', extra_tags='change_email')
    return redirect('dashboard_change_email')


# ── Orders ────────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def orders(request):
    user_orders = Order.objects.filter(user=request.user).prefetch_related('items__product')
    return render(request, 'dashboard/orders.html', {'orders': user_orders})


# ── Transactions ──────────────────────────────────────────────────────────────

@login_required(login_url='login')
def transactions(request):
    user_transactions = Transaction.objects.filter(user=request.user)
    return render(request, 'dashboard/transactions.html', {'transactions': user_transactions})


# ── Returns ───────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def returns(request):
    returned_orders = Order.objects.filter(user=request.user, status__in=['returned', 'cancelled'])
    return render(request, 'dashboard/returns.html', {'orders': returned_orders})


# ── Change Password ───────────────────────────────────────────────────────────

@login_required(login_url='login')
def change_password(request):
    if request.method == 'POST':
        user             = request.user
        user.otp         = generate_otp()
        user.otp_created_at = timezone.now()
        user.otp_purpose = 'change_password'
        user.save()

        sent = send_otp_email(user.email, user.otp, purpose='change_password')
        if sent:
            messages.success(request, f'OTP sent to {user.email}', extra_tags='change_password')
            return redirect('dashboard_verify_change_password')
        else:
            messages.error(request, 'Failed to send OTP. Please try again.', extra_tags='change_password')

    return render(request, 'dashboard/change_password.html')


@login_required(login_url='login')
def verify_change_password(request):
    user      = request.user
    remaining = _otp_remaining(user.otp_created_at)
    expired   = (remaining == 0) or (user.otp_purpose != 'change_password')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'verify_otp':
            if expired:
                messages.error(request, 'OTP expired. Please request a new one.', extra_tags='change_password')
                return redirect('dashboard_change_password')

            entered_otp = request.POST.get('otp', '').strip()
            if entered_otp == user.otp:
                user.otp_purpose    = 'change_password_verified'
                user.otp            = None
                user.otp_created_at = None
                user.save()
                return render(request, 'dashboard/change_password.html', {
                    'otp_verified': True
                })
            else:
                messages.error(request, 'Invalid OTP.', extra_tags='change_password')

        elif action == 'set_password':
            if user.otp_purpose != 'change_password_verified':
                messages.error(request, 'Please verify OTP first.', extra_tags='change_password')
                return redirect('dashboard_change_password')

            new_password     = request.POST.get('new_password', '')
            confirm_password = request.POST.get('confirm_password', '')

            if new_password != confirm_password:
                messages.error(request, 'Passwords do not match.', extra_tags='change_password')
                return render(request, 'dashboard/change_password.html', {'otp_verified': True})

            if len(new_password) < 8:
                messages.error(request, 'Password must be at least 8 characters.', extra_tags='change_password')
                return render(request, 'dashboard/change_password.html', {'otp_verified': True})

            user.set_password(new_password)
            user.otp_purpose = None
            user.save()

            auth.login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, 'Password changed successfully.', extra_tags='profile')
            return redirect('dashboard_profile')

    return render(request, 'dashboard/change_password.html', {
        'remaining_time': remaining,
        'expired': expired,
    })


@login_required(login_url='login')
def resend_change_password_otp(request):
    user             = request.user
    user.otp         = generate_otp()
    user.otp_created_at = timezone.now()
    user.otp_purpose = 'change_password'
    user.save()

    sent = send_otp_email(user.email, user.otp, purpose='change_password')
    if sent:
        messages.success(request, 'New OTP sent.', extra_tags='change_password')
    else:
        messages.error(request, 'Failed to send OTP.', extra_tags='change_password')
    return redirect('dashboard_verify_change_password')


# ── Delete Account ────────────────────────────────────────────────────────────

@login_required(login_url='login')
def delete_account(request):
    if request.method == 'POST':
        user             = request.user
        user.otp         = generate_otp()
        user.otp_created_at = timezone.now()
        user.otp_purpose = 'delete_account'
        user.save()

        sent = send_otp_email(user.email, user.otp, purpose='delete_account')
        if sent:
            messages.success(request, f'OTP sent to {user.email}', extra_tags='delete_account')
            return redirect('dashboard_verify_delete_account')
        else:
            messages.error(request, 'Failed to send OTP. Please try again.', extra_tags='delete_account')

    return render(request, 'dashboard/delete_account.html')


@login_required(login_url='login')
def verify_delete_account(request):
    user      = request.user
    remaining = _otp_remaining(user.otp_created_at)
    expired   = (remaining == 0) or (user.otp_purpose != 'delete_account')

    if request.method == 'POST':
        if expired:
            messages.error(request, 'OTP expired. Please request a new one.', extra_tags='delete_account')
            return redirect('dashboard_delete_account')

        entered_otp = request.POST.get('otp', '').strip()
        if entered_otp == user.otp:
            auth.logout(request)
            user.delete()
            messages.success(request, 'Your account has been deleted.', extra_tags='delete_account')
            return redirect('register')
        else:
            messages.error(request, 'Invalid OTP. Please try again.', extra_tags='delete_account')

    return render(request, 'dashboard/verify_delete_account.html', {
        'remaining_time': remaining,
        'expired': expired,
    })


@login_required(login_url='login')
def resend_delete_account_otp(request):
    user             = request.user
    user.otp         = generate_otp()
    user.otp_created_at = timezone.now()
    user.otp_purpose = 'delete_account'
    user.save()

    sent = send_otp_email(user.email, user.otp, purpose='delete_account')
    if sent:
        messages.success(request, 'New OTP sent.', extra_tags='delete_account')
    else:
        messages.error(request, 'Failed to send OTP.', extra_tags='delete_account')
    return redirect('dashboard_verify_delete_account')


# ── Address (Demo) ────────────────────────────────────────────────────────────

@login_required(login_url='login')
def address(request):
    return render(request, 'dashboard/address.html')


# ── Wallet (Demo) ─────────────────────────────────────────────────────────────

@login_required(login_url='login')
def wallet(request):
    return render(request, 'dashboard/wallet.html')


# ── Coupons (Demo) ────────────────────────────────────────────────────────────

@login_required(login_url='login')
def coupons(request):
    return render(request, 'dashboard/coupons.html')