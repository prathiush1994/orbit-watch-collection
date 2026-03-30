from django.contrib import admin
from .models import Wishlist


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display  = ('user', 'variant', 'added_at')
    list_filter   = ('added_at',)
    search_fields = ('user__email', 'variant__product__product_name')
    ordering      = ('-added_at',)