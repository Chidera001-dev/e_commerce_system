import logging
from celery import shared_task
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import get_object_or_404
from orders.models import Order, OrderItem
from product.models import Product
from carts.redis_cart import clear_cart

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def process_order_after_payment(self, order_id, user_email=None, user_id=None):

    try:
        order = get_object_or_404(Order, id=order_id)

        order_items = order.items.select_related("product").all()
        if not order_items.exists():
            logger.error(f"Order {order.id} has no items. Task stopped (not retrying).")
            # mark order as error
            order.status = "pending_items"
            order.payment_status = "pending"
            order.save()
            return  

        with transaction.atomic():

            # reduce stock
            for item in order_items:
                product = Product.objects.select_for_update().get(id=item.product.id)

                if product.stock < item.quantity:
                    raise ValueError(f"Insufficient stock for {product.name}")

                product.stock -= item.quantity
                product.save()

            # clear redis cart
            if user_id:
                clear_cart(f"user:{user_id}")

            # update order
            order.payment_status = "paid"
            order.status = "processing"
            order.save()

        # send email
        if user_email:
            items_list = "\n".join(
                [f"{i.product.name} x {i.quantity} = ₦{i.subtotal}" for i in order_items]
            )
            message = f"""
Hi {order.user.username if order.user else 'Customer'},

Your payment is confirmed and your order is now processing.

Order ID: {order.id}
Total Paid: ₦{order.total}

Items:
{items_list}

Thank you for your purchase!
            """

            send_mail(
                subject=f"Payment Received - Order {order.id}",
                message=message,
                from_email="no-reply@shop.com",
                recipient_list=[user_email],
                fail_silently=False
            )

        logger.info(f"Order {order.id} processed SUCCESSFULLY.")

    except Exception as exc:
        logger.error(f"Failed processing order {order_id}: {exc}")
        raise self.retry(exc=exc, countdown=10)

