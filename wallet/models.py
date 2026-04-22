from django.db import models
from django.conf import settings
from decimal import Decimal


class Wallet(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallet"
    )
    balance = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} — ₹{self.balance}"

    # ── business methods ─────────────────────────────────
    def credit(self, amount, description="", order=None):
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError("Credit amount must be positive.")
        self.balance += amount
        self.save(update_fields=["balance", "updated_at"])
        WalletTransaction.objects.create(
            wallet=self,
            amount=amount,
            txn_type="credit",
            description=description,
            order=order,
        )

    def debit(self, amount, description="", order=None):
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError("Debit amount must be positive.")
        if self.balance < amount:
            raise ValueError("Insufficient wallet balance.")
        self.balance -= amount
        self.save(update_fields=["balance", "updated_at"])
        WalletTransaction.objects.create(
            wallet=self,
            amount=amount,
            txn_type="debit",
            description=description,
            order=order,
        )


class WalletTransaction(models.Model):
    TYPE_CHOICES = (
        ("credit", "Credit"),
        ("debit", "Debit"),
    )
    wallet = models.ForeignKey(
        Wallet, on_delete=models.CASCADE, related_name="transactions"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    txn_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    description = models.CharField(max_length=255, blank=True)
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="wallet_transactions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.txn_type.upper()} ₹{self.amount} — {self.description}"
