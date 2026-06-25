from django.db import models
from accounts.models import Account

from django.utils import timezone
from decimal import Decimal


class Coupon(models.Model):
    DISCOUNT_TYPE_CHOICES = (
        ("percentage", "Percentage"),
        ("fixed", "Fixed Amount"),
    )
    code = models.CharField(max_length=20, unique=True, db_index=True)
    discount_type = models.CharField(
        max_length=10, choices=DISCOUNT_TYPE_CHOICES, default="percentage"
    )
    discount = models.DecimalField(max_digits=6, decimal_places=2)
    min_order_amt = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
    )
    max_discount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
    )
    usage_limit = models.PositiveIntegerField(default=1)
    total_usage = models.PositiveIntegerField(default=0)
    max_total_usage = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.code} ({self.discount_type})"

    def is_valid(self):
        now = timezone.now()
        if not self.is_active:
            return False, "Coupon is inactive."
        if now < self.valid_from:
            return False, "Coupon is not yet active."
        if self.valid_until and now > self.valid_until:
            return False, "Coupon has expired."
        if self.max_total_usage and self.total_usage >= self.max_total_usage:
            return False, "Coupon usage limit reached."
        return True, "Valid"

    def calculate_discount(self, subtotal):
        subtotal = Decimal(str(subtotal))
        if self.discount_type == "percentage":
            amount = (self.discount / 100) * subtotal
            if self.max_discount:
                amount = min(amount, self.max_discount)
        else:
            amount = self.discount
        return min(amount, subtotal) 


class CouponUsage(models.Model):
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name="usages")
    user = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="coupon_usages"
    )
    used_count = models.PositiveIntegerField(default=0)
    last_used = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ("coupon", "user")

    def __str__(self):
        return f"{self.user} used {self.coupon.code} × {self.used_count}"

