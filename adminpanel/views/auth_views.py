from django.shortcuts import render, redirect
from django.contrib import messages, auth
from .decorators import admin_required


def admin_login(request):
    if request.user.is_authenticated:
        if request.user.is_superadmin or request.user.is_staff:
            return redirect("admin_dashboard")

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        user = auth.authenticate(email=email, password=password)

        if user is None:
            messages.error(request, "Invalid email or password.")
            return render(request, "adminpanel/login.html")

        if not (user.is_superadmin or user.is_staff):
            messages.error(request, "You do not have admin access.")
            return render(request, "adminpanel/login.html")

        auth.login(request, user)
        return redirect("admin_dashboard")

    return render(request, "adminpanel/login.html")


@admin_required
def admin_logout(request):
    auth.logout(request)
    return redirect("admin_login")
