from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from accounts.models import UserAddress


@login_required(login_url="login")
def address(request):
    addresses = UserAddress.objects.filter(user=request.user)
    return render(request, "dashboard/address.html", {"addresses": addresses})