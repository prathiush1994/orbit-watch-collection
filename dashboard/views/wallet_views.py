from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from wallet.models import Wallet


@login_required(login_url="login")
def dashboard_wallet(request):
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    transactions = wallet.transactions.select_related("order").all()[:50]
    total_credited = sum(
        t.amount for t in wallet.transactions.filter(txn_type="credit")
    )
    total_debited = sum(t.amount for t in wallet.transactions.filter(txn_type="debit"))

    context = {
        "wallet": wallet,
        "transactions": transactions,
        "total_credited": total_credited,
        "total_debited": total_debited,
    }
    return render(request, "dashboard/wallet.html", context)
