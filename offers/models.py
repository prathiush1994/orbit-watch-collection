from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
import uuid


# ─────────────────────────────────────────────────────────
# PRODUCT OFFER
# ─────────────────────────────────────────────────────────
class ProductOffer(models.Model):
    """Discount applied to a specific product (all its variants)."""
    product     = models.OneToOneField(
        'store.Product', on_delete=models.CASCADE, related_name='offer'
    )
    discount_pct = models.DecimalField(
        max_digits=5, decimal_places=2,
        help_text='Percentage discount e.g. 15 for 15%'
    )
    is_active   = models.BooleanField(default=True)
    valid_from  = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.product_name} — {self.discount_pct}% off"

    def is_valid(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        return True

    def apply_to_price(self, price):
        """Returns discounted price."""
        price = Decimal(str(price))
        return round(price - (price * self.discount_pct / 100), 2)


# ─────────────────────────────────────────────────────────
# CATEGORY OFFER
# ─────────────────────────────────────────────────────────
class CategoryOffer(models.Model):
    """Discount applied to all products in a category."""
    category    = models.OneToOneField(
        'category.Category', on_delete=models.CASCADE, related_name='offer'
    )
    discount_pct = models.DecimalField(
        max_digits=5, decimal_places=2,
        help_text='Percentage discount e.g. 10 for 10%'
    )
    is_active   = models.BooleanField(default=True)
    valid_from  = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.category.category_name} — {self.discount_pct}% off"

    def is_valid(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        return True

    def apply_to_price(self, price):
        price = Decimal(str(price))
        return round(price - (price * self.discount_pct / 100), 2)


# ─────────────────────────────────────────────────────────
# REFERRAL OFFER
# ─────────────────────────────────────────────────────────
class ReferralCode(models.Model):
    """
    Each user gets one referral code.
    When a new user registers using this code:
      - Referee (new user) gets referee_discount on first order
      - Referrer (code owner) gets referrer_reward credited to wallet
    """
    user             = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='referral_code'
    )
    code             = models.CharField(max_length=20, unique=True, db_index=True)
    token            = models.UUIDField(default=uuid.uuid4, unique=True,
                                        help_text='Token-based referral URL: /register/?ref=<token>')
    referee_discount = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('100.00'),
        help_text='₹ discount new user gets on first order'
    )
    referrer_reward  = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('50.00'),
        help_text='₹ wallet credit given to referrer when referee places first order'
    )
    times_used       = models.PositiveIntegerField(default=0)
    is_active        = models.BooleanField(default=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} — code: {self.code}"

    def get_referral_url(self, request=None):
        path = f"/accounts/register/?ref={self.token}"
        if request:
            return request.build_absolute_uri(path)
        return path


class ReferralUse(models.Model):
    """Records each time a referral code was used."""
    referral_code = models.ForeignKey(
        ReferralCode, on_delete=models.CASCADE, related_name='uses'
    )
    referee       = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='used_referral'
    )
    reward_given  = models.BooleanField(default=False,
                                        help_text='True after referee places first order')
    used_at       = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.referee.email} used {self.referral_code.code}"