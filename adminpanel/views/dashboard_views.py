from django.shortcuts import render

from accounts.models import Account
from store.models import ProductVariant
from category.models import Category
from brands.models import Brand

from .decorators import admin_required


@admin_required
def dashboard(request):
    total_users = Account.objects.filter(is_admin=False, is_superadmin=False).count()
    active_users = Account.objects.filter(
        is_admin=False, is_superadmin=False, is_active=True
    ).count()
    blocked_users = Account.objects.filter(
        is_admin=False, is_superadmin=False, is_active=False
    ).count()

    total_products = ProductVariant.objects.count()
    active_products = ProductVariant.objects.filter(is_available=True).count()

    total_categories = Category.objects.count()
    total_brands = Brand.objects.count()

    recent_users = Account.objects.filter(is_admin=False, is_superadmin=False).order_by(
        "-date_joined"
    )[:5]

    context = {
        "total_users": total_users,
        "active_users": active_users,
        "blocked_users": blocked_users,
        "total_products": total_products,
        "active_products": active_products,
        "total_categories": total_categories,
        "total_brands": total_brands,
        "recent_users": recent_users,
    }
    return render(request, "adminpanel/dashboard.html", context)
