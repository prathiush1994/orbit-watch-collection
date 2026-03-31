from django.db import models
from accounts.models import Account, UserAddress
from store.models import ProductVariant


class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = (
        ('COD',      'Cash on Delivery'),
        ('RAZORPAY', 'Razorpay'),          # ready for future
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
    transaction_id = models.CharField(max_length=100, blank=True)  # filled by Razorpay later
    created_at     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.payment_method} — {self.status} — ₹{self.amount_paid}"


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

    user           = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True)
    payment        = models.ForeignKey(Payment, on_delete=models.SET_NULL, blank=True, null=True)

    # Snapshot of address at time of order (address can be edited later)
    full_name      = models.CharField(max_length=100)
    phone          = models.CharField(max_length=20)
    address_line   = models.TextField(max_length=300)
    city           = models.CharField(max_length=100)
    state          = models.CharField(max_length=100)
    pincode        = models.CharField(max_length=10)
    address_type   = models.CharField(max_length=10, default='Home')

    order_number   = models.CharField(max_length=20, unique=True)
    order_total    = models.DecimalField(max_digits=10, decimal_places=2)
    tax            = models.DecimalField(max_digits=10, decimal_places=2)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='New')
    is_ordered     = models.BooleanField(default=False)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.order_number} — {self.user}"


class OrderProduct(models.Model):
    order   = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    user    = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True)

    # Snapshot prices — so price changes don't affect past orders
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