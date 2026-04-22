from django.db import models
from django.urls import reverse


class Category(models.Model):
    category_name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    cat_image = models.ImageField(upload_to="photos/categories", blank=True)
    status = models.CharField(max_length=20, default="active")  # active / inactive

    is_offer_applicable = models.BooleanField(
        default=True,
        help_text="Uncheck for Men / Women / Kids — allow only for product-type categories.",
    )

    def __str__(self):
        return self.category_name

    class Meta:
        verbose_name = "category"
        verbose_name_plural = "categories"

    def get_url(self):
        return reverse("products_by_category", args=[self.slug])
