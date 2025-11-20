from celery import shared_task
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import get_object_or_404
from orders.models import Order, OrderItem
from carts.models import Cart, CartItem
from product.models import Product
from carts.redis_cart import clear_cart

@shared_task
def checkout_cart_to_order(cart_id, user_email=None, user_id=None):
    """
    Create an Order from Cart, reduce stock, clear cart, send email after payment.
    """
    cart = get_object_or_404(Cart, id=cart_id)
    items = cart.items.select_related("product").all()

    with transaction.atomic():
        # Create Order
        order = Order.objects.create(
            user=cart.user,
            total=sum(item.subtotal for item in items),
            status="pending",
            payment_status="pending"
        )

        # Transfer CartItems → OrderItems
        for item in items:
            product = Product.objects.select_for_update().get(id=item.product.id)
            if product.stock < item.quantity:
                raise ValueError(f"Insufficient stock for {product.name}")

            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=item.quantity,
                price_snapshot=item.price_snapshot
            )

            # Reduce stock
            product.stock -= item.quantity
            product.save()

        # Clear cart
        cart.is_active = False
        cart.save()
        cart.items.all().delete()
        if user_id:
            clear_cart(f"user:{user_id}")

    # OPTIONAL: Send receipt email AFTER payment
    if user_email:
        items_list = "\n".join(
            [f"{item.product.name} x {item.quantity} = ${item.subtotal}" for item in items]
        )

        message = f"""
        Hi {cart.user.username if cart.user else 'Customer'},

        Thank you for your payment! Your order has been successfully processed.

        Order ID: {order.id}
        Total Paid: ${order.total}

        Items Purchased:
        {items_list}

        Your order is now being prepared for shipment. You will receive another email once it has been shipped.

        If you have any questions or need assistance, please contact our support team at support@shop.com.

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




