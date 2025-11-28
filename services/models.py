import shortuuid
from django.db import models
from orders.models import Order

# -------------------------------
# Shipping Address
# -------------------------------
class ShippingAddress(models.Model):
    """
    Stores delivery address for an order.
    One-to-one relationship with Order.
    """
    id = models.CharField(
        primary_key=True,
        max_length=22,
        default=shortuuid.uuid,
        editable=False,
        unique=True,
    )
    order = models.OneToOneField(
        Order, on_delete=models.CASCADE, related_name="order_shippingaddress"
    )
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20)
    address = models.CharField(max_length=255)
    address2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=50, default="Nigeria")  # default for now

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Shipping Address"
        verbose_name_plural = "Shipping Addresses"

    def __str__(self):
        return f"{self.full_name} - {self.city}"


# -------------------------------
# Shipment
# -------------------------------
class Shipment(models.Model):
    """
    Stores shipping details, tracking info, and status for Shippo integration.
    Each order has one shipment.
    """
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("dispatched", "Dispatched"),
        ("in_transit", "In Transit"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
    ]

    SHIPPING_METHOD_CHOICES = [
        ("standard", "Standard"),
        ("express", "Express"),
    ]

    id = models.CharField(
        primary_key=True,
        max_length=22,
        default=shortuuid.uuid,
        editable=False,
        unique=True,
    )
    order = models.OneToOneField(
        Order, 
         on_delete=models.CASCADE,
         related_name="order_shipment" 
    )
    shipping_address = models.OneToOneField(
        ShippingAddress, on_delete=models.SET_NULL, null=True, blank=True
    )
    shipping_method = models.CharField(
        max_length=20, choices=SHIPPING_METHOD_CHOICES, default="standard"
    )
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending"
    )
    tracking_number = models.CharField(max_length=50, blank=True, null=True)
    estimated_delivery_date = models.DateField(blank=True, null=True)
    courier_name = models.CharField(max_length=50, default="Shippo")  # Only Shippo
    label_created = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Shipment"
        verbose_name_plural = "Shipments"

    def __str__(self):
        return f"{self.order.id} - {self.delivery_status}"

