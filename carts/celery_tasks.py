import logging

from celery import shared_task
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import get_object_or_404

from carts.redis_cart import clear_cart
from orders.models import Order, OrderItem
from product.models import Product
from services.models import Shipment
from services.shipping_service import create_shipment  # Your Shippo helper

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_order_after_payment(self, order_id, user_email=None, user_id=None):
    """
    Process an order after payment:
    - Reduce stock
    - Clear Redis cart
    - Update order status & payment status
    - Create shipment via Shippo asynchronously
    - Send confirmation email with tracking info
    """
    try:
        order = get_object_or_404(Order, id=order_id)
        order_items = order.items.select_related("product").all()

        if not order_items.exists():
            logger.error(f"Order {order.id} has no items. Task stopped.")
            order.status = "pending_items"
            order.payment_status = "pending"
            order.save()
            return

        with transaction.atomic():
            # Reduce stock for each item
            for item in order_items:
                product = Product.objects.select_for_update().get(id=item.product.id)
                if product.stock < item.quantity:
                    raise ValueError(f"Insufficient stock for {product.name}")
                product.stock -= item.quantity
                product.save()

            # Clear Redis cart if user_id provided
            if user_id:
                clear_cart(f"user:{user_id}")

            # Update order payment and status
            order.payment_status = "paid"
            order.status = "processing"
            order.save()

        # -----------------------------
        # Async Shipment creation
        # -----------------------------
        try:
            shipment_info = create_shipment(order)

            # Create Shipment record in DB
            shipment = Shipment.objects.create(
                order=order,
                shipping_full_name=order.shipping_full_name,
                shipping_phone=order.shipping_phone,
                shipping_address_text=order.shipping_address_text,  
                shipping_city=order.shipping_city,
                shipping_state=order.shipping_state,
                shipping_country=order.shipping_country,
                shipping_postal_code=order.shipping_postal_code,
                shipping_fee=order.shipping_cost,
                delivery_status=shipment_info.get("status", "pending"),
                tracking_number=shipment_info.get("tracking_number"),
                courier_name=shipment_info.get("provider", "Shippo"),
        )


            # Update order shipping fields
            order.shipping_tracking_number = shipment.tracking_number
            order.shipping_status = shipment.delivery_status
            order.shipping_provider = shipment.courier_name
            order.save()

            logger.info(
                f"Shipment created for Order {order.id}: {shipment.tracking_number}"
            )
        except Exception as ship_exc:
            logger.error(f"Shipment creation failed for Order {order.id}: {ship_exc}")

        # -----------------------------
        # Send confirmation email
        # -----------------------------
        if user_email:
            items_list = "\n".join(
                [
                    f"{i.product.name} x {i.quantity} = ₦{i.subtotal}"
                    for i in order_items
                ]
            )
            message = f"""
Hi {order.user.username if order.user else 'Customer'},

Your payment has been confirmed, and your order is now processing.

Order ID: {order.id}
Total Paid: ₦{order.total}

Items:
{items_list}

Shipping Info:
Name: {order.shipping_full_name}
Phone: {order.shipping_phone}
Address: {order.shipping_address}, {order.shipping_city}, {order.shipping_state}, {order.shipping_country}
Postal Code: {order.shipping_postal_code}
Shipping Provider: {order.shipping_provider or 'Shippo'}
Tracking Number: {order.shipping_tracking_number or 'Not available yet'}
Status: {order.shipping_status or 'Pending'}

Thank you for your purchase!
            """

            send_mail(
                subject=f"Payment Received - Order {order.id}",
                message=message,
                from_email="no-reply@shop.com",
                recipient_list=[user_email],
                fail_silently=False,
            )

        logger.info(f"Order {order.id} processed successfully.")

    except Exception as exc:
        logger.error(f"Failed processing order {order_id}: {exc}")
        # Retry task in 10 seconds
        raise self.retry(exc=exc, countdown=10)
