import nested_admin
from django.contrib import admin
from store.models import Product, ProductVariant, VariantImage


class VariantImageInline(nested_admin.NestedTabularInline):
    """Gallery images — nested inside the variant inline."""

    model = VariantImage
    extra = 3
    fields = ("image", "alt_text", "order")


class ProductVariantInline(nested_admin.NestedStackedInline):
    """
    Variants — shown inside the Product admin page.
    Each variant has VariantImageInline nested inside it.
    One page, one save — no separate steps needed.
    """

    model = ProductVariant
    extra = 1
    fields = (
        "color_name",
        "color_code",
        "slug",
        "price",
        "stock",
        "primary_image",
        "description_override",
        "is_available",
    )
    prepopulated_fields = {"slug": ("color_name",)}
    inlines = [VariantImageInline]


@admin.register(Product)
class ProductAdmin(nested_admin.NestedModelAdmin):
    list_display = ("product_name", "brand", "variant_count", "created_at")
    list_filter = ("category", "brand")
    search_fields = ("product_name",)
    prepopulated_fields = {"slug": ("product_name",)}
    filter_horizontal = ("category",)
    inlines = [ProductVariantInline]

    def variant_count(self, obj):
        return obj.variants.count()

    variant_count.short_description = "Variants"


@admin.register(ProductVariant)
class ProductVariantAdmin(nested_admin.NestedModelAdmin):
    list_display = ("__str__", "price", "stock", "is_available", "in_stock")
    list_filter = ("is_available", "product")
    search_fields = ("product__product_name", "color_name", "slug")
    prepopulated_fields = {"slug": ("color_name",)}
    inlines = [VariantImageInline]

    def in_stock(self, obj):
        return obj.is_in_stock()

    in_stock.boolean = True
    in_stock.short_description = "In Stock"


@admin.register(VariantImage)
class VariantImageAdmin(admin.ModelAdmin):
    list_display = ("variant", "alt_text", "order")
    ordering = ("variant", "order")
