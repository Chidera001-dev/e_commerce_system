from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Shipment


@receiver(post_save, sender=Shipment)
def sync_order_on_delivery(sender, instance, **kwargs):
    """
    If admin updates shipment delivery_status to DELIVERED,
    automatically update the related Order.
    """

    if instance.delivery_status == "delivered":
        order = instance.order

        # Avoid unnecessary updates
        if order.status != "delivered":
            order.status = "delivered"
            order.shipping_status = "delivered"
            order.save(update_fields=["status", "shipping_status"])
