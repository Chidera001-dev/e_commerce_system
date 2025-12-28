from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from ecommerce_api.core.throttles import ComboRateThrottle

from orders.models import Order, OrderItem
from orders.utils import initialize_transaction
from product.models import Product
from services.models import Shipment, ShippingAddress
from services.shipping_service import calculate_shipping_fee

from .celery_tasks import process_order_after_payment as process_order_shipment
from .models import Cart, CartItem
from .permissions import CartPermission
from .redis_cart import clear_cart, get_cart as redis_get_cart, save_cart


class CartViewSet(viewsets.ViewSet):
    permission_classes = [CartPermission]
    throttle_classes = [ComboRateThrottle] 

    # ------------------- LIST CART -------------------
    @swagger_auto_schema(
        operation_summary="Get cart",
        operation_description="Retrieve the current cart (guest or authenticated).",
        responses={200: "Cart retrieved successfully"},
    )
    def list(self, request):
        if request.user.is_authenticated:
            key = f"user:{request.user.id}"
        else:
            key = request.session.session_key
            if not key:
                request.session.create()
                key = request.session.session_key

        cart_data = redis_get_cart(key) or {}
        total = sum(item.get("subtotal", 0) for item in cart_data.values())

        return Response({"items": cart_data, "total": total}, status=status.HTTP_200_OK)

    # ------------------- ADD ITEM -------------------
    @swagger_auto_schema(
        operation_summary="Add item to cart",
        operation_description="Add a product to the cart (supports authenticated and guest users).",
        responses={200: "Item added to cart"},
    )
    @action(detail=False, methods=["post"])
    def add_item(self, request):
        product_id = request.data.get("product_id")
        if not product_id:
            return Response({"error": "product_id is required"}, status=400)

        try:
            quantity = int(request.data.get("quantity", 1))
        except (ValueError, TypeError):
            return Response({"error": "quantity must be an integer"}, status=400)

        if quantity <= 0:
            return Response({"error": "quantity must be greater than zero"}, status=400)

        product = get_object_or_404(Product, id=product_id)
        if product.stock < quantity:
            return Response({"error": "Not enough stock"}, status=400)

        cart_obj, _ = self.load_cart(request)

        if request.user.is_authenticated:
            user_key = f"user:{request.user.id}"
            db_cart, _ = Cart.objects.get_or_create(user=request.user, is_active=True)
            item, created = CartItem.objects.get_or_create(
                cart=db_cart,
                product=product,
                defaults={"quantity": quantity, "price_snapshot": product.price},
            )
            if not created:
                item.quantity += quantity
                item.price_snapshot = product.price
                item.save()

            db_cart_data = {
                str(i.product.id): {
                    "quantity": i.quantity,
                    "price_snapshot": float(i.price_snapshot),
                    "subtotal": float(i.subtotal),
                }
                for i in db_cart.items.all()
            }
            save_cart(user_key, db_cart_data)

        else:
            session_key = cart_obj["session_key"]
            items = cart_obj.get("items", {}) or {}
            pid = str(product_id)

            if pid in items:
                items[pid]["quantity"] += quantity
            else:
                items[pid] = {
                    "quantity": quantity,
                    "price_snapshot": float(product.price),
                    "subtotal": float(product.price * quantity),
                }

            items[pid]["subtotal"] = float(
                items[pid]["quantity"] * items[pid]["price_snapshot"]
            )
            save_cart(session_key, items)

        return self.list(request)

    # ------------------- UPDATE ITEM -------------------
    @swagger_auto_schema(
        operation_summary="Update item quantity in cart",
        operation_description="Set the quantity of a product in the cart.",
        responses={200: "Item quantity updated"},
    )
    @action(detail=False, methods=["post"])
    def update_item(self, request):
        product_id = request.data.get("product_id")
        if not product_id:
            return Response({"error": "product_id is required"}, status=400)

        try:
            quantity = int(request.data.get("quantity", 1))
            if quantity <= 0:
                return Response({"error": "Quantity must be at least 1"}, status=400)
        except (ValueError, TypeError):
            return Response({"error": "Quantity must be an integer"}, status=400)

        product = get_object_or_404(Product, id=product_id)

        if request.user.is_authenticated:
            user_key = f"user:{request.user.id}"
            db_cart, _ = Cart.objects.get_or_create(user=request.user, is_active=True)
            item, created = CartItem.objects.get_or_create(
                cart=db_cart,
                product=product,
                defaults={"quantity": quantity, "price_snapshot": product.price},
            )
            if not created:
                item.quantity = quantity
                item.price_snapshot = product.price
                item.save()

            db_cart_data = {
                str(i.product.id): {
                    "quantity": i.quantity,
                    "price_snapshot": float(i.price_snapshot),
                    "subtotal": float(i.subtotal),
                }
                for i in db_cart.items.all()
            }
            save_cart(user_key, db_cart_data)

        else:
            session_key = request.session.session_key or request.session.create()
            items = redis_get_cart(session_key) or {}
            pid = str(product_id)

            if pid not in items:
                return Response({"error": "Item not in cart"}, status=400)

            items[pid]["quantity"] = quantity
            items[pid]["price_snapshot"] = float(product.price)
            items[pid]["subtotal"] = float(quantity * product.price)
            save_cart(session_key, items)

        return self.list(request)

    # ------------------- REMOVE ITEM -------------------
    @swagger_auto_schema(
        operation_summary="Remove an item from cart",
        operation_description="Remove a product completely from the cart.",
        responses={200: "Item removed"},
    )
    @action(detail=False, methods=["post"])
    def remove_item(self, request):
        product_id = request.data.get("product_id")
        if not product_id:
            return Response({"error": "product_id is required"}, status=400)

        if request.user.is_authenticated:
            cart = Cart.objects.filter(user=request.user, is_active=True).first()
            user_key = f"user:{request.user.id}"

            if cart:
                CartItem.objects.filter(cart=cart, product_id=product_id).delete()
                if not cart.items.exists():
                    cart.is_active = False
                    cart.save()

            cart_data = redis_get_cart(user_key) or {}
            cart_data.pop(str(product_id), None)

            if not cart_data:
                clear_cart(user_key)
            else:
                save_cart(user_key, cart_data)

        else:
            session_key = request.session.session_key
            if not session_key:
                return Response({"error": "No guest session found"}, status=400)

            cart_data = redis_get_cart(session_key) or {}
            cart_data.pop(str(product_id), None)

            if not cart_data:
                clear_cart(session_key)
            else:
                save_cart(session_key, cart_data)

        return Response({"message": "Item removed from cart"}, status=200)

    # ------------------- CHECKOUT -------------------
    @swagger_auto_schema(
        operation_summary="Checkout cart",
        operation_description="Create an order and initialize payment.",
        responses={200: "Checkout initialized"},
    )
    @action(detail=False, methods=["post"])
    def checkout(self, request):
        # Set scoped throttle dynamically
        self.throttle_classes = [ScopedRateThrottle]
        self.throttle_scope = "checkout"
        self.check_throttles(request)

        if not request.user.is_authenticated:
            return Response({"error": "Login required"}, status=401)

        cart = Cart.objects.filter(user=request.user, is_active=True).first()
        if not cart or not cart.items.exists():
            return Response({"error": "Cart is empty"}, status=400)

        for item in cart.items.all():
            if item.product.stock < item.quantity:
                return Response(
                    {"error": f"Insufficient stock for {item.product.name}"}, status=400
                )

        shipping_address_id = request.data.get("shipping_address_id")
        if not shipping_address_id:
            return Response({"error": "shipping_address_id is required"}, status=400)

        shipping_address = get_object_or_404(
            ShippingAddress, id=shipping_address_id, user=request.user
        )

        subtotal = sum(item.subtotal for item in cart.items.all())
        shipping_fee = calculate_shipping_fee(cart.items.all(), shipping_address)
        total_amount = subtotal + shipping_fee

        order = Order.objects.create(
            user=request.user,
            cart=cart,
            total=total_amount,
            status="pending",
            payment_status="pending",
            shipping_full_name=shipping_address.full_name,
            shipping_phone=shipping_address.phone,
            shipping_address_text=shipping_address.address,
            shipping_city=shipping_address.city,
            shipping_state=shipping_address.state,
            shipping_country=shipping_address.country,
            shipping_postal_code=shipping_address.postal_code,
            shipping_cost=shipping_fee,
        )

        OrderItem.objects.bulk_create(
            [
                OrderItem(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price_snapshot=item.price_snapshot,
                )
                for item in cart.items.all()
            ]
        )

        cart.items.all().delete()
        cart.is_active = False
        cart.save()

        order.reference = f"ORD-{order.id}"
        order.save()

        paystack_resp = initialize_transaction(
            request.user.email, int(order.total), order.reference
        )

        if not paystack_resp.get("status"):
            return Response(
                {"error": paystack_resp.get("message", "Payment failed")}, status=400
            )

        return Response(
            {
                "order_id": order.id,
                "reference": order.reference,
                "shipping_cost": shipping_fee,
                "total_amount": total_amount,
                "authorization_url": paystack_resp["data"]["authorization_url"],
                "access_code": paystack_resp["data"]["access_code"],
            },
            status=200,
        )

    # ------------------- LOAD CART -------------------
    def load_cart(self, request):
        if request.user.is_authenticated:
            user_key = f"user:{request.user.id}"
            cached_cart = redis_get_cart(user_key) or {}
            if cached_cart:
                return cached_cart, "redis"

            db_cart, _ = Cart.objects.get_or_create(user=request.user, is_active=True)
            cart_data = {
                str(i.product.id): {
                    "quantity": i.quantity,
                    "price_snapshot": float(i.price_snapshot),
                    "subtotal": float(i.subtotal),
                }
                for i in db_cart.items.all()
            }
            save_cart(user_key, cart_data)
            return cart_data, "redis"

        session_key = request.session.session_key or request.session.create()
        cart_data = redis_get_cart(session_key) or {}
        return {"session_key": session_key, "items": cart_data}, "redis"
