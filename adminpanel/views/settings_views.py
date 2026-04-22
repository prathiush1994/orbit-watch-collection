from django.shortcuts import render
from django.contrib import messages, auth
from .decorators import admin_required


@admin_required
def settings(request):
    if request.method == "POST":
        current_password = request.POST.get("current_password", "")
        new_password = request.POST.get("new_password", "")
        confirm_password = request.POST.get("confirm_password", "")
        user = request.user

        if not user.check_password(current_password):
            messages.error(request, "Current password is incorrect.")
            return render(request, "adminpanel/settings.html")

        if new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
            return render(request, "adminpanel/settings.html")

        if len(new_password) < 8:
            messages.error(request, "Password must be at least 8 characters.")
            return render(request, "adminpanel/settings.html")

        user.set_password(new_password)
        user.save()
        auth.login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, "Password changed successfully.")

    return render(request, "adminpanel/settings.html")
