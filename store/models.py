from django.db import models
from django.urls import reverse
from category.models import Category
from brands.models import Brand


class Product(models.Model):
    product_name = models.CharField(max_length=250, unique=True)
    slug = models.SlugField(max_length=250, unique=True)
    description = models.TextField(max_length=1500)
    category = models.ManyToManyField(Category)
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"

    def __str__(self):
        return self.product_name

    def get_variants(self):
        return self.variants.filter(is_available=True)


class ProductVariant(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="variants"
    )
    color_name = models.CharField(
        max_length=100, help_text="e.g. Red, Navy Blue, Black"
    )
    color_code = models.CharField(
        max_length=20, blank=True, help_text="Optional hex code e.g. #FF0000"
    )
    price = models.IntegerField(help_text="Price for this specific variant")

    is_available = models.BooleanField(default=True)
    slug = models.SlugField(
        max_length=250, unique=True, help_text="e.g. titan-celestor-red"
    )
    primary_image = models.ImageField(
        upload_to="photos/variants",
        null=True,
        blank=True,
        help_text="Front view image of this color variant",
    )

    description_override = models.TextField(
        max_length=1500,
        blank=True,
        help_text="Leave blank to use the base product description. "
        "Only fill this if this variant needs a different description.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Product Variant"
        verbose_name_plural = "Product Variants"
        unique_together = ("product", "color_name")

    def __str__(self):
        return f"{self.product.product_name} \u2013 {self.color_name}"

    def get_url(self):
        """URL for this variant's detail page."""
        category = self.product.category.first()
        if category:
            return reverse("product_detail", args=[category.slug, self.slug])
        return reverse("product_detail", args=["uncategorized", self.slug])

    def get_description(self):
        """
        Returns description_override if set,
        otherwise falls back to the base product description.
        """
        if self.description_override:
            return self.description_override
        return self.product.description

    def get_other_variants(self):
        """All OTHER variants of the same product (for color selector)."""
        return self.product.variants.filter(is_available=True).exclude(pk=self.pk)

    def get_all_variants(self):
        """ALL variants of the same product including self (for swatches)."""
        return self.product.variants.filter(is_available=True)
    
    @property
    def stock(self):
        return self.inventory.quantity if hasattr(self, "inventory") else 0

    @property
    def is_in_stock(self):
        return self.stock > 0


class VariantImage(models.Model):

    variant = models.ForeignKey(
        ProductVariant, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="photos/variant_gallery")
    alt_text = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(
        default=0, help_text="Lower number = shown first in the gallery"
    )

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Variant Image"
        verbose_name_plural = "Variant Images"

    def __str__(self):
        return f"{self.variant} | image {self.order}"
