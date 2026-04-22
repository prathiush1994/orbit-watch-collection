from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Account, UserAddress


class AccountAdmin(UserAdmin):
    list_display = (
        "email",
        "first_name",
        "last_name",
        "is_active",
        "is_admin",
        "date_joined",
    )
    list_filter = ("is_active", "is_admin", "is_staff")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("-date_joined",)

    fieldsets = (
        ("Login Info", {"fields": ("email", "password")}),
        (
            "Personal",
            {"fields": ("first_name", "last_name", "phone_number", "profile_photo")},
        ),
        (
            "Permissions",
            {"fields": ("is_active", "is_admin", "is_staff", "is_superadmin")},
        ),
        ("OTP", {"fields": ("otp", "otp_created_at", "otp_purpose")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    filter_horizontal = ()
    list_filter = ()


@admin.register(UserAddress)
class UserAddressAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "full_name",
        "city",
        "state",
        "pincode",
        "address_type",
        "is_default",
        "created_at",
    )
    list_filter = ("address_type", "is_default", "state")
    search_fields = ("user__email", "full_name", "city", "pincode", "phone")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)

    fieldsets = (
        ("User", {"fields": ("user",)}),
        ("Contact", {"fields": ("full_name", "phone")}),
        (
            "Address",
            {"fields": ("address_line", "city", "state", "pincode", "address_type")},
        ),
        ("Default", {"fields": ("is_default",)}),
        ("Meta", {"fields": ("created_at",)}),
    )


admin.site.register(Account, AccountAdmin)
