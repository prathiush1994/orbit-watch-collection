from django.db import models
from accounts.models import Account
from store.models import ProductVariant
from coupons.models import Coupon


class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = (
        ("COD", "Cash on Delivery"),
        ("RAZORPAY", "Razorpay"),
        ("WALLET", "Wallet"),  
    )
    STATUS_CHOICES = (
        ("Pending", "Pending"),
        ("Completed", "Completed"),
        ("Failed", "Failed"),
        ("Refunded", "Refunded"),
    )
    user = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True)
    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_METHOD_CHOICES
    )
    amount_paid = models.CharField(max_length=100)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="Pending"
    )
    transaction_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.payment_method} — {self.status} — ₹{self.amount_paid}"


class Order(models.Model):
    STATUS_CHOICES = (
        ("Order Placed", "Order Placed"),
        ("Accepted", "Accepted"),
        ("Shipped", "Shipped"),
        ("Delivered", "Delivered"),
        ("Cancelled", "Cancelled"),
        ("Return Requested", "Return Requested"),
        ("Returned", "Returned"),
    )
    user = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True)
    payment = models.ForeignKey(
        Payment, on_delete=models.SET_NULL, blank=True, null=True
    )
    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    address_line = models.TextField(max_length=300)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    address_type = models.CharField(max_length=10, default="Home")
    order_number = models.CharField(max_length=20, unique=True)
    order_total = models.DecimalField(
        max_digits=10, decimal_places=2
    )
    tax = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    coupon_code = models.CharField(
        max_length=20, blank=True, help_text="Snapshot of coupon code used"
    )
    wallet_used = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Amount paid from wallet balance",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Order Placed"
    )
    is_ordered = models.BooleanField(default=False)
    cancel_reason = models.CharField(max_length=255, blank=True)
    return_reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.order_number} — {self.user}"

    def active_items(self):
        return self.items.exclude(
            item_status__in=["Cancelled", "Return Requested", "Returned"]
        )

    def all_items_cancelled(self):
        return not self.items.exclude(item_status="Cancelled").exists()

    def all_items_returned(self):
        return not self.items.exclude(
            item_status__in=["Returned", "Cancelled"]
        ).exists()


class OrderProduct(models.Model):

    ITEM_STATUS_CHOICES = (
        ("Active", "Active"),
        ("Cancelled", "Cancelled"),
        ("Return Requested", "Return Requested"),
        ("Returned", "Returned"),
    )
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    user = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True)

    product_name = models.CharField(max_length=250)
    color_name = models.CharField(max_length=100)
    product_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField()  

    item_status = models.CharField(
        max_length=20, choices=ITEM_STATUS_CHOICES, default="Active"
    )
    cancelled_qty = models.IntegerField(default=0)
    cancel_reason = models.CharField(max_length=255, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    returned_qty = models.IntegerField(default=0)
    return_reason = models.CharField(max_length=255, blank=True)
    return_requested_at = models.DateTimeField(null=True, blank=True)

    ordered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def active_qty(self):
        return self.quantity - self.cancelled_qty - self.returned_qty
    
    def sub_total(self):
        return self.product_price * self.active_qty()
    
    def removed_qty(self):
        return self.returned_qty + self.cancelled_qty

    def __str__(self):
        return f"{self.product_name} ({self.color_name}) × {self.quantity}"
