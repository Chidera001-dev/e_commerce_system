import logging

from celery import shared_task
from django.core.mail import send_mail
from django.db import transaction

from carts.redis_cart import clear_cart
from orders.models import Order
from product.models import Product

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_order_after_payment(self, order_id, user_email=None, user_id=None):
    try:
        order = (
            Order.objects.select_related("user")
            .prefetch_related("items__product")
            .get(id=order_id)
        )
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found.")
        return

    #  STRONG IDEMPOTENCY GUARD
    if order.is_processed:
        logger.info(f"Order {order.id} already processed. Skipping.")
        return

    if order.payment_status != "paid":
        logger.warning(f"Order {order.id} not paid. Skipping.")
        return

    order_items = order.items.all()
    if not order_items.exists():
        logger.error(f"Order {order.id} has no items.")
        return

    try:
        with transaction.atomic():
            #  Lock products & reduce stock
            for item in order_items:
                product = Product.objects.select_for_update().get(id=item.product.id)
                if product.stock < item.quantity:
                    raise ValueError(f"Insufficient stock for {product.name}")

                product.stock -= item.quantity
                product.save(update_fields=["stock"])

            #  Clear cart
            if user_id:
                clear_cart(f"user:{user_id}")

            #  Update order business status
            order.status = "processing"
            order.is_processed = True
            order.save(update_fields=["status", "is_processed"])

            # Send email notification

            if user_email:
                currency_symbol = (
                    "₦" if getattr(order, "currency", "NGN").upper() == "NGN" else "$"
                )

                # Format items with dynamic currency
                items_list = "\n".join(
                    [
                        f"{i.product.name} x {i.quantity} = {currency_symbol}{i.subtotal}"
                        for i in order_items
                    ]
                )

                # Format total paid
                total_paid = f"{currency_symbol}{order.total}"

                shipping_info = (
                    f"Name: {order.shipping_full_name}\n"
                    f"Phone: {order.shipping_phone}\n"
                    f"Address: {order.full_shipping_address}"
                )

                message = f"""
Hi {order.user.username if order.user else 'Customer'},

Your payment has been confirmed, and your order is now processing.

Order ID: {order.id}
Total Paid: {total_paid}

Items:
{items_list}

Shipping Info:
{shipping_info}

A follow-up email will be sent when your shipment is created with tracking details.

Thank you for your purchase!
"""
                send_mail(
                    subject=f"Payment Successful - Order {order.id}",
                    message=message,
                    from_email="no-reply@shop.com",
                    recipient_list=[user_email],
                    fail_silently=True,
                )

        logger.info(f"Order {order.id} processed successfully.")

    except Exception as exc:
        logger.error(f"Order {order.id} failed: {exc}")
        raise self.retry(exc=exc, countdown=10)
