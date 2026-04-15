from django.contrib import admin
from .models import Wallet, WalletTransaction


class WalletTransactionInline(admin.TabularInline):
    model   = WalletTransaction
    extra   = 0
    readonly_fields = ('txn_type', 'amount', 'description', 'order', 'created_at')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display  = ('user', 'balance', 'updated_at')
    search_fields = ('user__email', 'user__first_name')
    readonly_fields = ('updated_at',)
    inlines       = [WalletTransactionInline]


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display  = ('wallet', 'txn_type', 'amount', 'description', 'order', 'created_at')
    list_filter   = ('txn_type',)
    search_fields = ('wallet__user__email', 'description')
    readonly_fields = ('created_at',)