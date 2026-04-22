from django.shortcuts import redirect
from functools import wraps


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('admin_login')
        if request.user.is_superadmin or request.user.is_staff:
            return view_func(request, *args, **kwargs)
        return redirect('home')
    return wrapper