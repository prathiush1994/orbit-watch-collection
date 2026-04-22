from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Inventory(models.Model):

    variant = models.OneToOneField(
        "store.ProductVariant", on_delete=models.CASCADE, related_name="inventory"
    )
    quantity = models.IntegerField(default=0)
    low_stock_threshold = models.IntegerField(
        default=5, help_text="Alert when stock falls at or below this number"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Inventory"
        verbose_name_plural = "Inventories"
        ordering = ["variant__product__product_name", "variant__color_name"]

    def __str__(self):
        return f"{self.variant} — qty: {self.quantity}"

    @property
    def is_low_stock(self):
        return 0 < self.quantity <= self.low_stock_threshold

    @property
    def is_out_of_stock(self):
        return self.quantity <= 0

    def add_stock(self, qty, reason, updated_by=None, note=""):
        if qty <= 0:
            raise ValueError("Quantity to add must be positive.")
        if reason in ["damage", "order"]:
            # behave like deduct
            self.quantity = max(0, self.quantity - qty)
            change_type = InventoryLog.DEDUCT

        else:
            # default → add
            self.quantity += qty
            change_type = InventoryLog.ADD

        self.save(update_fields=["quantity", "updated_at"])
        InventoryLog.objects.create(
            inventory=self,
            change_type=InventoryLog.ADD,
            quantity_changed=qty,
            quantity_after=self.quantity,
            reason=reason,
            note=note,
            updated_by=updated_by,
        )

    def deduct_stock(self, qty, reason, updated_by=None, note=""):

        if qty <= 0:
            raise ValueError("Quantity to deduct must be positive.")
        self.quantity = max(0, self.quantity - qty)
        self.save(update_fields=["quantity", "updated_at"])
        InventoryLog.objects.create(
            inventory=self,
            change_type=change_type,
            quantity_changed=qty,
            quantity_after=self.quantity,
            reason=reason,
            note=note,
            updated_by=updated_by,
        )


class InventoryLog(models.Model):
    ADD = "add"
    DEDUCT = "deduct"
    ADJUSTMENT = "adjustment"

    CHANGE_TYPE_CHOICES = [
        (ADD, "Stock Added"),
        (DEDUCT, "Stock Deducted"),
        (ADJUSTMENT, "Manual Adjustment"),
    ]

    REASON_CHOICES = [
        ("restock", "Restock / New Delivery"),
        ("order", "Order Placed"),
        ("order_cancel", "Order Cancelled / Returned"),
        ("correction", "Stock Correction"),
        ("damage", "Damaged / Lost"),
        ("other", "Other"),
    ]

    inventory = models.ForeignKey(
        Inventory, on_delete=models.CASCADE, related_name="logs"
    )
    change_type = models.CharField(max_length=20, choices=CHANGE_TYPE_CHOICES)
    quantity_changed = models.IntegerField(
        help_text="Units added or removed (always positive)"
    )
    quantity_after = models.IntegerField(help_text="Stock level after this change")
    reason = models.CharField(max_length=50, choices=REASON_CHOICES)
    note = models.TextField(blank=True, help_text="Optional extra detail")
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_logs",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Inventory Log"
        verbose_name_plural = "Inventory Logs"
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.inventory.variant} | {self.get_change_type_display()} "
            f"{self.quantity_changed} → {self.quantity_after}"
        )
