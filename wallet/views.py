import json
from decimal import Decimal
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Wallet


def get_or_create_wallet(user):
    wallet, _ = Wallet.objects.get_or_create(user=user)
    return wallet


@login_required(login_url="login")
def wallet_dashboard(request):
    wallet = get_or_create_wallet(request.user)
    transactions = wallet.transactions.select_related("order").all()[:50]
    return render(
        request,
        "dashboard/wallet.html",
        {
            "wallet": wallet,
            "transactions": transactions,
        },
    )


@login_required(login_url="login")
def apply_wallet(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid request."})

    data = json.loads(request.body)
    final_total = Decimal(str(data.get("final_total", "0")))
    wallet = get_or_create_wallet(request.user)

    if wallet.balance <= 0:
        return JsonResponse({"success": False, "message": "Your wallet balance is ₹0."})

    if final_total <= 0:
        return JsonResponse({"success": False, "message": "Nothing left to pay."})

    # Use as much wallet as needed (can't exceed bill or balance)
    wallet_used = min(wallet.balance, final_total)
    amount_to_pay = round(final_total - wallet_used, 2)

    # Save in session
    request.session["wallet_used"] = str(wallet_used)
    request.session["wallet_applied"] = True

    return JsonResponse(
        {
            "success": True,
            "wallet_used": str(wallet_used),
            "amount_to_pay": str(amount_to_pay),
            "message": f"₹{wallet_used} will be deducted from your wallet.",
        }
    )


@login_required(login_url="login")
def remove_wallet(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid request."})

    data = json.loads(request.body)
    final_total = Decimal(str(data.get("final_total", "0")))

    request.session.pop("wallet_used", None)
    request.session.pop("wallet_applied", None)

    return JsonResponse(
        {
            "success": True,
            "message": "Wallet removed.",
            "amount_to_pay": str(final_total),
        }
    )
