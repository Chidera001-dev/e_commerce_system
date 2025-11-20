from celery import shared_task
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from django.core.exceptions import ValidationError

from .models import Cart
from product.models import Product
from .redis_cart import clear_cart
from orders.models import Order, OrderItem  # import your Order models

@shared_task
def checkout_cart(cart_id, user_email=None, user_id=None):
    """
    Checkout task:
    - Move cart items to Order + OrderItem
    - Reduce product stock safely
    - Mark cart inactive
    - Clear Redis cart
    - Send receipt email
    """
    cart = get_object_or_404(Cart, id=cart_id)
    items = cart.items.select_related("product").all()

    if not items.exists():
        raise ValidationError("Cannot checkout empty cart.")

    with transaction.atomic():
        # Lock each product row and reduce stock
        for item in items:
            product = Product.objects.select_for_update().get(id=item.product.id)
            if product.stock < item.quantity:
                raise ValidationError(
                    f"Insufficient stock for {product.name}. Requested: {item.quantity}, Available: {product.stock}"
                )
            product.stock -= item.quantity
            product.save()
            cache.delete(f"product:{product.id}")

        # Create Order
        order = Order.objects.create(
            user=cart.user,
            total=sum(item.subtotal for item in items),
            status='PENDING'
        )

        # Move CartItems → OrderItems
        order_items = [
            OrderItem(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price_snapshot=item.price_snapshot
            )
            for item in items
        ]
        OrderItem.objects.bulk_create(order_items)

        # Mark cart inactive and clear items
        cart.is_active = False
        cart.save()
        cart.items.all().delete()

        # Clear Redis cart
        if user_id:
            clear_cart(f"user:{user_id}")

    # Send email receipt
    if user_email:
        message = f"Thank you for your order {order.id}.\nTotal: ${order.total}\n\nItems:\n"
        for i in order.items.all():
            message += f"- {i.product.name} x {i.quantity} = ${i.subtotal}\n"
        send_mail(
            subject=f"Order Receipt {order.id}",
            message=message,
            from_email="no-reply@shop.com",
            recipient_list=[user_email],
            fail_silently=False
        )

    return f"Checkout complete for order {order.id}"


