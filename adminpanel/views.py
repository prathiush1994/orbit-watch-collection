from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages, auth
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.decorators.http import require_POST

from accounts.models import Account
from store.models import Product, ProductVariant
from category.models import Category
from brands.models import Brand

from .decorators import admin_required


# ── Admin Login / Logout ──────────────────────────────────────────────────────

def admin_login(request):
    if request.user.is_authenticated:
        if request.user.is_superadmin or request.user.is_staff:
            return redirect('admin_dashboard')

    if request.method == 'POST':
        email    = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        user     = auth.authenticate(email=email, password=password)

        if user is None:
            messages.error(request, 'Invalid email or password.')
            return render(request, 'adminpanel/login.html')

        if not (user.is_superadmin or user.is_staff):
            messages.error(request, 'You do not have admin access.')
            return render(request, 'adminpanel/login.html')

        auth.login(request, user)
        return redirect('admin_dashboard')

    return render(request, 'adminpanel/login.html')


@admin_required
def admin_logout(request):
    auth.logout(request)
    return redirect('admin_login')


# ── Dashboard ─────────────────────────────────────────────────────────────────

@admin_required
def dashboard(request):
    total_users      = Account.objects.filter(is_admin=False, is_superadmin=False).count()
    active_users     = Account.objects.filter(is_admin=False, is_superadmin=False, is_active=True).count()
    blocked_users    = Account.objects.filter(is_admin=False, is_superadmin=False, is_active=False).count()

    # Product counts use ProductVariant (is_available lives here now)
    total_products   = ProductVariant.objects.count()
    active_products  = ProductVariant.objects.filter(is_available=True).count()

    total_categories = Category.objects.count()
    total_brands     = Brand.objects.count()

    recent_users = Account.objects.filter(
        is_admin=False, is_superadmin=False
    ).order_by('-date_joined')[:5]

    context = {
        'total_users'      : total_users,
        'active_users'     : active_users,
        'blocked_users'    : blocked_users,
        'total_products'   : total_products,
        'active_products'  : active_products,
        'total_categories' : total_categories,
        'total_brands'     : total_brands,
        'recent_users'     : recent_users,
    }
    return render(request, 'adminpanel/dashboard.html', context)


# ── User Management ───────────────────────────────────────────────────────────

@admin_required
def user_list(request):
    search_query = request.GET.get('q', '').strip()

    users = Account.objects.filter(
        is_admin=False, is_superadmin=False
    ).order_by('-date_joined')

    if search_query:
        users = users.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)  |
            Q(email__icontains=search_query)
        )

    paginator = Paginator(users, 10)
    page      = request.GET.get('page', 1)
    users     = paginator.get_page(page)

    context = {
        'users'        : users,
        'search_query' : search_query,
    }
    return render(request, 'adminpanel/users.html', context)


@admin_required
@require_POST
def toggle_user_status(request, user_id):
    user = get_object_or_404(Account, id=user_id)

    if user.is_admin or user.is_superadmin:
        messages.error(request, 'Cannot block admin users.')
        return redirect('admin_user_list')

    user.is_active = not user.is_active
    user.save()

    action = 'unblocked' if user.is_active else 'blocked'
    messages.success(request, f'{user.get_full_name()} has been {action}.')
    return redirect('admin_user_list')


# ── Settings ──────────────────────────────────────────────────────────────────

@admin_required
def settings(request):
    if request.method == 'POST':
        current_password = request.POST.get('current_password', '')
        new_password     = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')
        user             = request.user

        if not user.check_password(current_password):
            messages.error(request, 'Current password is incorrect.')
            return render(request, 'adminpanel/settings.html')

        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
            return render(request, 'adminpanel/settings.html')

        if len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters.')
            return render(request, 'adminpanel/settings.html')

        user.set_password(new_password)
        user.save()
        auth.login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        messages.success(request, 'Password changed successfully.')

    return render(request, 'adminpanel/settings.html')