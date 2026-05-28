import json
from decimal import Decimal
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Wallet
from orders.views.helpers import _compute_totals
from carts.views import _get_or_create_cart
from carts.models import CartItem


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
        return JsonResponse(
            {"success": False, "message": "Invalid request."}
        )

    wallet = get_or_create_wallet(request.user)

    cart = _get_or_create_cart(request)

    cart_items = CartItem.objects.filter(
        cart=cart,
        is_active=True
    ).select_related(
        "variant",
        "variant__product"
    )

    totals = _compute_totals(
        cart_items,
        request.session
    )

    final_total = totals["final_total"]

    print("final_total =", final_total)
    print("wallet_balance =", wallet.balance)

    if wallet.balance <= 0:
        return JsonResponse({
            "success": False,
            "message": "Your wallet balance is ₹0."
        })

    if final_total <= 0:
        return JsonResponse({
            "success": False,
            "message": "Nothing left to pay."
        })

    wallet_used = min(wallet.balance, final_total)

    amount_to_pay = round(
        final_total - wallet_used,
        2
    )

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
    print("remove_wallet final_total =", final_total)
    return JsonResponse(
        {
            "success": True,
            "message": "Wallet removed.",
            "amount_to_pay": str(final_total),
        }
    )
