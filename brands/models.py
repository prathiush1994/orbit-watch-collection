from django.db import models

# Create your models here.
class Brand(models.Model):
    brand_name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    logo_image = models.ImageField(upload_to='photos/brands', blank = True)
    status = models.CharField(max_length=20, default='active')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.brand_name

    class Meta:
        verbose_name = 'brand'
        verbose_name_plural = 'brands'


