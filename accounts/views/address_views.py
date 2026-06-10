from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import UserAddress
from ..forms import AddressForm


@login_required(login_url="login")
def add_address(request):
    next_page = request.GET.get("next", "manage_address")

    if request.method == "POST":
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            messages.success(
                request, "Address added successfully!",
                extra_tags="add_address_message"
                )
            next_page = request.POST.get("next", "manage_address")
            if next_page == "checkout":
                return redirect("checkout")
            return redirect("manage_address")
        else:
            return render(
                request,
                "accounts/add_address.html",
                {
                    "form": form,
                    "next": next_page,
                }, 
                status=422,
            )
    else:
        form = AddressForm()

    return render(
        request,
        "accounts/add_address.html",
        {
            "form": form,
            "next": next_page,
        },)


@login_required(login_url="login")
def edit_address(request, address_id):
    address = get_object_or_404(
        UserAddress,
        id=address_id,
        user=request.user
    )

    next_page = request.GET.get("next", "manage_address")

    if request.method == "POST":
        form = AddressForm(request.POST, instance=address)
        next_page = request.POST.get("next", "manage_address")

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Address updated successfully!",
            )

            if next_page == "checkout":
                return redirect("checkout")
            return redirect("manage_address")

        return render(
            request,
            "accounts/edit_address.html",
            {
                "form": form,
                "address": address,
                "next": next_page,
            },
            status=422,
        )

    form = AddressForm(instance=address)

    return render(
        request,
        "accounts/edit_address.html",
        {
            "form": form,
            "address": address,
            "next": next_page,
        },
    )


@login_required(login_url="login")
def delete_address(request, address_id):
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
        UserAddress.objects.filter(user=request.user).update(is_default=False)
        address.is_default = True
        address.save()
        messages.success(request, "Default address updated.")
    return redirect("manage_address")


@login_required(login_url="login")
def manage_address(request):
    addresses = UserAddress.objects.filter(user=request.user)
    return render(request, "dashboard/address.html", {"addresses": addresses})
