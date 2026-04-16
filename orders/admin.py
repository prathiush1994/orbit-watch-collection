from django.contrib import admin
from .models import Payment, Order, OrderProduct, Coupon, CouponUsage

# ───────────────────────── PAYMENT ─────────────────────────
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'payment_method',
        'amount_paid',
        'status',
        'created_at',
    )
    list_filter = ('payment_method', 'status', 'created_at')
    search_fields = ('user__email', 'transaction_id')
    ordering = ('-created_at',)


# ───────────────────────── ORDER PRODUCT (INLINE) ─────────────────────────
class OrderProductInline(admin.TabularInline):
    model = OrderProduct
    extra = 0
    readonly_fields = (
        'product_name',
        'color_name',
        'product_price',
        'quantity',
    )


# ───────────────────────── ORDER ─────────────────────────
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number',
        'user',
        'full_name',
        'phone',
        'order_total',
        'status',
        'is_ordered',
        'created_at',
    )
    list_filter = ('status', 'is_ordered', 'created_at')
    search_fields = ('order_number', 'user__email', 'full_name', 'phone')
    ordering = ('-created_at',)

    inlines = [OrderProductInline]

    readonly_fields = (
        'order_number',
        'user',
        'payment',
        'order_total',
        'tax',
    )


# ───────────────────────── ORDER PRODUCT ─────────────────────────
@admin.register(OrderProduct)
class OrderProductAdmin(admin.ModelAdmin):
    list_display = (
        'order',
        'user',
        'product_name',
        'color_name',
        'product_price',
        'quantity',
        'ordered',
        'created_at',
    )
    list_filter = ('ordered', 'created_at')
    search_fields = ('product_name', 'user__email', 'order__order_number')
    ordering = ('-created_at',)


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'discount_type',
        'discount',
        'min_order_amt',
        'usage_limit',
        'total_usage',
        'is_active',
        'valid_from',
        'valid_until',
    )
    list_filter = ('discount_type', 'is_active', 'valid_from', 'valid_until')
    search_fields = ('code',)
    ordering = ('-id',)


@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):
    list_display = (
        'coupon',
        'user',
        'used_count',
        'last_used',
    )
    search_fields = ('coupon__code', 'user__email')
