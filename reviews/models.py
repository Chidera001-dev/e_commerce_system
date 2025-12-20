from django.db import models
from django.db import models
from django.conf import settings
from product.models import Product
import shortuuid
from orders.models import Order

class Review(models.Model):
    RATING_CHOICES = [(i, i) for i in range(1, 6)]

    id = models.CharField(
        primary_key=True,
        max_length=22,
        default=shortuuid.uuid,
        editable=False,
        unique=True,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="reviews",   
    )

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="reviews",
    )

    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)


    class Meta:
        unique_together = ("user", "product", "order")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product.name} - {self.rating}⭐"


# Create your models here.
