import shortuuid
from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL



# -------------------------------
# Shipping Address
# -------------------------------
class ShippingAddress(models.Model):
    """
    Optional separate shipping address, can be used for saving multiple addresses per user.
    Not strictly required by Order since Order stores snapshots.
    """
    id = models.CharField(
        primary_key=True,
        max_length=22,
        default=shortuuid.uuid,
        editable=False,
        unique=True,
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE,null=True,blank=True)
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20)
    address = models.CharField(max_length=255)
    address2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=50, default="US")

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
    Stores shipping details, tracking info, and status for each Order.
    Pulls snapshot data from Order at creation to maintain historical record.
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

    # Link to Order
    order = models.OneToOneField(
        "orders.Order", 
        on_delete=models.CASCADE,
        related_name="order_shipment"
    )

    # Snapshot shipping info (from Order)
    shipping_full_name = models.CharField(max_length=150, null=True, blank=True)
    shipping_phone = models.CharField(max_length=20, null=True, blank=True)
    shipping_address_text = models.CharField(max_length=255, null=True, blank=True)
    shipping_city = models.CharField(max_length=100, null=True, blank=True)
    shipping_state = models.CharField(max_length=100, null=True, blank=True)
    shipping_country = models.CharField(max_length=50, default="US", null=True, blank=True)
    shipping_postal_code = models.CharField(max_length=20, null=True, blank=True)

    shipping_method = models.CharField(
        max_length=20,
        choices=SHIPPING_METHOD_CHOICES,
        default="standard"
    )
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )
    tracking_number = models.CharField(max_length=50, blank=True, null=True)
    estimated_delivery_date = models.DateField(blank=True, null=True)
    courier_name = models.CharField(max_length=50, default="Shippo")
    label_created = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Shipment"
        verbose_name_plural = "Shipments"

    def __str__(self):
        return f"{self.order.id} - {self.delivery_status}"
