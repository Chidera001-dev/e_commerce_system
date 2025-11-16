from celery import shared_task
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from .models import Cart
from product.models import Product
from .redis_cart import clear_cart


@shared_task
def checkout_cart(cart_id, user_email=None, user_id=None):
    """
    Checkout task:
    - Reduce product stock
    - Mark cart inactive
    - Clear Redis
    - Send receipt email
    """

    cart = get_object_or_404(Cart, id=cart_id)
    items = cart.items.all()

    #  Reduce product stock
    for item in items:
        product = item.product

        # Reduce stock safely
        product.stock = max(product.stock - item.quantity, 0)
        product.save()

        # Clear product cache
        cache.delete(f"product:{product.id}")

    #  Mark cart inactive
    cart.is_active = False
    cart.save()

    # Clear DB cart items after checkout
    cart.items.all().delete()

    #  Clear Redis cart
    if user_id:
        clear_cart(f"user:{user_id}")

    #  Build receipt
    total_amount = sum(item.subtotal for item in items)
    message = f"Thank you for your order.\nTotal: ${total_amount}\n\nItems:\n"

    for item in items:
        message += f"{item.product.name} x {item.quantity} = ${item.subtotal}\n"

    #  Send email
    if user_email:
        send_mail(
            subject="Your Order Receipt",
            message=message,
            from_email="no-reply@shop.com",
            recipient_list=[user_email],
            fail_silently=False
        )

    return "Checkout complete"





