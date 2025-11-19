from celery import shared_task
from django.core.mail import send_mail
from .models import Cart, CartItem
from .redis_cart import clear_cart
from django.db import transaction

@shared_task
def checkout_cart_task(cart_id, redis_key=None, user_email=None, user_id=None):
    """
    Celery task to handle checkout:
    - Reduce product stock
    - Mark cart inactive
    - Clear Redis cart
    - Send confirmation email
    """
    try:
        cart = Cart.objects.get(id=cart_id, is_active=True)
    except Cart.DoesNotExist:
        return "Cart does not exist"

    with transaction.atomic():
        # Reduce stock
        for item in cart.items.select_related('product'):
            product = item.product
            if product.stock < item.quantity:
                raise Exception(f"Not enough stock for {product.name}")
            product.stock -= item.quantity
            product.save()

        # Mark cart inactive
        cart.is_active = False
        cart.save()

        # Clear Redis cart
        if redis_key:
            clear_cart(redis_key)

    # Send confirmation email
    if user_email:
        subject = "Your order has been placed"
        message = f"Hello! Your order #{cart_id} has been successfully placed."
        send_mail(subject, message, 'no-reply@myshop.com', [user_email])

    return "Checkout completed"

