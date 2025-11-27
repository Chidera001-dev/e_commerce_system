import shortuuid
from django.conf import settings
from django.db import models

from carts.models import Cart
from product.models import Product

User = settings.AUTH_USER_MODEL


class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("processing", "Processing"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    PAYMENT_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ]

    # Primary ID
    id = models.CharField(
        primary_key=True,
        max_length=22,
        default=shortuuid.uuid,
        editable=False,
        unique=True,
    )

    # User & Cart
    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="orders",
    )
    cart = models.OneToOneField(
        Cart,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="order",
    )

    # Payment
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        db_index=True,
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default="pending",
        db_index=True,
    )
    reference = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Internal order reference (for Paystack/Rave)",
        db_index=True,
    )
    transaction_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        unique=True,
        help_text="Transaction reference from payment gateway",
    )
    payment_method = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="E.g. paystack, flutterwave, bank_transfer",
    )

    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Order total including product cost + shipping",
    )

    # Shipping Info
    shipping_full_name = models.CharField(max_length=100, null=True, blank=True)
    shipping_phone = models.CharField(max_length=20, null=True, blank=True)
    shipping_address = models.TextField(null=True, blank=True)
    shipping_city = models.CharField(max_length=100, null=True, blank=True)
    shipping_state = models.CharField(max_length=100, null=True, blank=True)
    shipping_country = models.CharField(
        max_length=100, default="Nigeria", null=True, blank=True
    )
    shipping_postal_code = models.CharField(max_length=20, null=True, blank=True)

    # Provider fields
    shipping_provider = models.CharField(max_length=100, null=True, blank=True)
    shipping_tracking_number = models.CharField(
        max_length=100, null=True, blank=True, db_index=True
    )
    shipping_label_url = models.URLField(null=True, blank=True)
    shipping_status = models.CharField(
        max_length=50, null=True, blank=True, db_index=True
    )
    shipping_cost = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order {self.id}"

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["payment_status"]),
            models.Index(fields=["shipping_status"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["reference"]),
        ]


class OrderItem(models.Model):
    id = models.CharField(
        primary_key=True,
        max_length=22,
        default=shortuuid.uuid,
        editable=False,
        unique=True,
    )
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, related_name="order_items"
    )
    quantity = models.PositiveIntegerField(default=1)
    price_snapshot = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Price of product when order was created",
    )

    @property
    def subtotal(self):
        return (self.price_snapshot or 0) * (self.quantity or 0)

    def __str__(self):
        return f"{self.product} × {self.quantity}"

    class Meta:
        ordering = ["-id"]
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"


# Create your models here.
