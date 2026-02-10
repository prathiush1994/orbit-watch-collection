from django.db import models
from category.models import Category
from brands.models import Brand
from django.urls import reverse

# Create your models here.
class Product(models.Model):
    product_name = models.CharField(max_length=250, unique=True)
    slug = models.SlugField(max_length=2500, unique=True)
    description = models.TextField(max_length=1500, unique=True)
    price = models.IntegerField()
    images = models.ImageField(upload_to = 'photos/products')
    stock = models.IntegerField()
    is_available = models.BooleanField(default=True)

    category = models.ManyToManyField(Category)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, null=True, blank=True)

    created_data = models.DateTimeField(auto_now_add=True)
    Modified_data = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.product_name
    
    def get_url(self):
        category = self.category.first()
        return reverse('product_detail', args = [category.slug, self.slug])