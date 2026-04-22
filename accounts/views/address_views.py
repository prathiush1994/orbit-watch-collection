from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import UserAddress


@login_required(login_url="login")
def add_address(request):
    next_page = request.GET.get("next", "manage_address")

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        address_line = request.POST.get("address_line", "").strip()
        city = request.POST.get("city", "").strip()
        state = request.POST.get("state", "").strip()
        pincode = request.POST.get("pincode", "").strip()
        address_type = request.POST.get("address_type", "Home")
        is_default = request.POST.get("is_default") == "on"
        next_page = request.POST.get("next", "manage_address")

        # Basic validation
        if not all([full_name, phone, address_line, city, state, pincode]):
            messages.error(request, "Please fill in all required fields.")
            return render(
                request,
                "accounts/add_address.html",
                {
                    "next": next_page,
                    "form_data": request.POST,
                },
            )

        UserAddress.objects.create(
            user=request.user,
            full_name=full_name,
            phone=phone,
            address_line=address_line,
            city=city,
            state=state,
            pincode=pincode,
            address_type=address_type,
            is_default=is_default,
        )

        messages.success(request, "Address added successfully!")

        if next_page == "checkout":
            return redirect("checkout")
        return redirect("manage_address")

    return render(request, "accounts/add_address.html", {"next": next_page})


@login_required(login_url="login")
def edit_address(request, address_id):
    """Edit an existing address."""
    address = get_object_or_404(UserAddress, id=address_id, user=request.user)
    next_page = request.GET.get("next", "manage_address")

    if request.method == "POST":
        address.full_name = request.POST.get("full_name", "").strip()
        address.phone = request.POST.get("phone", "").strip()
        address.address_line = request.POST.get("address_line", "").strip()
        address.city = request.POST.get("city", "").strip()
        address.state = request.POST.get("state", "").strip()
        address.pincode = request.POST.get("pincode", "").strip()
        address.address_type = request.POST.get("address_type", "Home")
        address.is_default = request.POST.get("is_default") == "on"
        next_page = request.POST.get("next", "manage_address")

        if not all(
            [
                address.full_name,
                address.phone,
                address.address_line,
                address.city,
                address.state,
                address.pincode,
            ]
        ):
            messages.error(request, "Please fill in all required fields.")
            return render(
                request,
                "accounts/edit_address.html",
                {
                    "address": address,
                    "next": next_page,
                },
            )

        address.save()
        messages.success(request, "Address updated successfully!")

        if next_page == "checkout":
            return redirect("checkout")
        return redirect("manage_address")

    return render(
        request,
        "accounts/edit_address.html",
        {
            "address": address,
            "next": next_page,
        },
    )


@login_required(login_url="login")
def delete_address(request, address_id):
    """Delete an address (POST only)."""
    address = get_object_or_404(UserAddress, id=address_id, user=request.user)
    if request.method == "POST":
        address.delete()
        messages.success(request, "Address deleted.")
    return redirect("manage_address")


@login_required(login_url="login")
def set_default_address(request, address_id):
    """Set an address as default (POST only)."""
    address = get_object_or_404(UserAddress, id=address_id, user=request.user)
    if request.method == "POST":
        # Remove default from others
        UserAddress.objects.filter(user=request.user).update(is_default=False)
        address.is_default = True
        address.save()
        messages.success(request, "Default address updated.")
    return redirect("manage_address")


@login_required(login_url="login")
def manage_address(request):
    """Dashboard address management page."""
    addresses = UserAddress.objects.filter(user=request.user)
    return render(request, "dashboard/address.html", {"addresses": addresses})
