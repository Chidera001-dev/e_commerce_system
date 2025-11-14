from django.db import models
import shortuuid
from django.conf import settings
from product.models import Product

User = settings.AUTH_USER_MODEL

class Cart(models.Model):
    id = models.CharField(
        primary_key=True,
        max_length=22,
        default=shortuuid.uuid,
        editable=False,
        unique=True,
    )
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart({self.user.username})" if self.user else f"Cart({self.id})"

    @property
    def total(self):
        return sum([item.subtotal for item in self.items.all()])


class CartItem(models.Model):
    id = models.CharField(
        primary_key=True,
        max_length=22,
        default=shortuuid.uuid,
        editable=False,
        unique=True,
    )
    cart = models.ForeignKey(Cart, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price_snapshot = models.DecimalField(max_digits=10, decimal_places=2)
    added_at = models.DateTimeField(auto_now_add=True)

    @property
    def subtotal(self):
        return self.price_snapshot * self.quantity

    class Meta:
        unique_together = ("cart", "product")
        ordering = ['-added_at']


# Create your models here.
