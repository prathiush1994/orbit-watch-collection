from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.decorators.http import require_POST
from accounts.models import Account
from .decorators import admin_required


@admin_required
def user_list(request):
    search_query = request.GET.get("q", "").strip()

    users = Account.objects.filter(is_admin=False, is_superadmin=False).order_by(
        "-date_joined"
    )

    if search_query:
        users = users.filter(
            Q(first_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
            | Q(email__icontains=search_query)
        )

    paginator = Paginator(users, 10)
    page = request.GET.get("page", 1)
    users = paginator.get_page(page)

    context = {
        "users": users,
        "search_query": search_query,
    }
    return render(request, "adminpanel/users.html", context)


@admin_required
@require_POST
def toggle_user_status(request, user_id):
    user = get_object_or_404(Account, id=user_id)

    if user.is_admin or user.is_superadmin:
        messages.error(request, "Cannot block admin users.")
        return redirect("admin_user_list")

    user.is_active = not user.is_active
    user.save()

    action = "unblocked" if user.is_active else "blocked"
    messages.success(request, f"{user.get_full_name()} has been {action}.")
    return redirect("admin_user_list")
