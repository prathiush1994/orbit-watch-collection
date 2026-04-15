from django.db import models
from accounts.models import Account, UserAddress
from store.models import ProductVariant
from django.utils import timezone
from decimal import Decimal


# ─────────────────────────────────────────────────────────
# COUPON
# ─────────────────────────────────────────────────────────
class Coupon(models.Model):
    DISCOUNT_TYPE_CHOICES = (
        ('percentage', 'Percentage'),
        ('fixed',      'Fixed Amount'),
    )
    code            = models.CharField(max_length=20, unique=True, db_index=True)
    discount_type   = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, default='percentage')
    discount        = models.DecimalField(max_digits=6, decimal_places=2,
                                          help_text='Value: % or fixed ₹ amount')
    min_order_amt   = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                          help_text='Minimum cart value to apply coupon')
    max_discount    = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                          help_text='Max cap for percentage coupons')
    usage_limit     = models.PositiveIntegerField(default=1,
                                                   help_text='Max times ONE user can use this')
    total_usage     = models.PositiveIntegerField(default=0,
                                                   help_text='Total uses across all users (auto)')
    max_total_usage = models.PositiveIntegerField(null=True, blank=True,
                                                   help_text='Overall limit (blank = unlimited)')
    is_active       = models.BooleanField(default=True)
    valid_from      = models.DateTimeField(default=timezone.now)
    valid_until     = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.code} ({self.discount_type})"

    def is_valid(self):
        """Returns (bool, message)."""
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
        """Returns exact ₹ discount to subtract from subtotal."""
        subtotal = Decimal(str(subtotal))
        if self.discount_type == 'percentage':
            amount = (self.discount / 100) * subtotal
            if self.max_discount:
                amount = min(amount, self.max_discount)
        else:
            amount = self.discount
        return min(amount, subtotal)   # discount can never exceed bill


class CouponUsage(models.Model):
    """Tracks per-user usage count for each coupon."""
    coupon     = models.ForeignKey(Coupon,  on_delete=models.CASCADE, related_name='usages')
    user       = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='coupon_usages')
    used_count = models.PositiveIntegerField(default=0)
    last_used  = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('coupon', 'user')

    def __str__(self):
        return f"{self.user} used {self.coupon.code} × {self.used_count}"


# ─────────────────────────────────────────────────────────
# PAYMENT
# ─────────────────────────────────────────────────────────
class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = (
        ('COD',      'Cash on Delivery'),
        ('RAZORPAY', 'Razorpay'),
        ('WALLET',   'Wallet'),        # fully paid by wallet
    )
    STATUS_CHOICES = (
        ('Pending',   'Pending'),
        ('Completed', 'Completed'),
        ('Failed',    'Failed'),
        ('Refunded',  'Refunded'),
    )
    user           = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    amount_paid    = models.CharField(max_length=100)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    transaction_id = models.CharField(max_length=100, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.payment_method} — {self.status} — ₹{self.amount_paid}"


# ─────────────────────────────────────────────────────────
# ORDER
# ─────────────────────────────────────────────────────────
class Order(models.Model):
    STATUS_CHOICES = (
        ('New',              'New'),
        ('Accepted',         'Accepted'),
        ('Shipped',          'Shipped'),
        ('Delivered',        'Delivered'),
        ('Cancelled',        'Cancelled'),
        ('Return Requested', 'Return Requested'),
        ('Returned',         'Returned'),
    )

    user    = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True)
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, blank=True, null=True)
    coupon  = models.ForeignKey(Coupon,  on_delete=models.SET_NULL, null=True, blank=True)

    # ── Delivery address snapshot ─────────────────────────
    full_name    = models.CharField(max_length=100)
    phone        = models.CharField(max_length=20)
    address_line = models.TextField(max_length=300)
    city         = models.CharField(max_length=100)
    state        = models.CharField(max_length=100)
    pincode      = models.CharField(max_length=10)
    address_type = models.CharField(max_length=10, default='Home')

    # ── Financials ────────────────────────────────────────
    order_number = models.CharField(max_length=20, unique=True)
    order_total  = models.DecimalField(max_digits=10, decimal_places=2,
                                       help_text='Final amount actually charged')
    tax          = models.DecimalField(max_digits=10, decimal_places=2)
    discount     = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                       help_text='Coupon discount applied')
    coupon_code  = models.CharField(max_length=20, blank=True,
                                    help_text='Snapshot of coupon code used')
    wallet_used  = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                       help_text='Amount paid from wallet balance')

    # ── Status ────────────────────────────────────────────
    status     = models.CharField(max_length=20, choices=STATUS_CHOICES, default='New')
    is_ordered = models.BooleanField(default=False)

    # ── Cancel / Return ───────────────────────────────────
    cancel_reason = models.CharField(max_length=255, blank=True)
    return_reason = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.order_number} — {self.user}"


# ─────────────────────────────────────────────────────────
# ORDER PRODUCT
# ─────────────────────────────────────────────────────────
class OrderProduct(models.Model):
    order         = models.ForeignKey(Order,          on_delete=models.CASCADE,   related_name='items')
    user          = models.ForeignKey(Account,        on_delete=models.SET_NULL,  null=True)
    variant       = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL,  null=True)
    product_name  = models.CharField(max_length=250)
    color_name    = models.CharField(max_length=100)
    product_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity      = models.IntegerField()
    ordered       = models.BooleanField(default=False)
    created_at    = models.DateTimeField(auto_now_add=True)

    def sub_total(self):
        return self.product_price * self.quantity

    def __str__(self):
        return f"{self.product_name} ({self.color_name}) × {self.quantity}"