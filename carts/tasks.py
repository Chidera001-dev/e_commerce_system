from celery import shared_task
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from .models import Cart
from .redis_cart import clear_cart

@shared_task
def checkout_cart(cart_id, user_email=None, user_id=None):
    """
    Checkout task that:
    1. Marks the cart as inactive in DB
    2. Clears Redis cache for authenticated users
    3. Sends receipt email asynchronously
    """
    cart = get_object_or_404(Cart, id=cart_id)
    cart.is_active = False
    cart.save()

    if user_id:
        user_key = f"user:{user_id}"
        clear_cart(user_key)

    # Prepare receipt
    message = f"Thank you for your order. Total: ${cart.total}\n\nItems:\n"
    for item in cart.items.all():
        message += f"{item.product.name} x {item.quantity} = ${item.subtotal}\n"

    if user_email:
        send_mail(
            subject="Your Order Receipt",
            message=message,
            from_email="no-reply@shop.com",
            recipient_list=[user_email],
            fail_silently=False
        )
