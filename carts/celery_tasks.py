import logging
from celery import shared_task
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import get_object_or_404
from orders.models import Order, OrderItem
from carts.models import Cart, CartItem
from product.models import Product
from carts.redis_cart import clear_cart

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def process_order_after_payment(self, cart_id, order_id, user_email=None, user_id=None):
    """
    Moves CartItems to OrderItems, reduces stock, clears cart, and sends receipt email.
    Runs only after payment is confirmed.
    """
    try:
        cart = get_object_or_404(Cart, id=cart_id)
        order = get_object_or_404(Order, id=order_id)
        items = cart.items.select_related("product").all()

        if not items.exists():
            raise ValueError("Cannot process an empty cart")

        with transaction.atomic():
            order_items = []

            for item in items:
                product = Product.objects.select_for_update().get(id=item.product.id)
                
                if product.stock < item.quantity:
                    raise ValueError(f"Insufficient stock for {product.name}")

                # Prepare OrderItem
                order_items.append(OrderItem(
                    order=order,
                    product=product,
                    quantity=item.quantity,
                    price_snapshot=item.price_snapshot
                ))

                # Reduce stock
                product.stock -= item.quantity
                product.save()

            # Bulk create OrderItems
            OrderItem.objects.bulk_create(order_items)

            # Clear DB cart
            cart.is_active = False
            cart.items.all().delete()
            cart.save()

            # Clear Redis
            if user_id:
                clear_cart(f"user:{user_id}")

            # Update order status
            order.payment_status = "paid"
            order.status = "processing"
            order.save()

        # Send confirmation email
        if user_email:
            items_list = "\n".join([f"{i.product.name} x {i.quantity} = ₦{i.subtotal}" for i in items])
            message = f"""
Hi {cart.user.username if cart.user else 'Customer'},

Thank you for your payment! Your order has been successfully processed.

Order ID: {order.id}
Total Paid: ₦{order.total}

Items Purchased:
{items_list}

Your order is now being prepared for shipment. You will receive another email once it has been shipped.

Thank you for shopping with us!

Best regards,
The Shop Team
            """
            send_mail(
                subject=f"Payment Received - Order {order.id}",
                message=message,
                from_email="no-reply@shop.com",
                recipient_list=[user_email],
                fail_silently=False
            )

        logger.info(f"Order {order.id} processed successfully for cart {cart.id}")

    except Exception as exc:
        logger.error(f"Failed to process order for cart {cart_id}, order {order_id}: {exc}")
        # Retry the task up to 3 times if something goes wrong
        raise self.retry(exc=exc, countdown=10)



