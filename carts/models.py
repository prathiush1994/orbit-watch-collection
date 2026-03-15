from django.db import models
from store.models import ProductVariant


class Cart(models.Model):
    cart_id    = models.CharField(max_length=100, blank=True)
    date_added = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.cart_id


class CartItem(models.Model):
    """
    Cart stores the ProductVariant — not the base Product.
    This means 'Titan Celestor – Red' and 'Titan Celestor – Blue'
    are treated as completely separate cart items with independent stock.
    """
    variant   = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    cart      = models.ForeignKey(Cart, on_delete=models.CASCADE)
    quantity  = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return str(self.variant)

    def sub_total(self):
        return self.variant.price * self.quantity