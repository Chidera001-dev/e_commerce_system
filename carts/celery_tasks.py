from celery import shared_task
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from django.db import transaction
from django.core.exceptions import ValidationError

from .models import Cart
from product.models import Product
from .redis_cart import clear_cart

@shared_task
def checkout_cart(cart_id, user_email=None, user_id=None):
    """
    Checkout task:
    - Reduce product stock safely
    - Fail if any product has insufficient stock
    - Mark cart inactive
    - Clear Redis cart
    - Send receipt email
    """

    # Get cart and its items
    cart = get_object_or_404(Cart, id=cart_id)
    items = cart.items.select_related("product").all()  # Avoid extra queries

    with transaction.atomic(): 
        # Lock each product row and check stock
        for item in items:
            product = Product.objects.select_for_update().get(id=item.product.id)

            if product.stock < item.quantity:
                raise ValidationError(
                    f"Insufficient stock for '{product.name}'. "
                    f"Requested: {item.quantity}, Available: {product.stock}"
                )

            # Reduce stock
            product.stock -= item.quantity
            product.save()

            # Clear Redis cache for product
            cache.delete(f"product:{product.id}")

        # Mark cart inactive
        cart.is_active = False
        cart.save()

        # Optionally clear cart items after successful checkout
        cart.items.all().delete()

    # Clear Redis cart for authenticated user
    if user_id:
        clear_cart(f"user:{user_id}")

    # Build receipt message
    total_amount = sum(item.subtotal for item in items)
    message = f"Thank you for your order.\nTotal: ${total_amount}\n\nItems:\n"
    for item in items:
        message += f" Hello! Your order {item.product.name} x {item.quantity} = ${item.subtotal}\n has been successfully placed."

    # Send email receipt
    if user_email:
        send_mail(
            subject="Your Order Receipt",
            message=message,
            from_email="no-reply@shop.com",
            recipient_list=[user_email],
            fail_silently=False
        )

    return "Checkout complete"

