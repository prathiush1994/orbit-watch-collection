from django.db import models
from django.utils import timezone
from decimal import Decimal


class ProductOffer(models.Model):
    product = models.ForeignKey(
        "store.Product",
        on_delete=models.CASCADE,
        related_name="offers"
    )
    discount_pct = models.DecimalField(
        max_digits=5, decimal_places=2,
        help_text="Percentage discount e.g. 15 for 15%"
    )
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.product_name} — {self.discount_pct}% off"

    def is_valid(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        return True

    def apply_to_price(self, price):
        price = Decimal(str(price))
        return round(price - (price * self.discount_pct / 100), 2)


class CategoryOffer(models.Model):
    category = models.ForeignKey(
        "category.Category",
        on_delete=models.CASCADE,
        related_name="offers"
    )
    discount_pct = models.DecimalField(
        max_digits=5, decimal_places=2,
        help_text="Percentage discount e.g. 10 for 10%"
    )
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.category.category_name} — {self.discount_pct}% off"

    def is_valid(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        return True

    def apply_to_price(self, price):
        price = Decimal(str(price))
        return round(price - (price * self.discount_pct / 100), 2)
