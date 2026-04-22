from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from store.models import ProductVariant

User = get_user_model()


class Review(models.Model):
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews")
    variant = models.ForeignKey(
        ProductVariant, on_delete=models.CASCADE, related_name="reviews"
    )
    rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(max_length=120, blank=True)
    body = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # One review per user per variant
        unique_together = ("user", "variant")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} — {self.variant} ({self.rating}★)"

    @property
    def stars_range(self):
        """Returns (filled, empty) counts for template rendering."""
        return range(self.rating), range(5 - self.rating)
