from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages, auth
from django.utils import timezone

from accounts.models import Account
from accounts.email_utils import generate_otp, send_otp_email
from .models import Order, Transaction


# ── helpers ───────────────────────────────────────────────────────────────────

OTP_EXPIRY_MINUTES = 5

def _otp_remaining(otp_created_at):
    if not otp_created_at:
        return 0
    elapsed = (timezone.now() - otp_created_at).total_seconds()
    return max(0, int(OTP_EXPIRY_MINUTES * 60 - elapsed))


# ── Profile ───────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def profile(request):
    return render(request, 'dashboard/profile.html')


@login_required(login_url='login')
def edit_profile(request):
    if request.method == 'POST':
        user             = request.user
        user.first_name  = request.POST.get('first_name', '').strip()
        user.last_name   = request.POST.get('last_name', '').strip()
        user.phone_number = request.POST.get('phone_number', '').strip()

        # Profile photo
        if request.FILES.get('profile_photo'):
            user.profile_photo = request.FILES['profile_photo']

        user.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('dashboard_profile')

    return render(request, 'dashboard/edit_profile.html')


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
    """Step 1 — send OTP to email"""
    if request.method == 'POST':
        user             = request.user
        user.otp         = generate_otp()
        user.otp_created_at = timezone.now()
        user.otp_purpose = 'change_password'
        user.save()

        sent = send_otp_email(user.email, user.otp, purpose='change_password')
        if sent:
            messages.success(request, f'OTP sent to {user.email}')
            return redirect('dashboard_verify_change_password')
        else:
            messages.error(request, 'Failed to send OTP. Please try again.')

    return render(request, 'dashboard/change_password.html')


@login_required(login_url='login')
def verify_change_password(request):
    """Step 2 — verify OTP then set new password"""
    user      = request.user
    remaining = _otp_remaining(user.otp_created_at)
    expired   = (remaining == 0) or (user.otp_purpose != 'change_password')

    if request.method == 'POST':
        action = request.POST.get('action')

        # Verify OTP step
        if action == 'verify_otp':
            if expired:
                messages.error(request, 'OTP expired. Please request a new one.')
                return redirect('dashboard_change_password')

            entered_otp = request.POST.get('otp', '').strip()
            if entered_otp == user.otp:
                user.otp_purpose = 'change_password_verified'
                user.otp         = None
                user.otp_created_at = None
                user.save()
                return render(request, 'dashboard/change_password.html', {
                    'otp_verified': True
                })
            else:
                messages.error(request, 'Invalid OTP.')

        # Set new password step
        elif action == 'set_password':
            if user.otp_purpose != 'change_password_verified':
                messages.error(request, 'Please verify OTP first.')
                return redirect('dashboard_change_password')

            new_password     = request.POST.get('new_password', '')
            confirm_password = request.POST.get('confirm_password', '')

            if new_password != confirm_password:
                messages.error(request, 'Passwords do not match.')
                return render(request, 'dashboard/change_password.html', {'otp_verified': True})

            if len(new_password) < 8:
                messages.error(request, 'Password must be at least 8 characters.')
                return render(request, 'dashboard/change_password.html', {'otp_verified': True})

            user.set_password(new_password)
            user.otp_purpose = None
            user.save()

            # Re-login after password change
            auth.login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, 'Password changed successfully.')
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
        messages.success(request, 'New OTP sent.')
    else:
        messages.error(request, 'Failed to send OTP.')
    return redirect('dashboard_verify_change_password')


# ── Delete Account ────────────────────────────────────────────────────────────

@login_required(login_url='login')
def delete_account(request):
    """Step 1 — send OTP to email"""
    if request.method == 'POST':
        user             = request.user
        user.otp         = generate_otp()
        user.otp_created_at = timezone.now()
        user.otp_purpose = 'delete_account'
        user.save()

        sent = send_otp_email(user.email, user.otp, purpose='delete_account')
        if sent:
            messages.success(request, f'OTP sent to {user.email}')
            return redirect('dashboard_verify_delete_account')
        else:
            messages.error(request, 'Failed to send OTP. Please try again.')

    return render(request, 'dashboard/delete_account.html')


@login_required(login_url='login')
def verify_delete_account(request):
    """Step 2 — verify OTP then delete account"""
    user      = request.user
    remaining = _otp_remaining(user.otp_created_at)
    expired   = (remaining == 0) or (user.otp_purpose != 'delete_account')

    if request.method == 'POST':
        if expired:
            messages.error(request, 'OTP expired. Please request a new one.')
            return redirect('dashboard_delete_account')

        entered_otp = request.POST.get('otp', '').strip()
        if entered_otp == user.otp:
            auth.logout(request)
            user.delete()
            messages.success(request, 'Your account has been deleted.')
            return redirect('register')
        else:
            messages.error(request, 'Invalid OTP. Please try again.')

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
        messages.success(request, 'New OTP sent.')
    else:
        messages.error(request, 'Failed to send OTP.')
    return redirect('dashboard_verify_delete_account')