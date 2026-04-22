from django.contrib import admin
from .models import Wishlist, WishlistItem


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "wishlist_id", "created_at")
    ordering = ("-created_at",)


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ("id", "wishlist", "variant", "added_at")
    ordering = ("-added_at",)
    list_filter = ("added_at",)
