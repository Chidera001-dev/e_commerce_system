from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema

from .models import Cart, CartItem
from product.models import Product
from .permissions import CartPermission
from .redis_cart import get_cart as redis_get_cart, save_cart, clear_cart
from .celery_tasks import checkout_cart_to_order


class CartViewSet(viewsets.ViewSet):
    permission_classes = [CartPermission]

    # ------------------- LIST CART -------------------
    @swagger_auto_schema(
        operation_summary="Get cart",
        operation_description="Retrieve the current cart (guest or authenticated).",
        responses={200: "Cart retrieved successfully"}
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
        responses={200: "Item added to cart"}
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

        # Load cart
        cart_obj, _ = self.load_cart(request)

        if request.user.is_authenticated:
            user_key = f"user:{request.user.id}"
            db_cart, _ = Cart.objects.get_or_create(user=request.user, is_active=True)

            # Add or update CartItem
            item, created = CartItem.objects.get_or_create(
                cart=db_cart,
                product=product,
                defaults={"quantity": quantity, "price_snapshot": product.price}
            )
            if not created:
                item.quantity += quantity
                item.price_snapshot = product.price
                item.save()

            # Sync Redis with DB
            db_cart_data = {
                str(i.product.id): {
                    "quantity": i.quantity,
                    "price_snapshot": float(i.price_snapshot),
                    "subtotal": float(i.subtotal)
                } for i in db_cart.items.all()
            }
            save_cart(user_key, db_cart_data)

        else:  # Guest
            session_key = cart_obj["session_key"]
            items = cart_obj.get("items", {}) or {}
            pid = str(product_id)
            if pid in items:
                items[pid]["quantity"] += quantity
            else:
                items[pid] = {
                    "quantity": quantity,
                    "price_snapshot": float(product.price),
                    "subtotal": float(product.price * quantity)
                }
            items[pid]["subtotal"] = float(items[pid]["quantity"] * items[pid]["price_snapshot"])
            save_cart(session_key, items)

        return self.list(request)

    # ------------------- UPDATE ITEM -------------------
    @swagger_auto_schema(
        operation_summary="Update item quantity in cart",
        operation_description="Set the quantity of a product in the cart (authenticated or guest).",
        responses={200: "Item quantity updated"}
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
                defaults={"quantity": quantity, "price_snapshot": product.price}
            )
            if not created:
                item.quantity = quantity
                item.price_snapshot = product.price
                item.save()

            # Sync Redis
            db_cart_data = {
                str(i.product.id): {
                    "quantity": i.quantity,
                    "price_snapshot": float(i.price_snapshot),
                    "subtotal": float(i.subtotal)
                } for i in db_cart.items.all()
            }
            save_cart(user_key, db_cart_data)

        else:  # Guest
            session_key = request.session.session_key or request.session.create()
            items = redis_get_cart(session_key) or {}
            pid = str(product_id)
            if pid in items:
                items[pid]["quantity"] = quantity
                items[pid]["price_snapshot"] = float(product.price)
                items[pid]["subtotal"] = float(quantity * product.price)
                save_cart(session_key, items)
            else:
                return Response({"error": "Item not in cart"}, status=400)

        return self.list(request)

    # ------------------- REMOVE ITEM -------------------
    @swagger_auto_schema(
        operation_summary="Remove an item from cart",
        operation_description="Completely remove a product from the cart (works for both authenticated and guest users).",
        responses={200: "Item removed from cart", 400: "Bad request"}
    )
    @action(detail=False, methods=["post"])
    def remove_item(self, request):
        product_id = request.data.get("product_id")
        if not product_id:
            return Response({"error": "product_id is required"}, status=400)

        if request.user.is_authenticated:
            user_key = f"user:{request.user.id}"
            cart = Cart.objects.filter(user=request.user, is_active=True).first()
            if cart:
                CartItem.objects.filter(cart=cart, product_id=product_id).delete()
            cart_data = redis_get_cart(user_key)
            cart_data.pop(str(product_id), None)
            save_cart(user_key, cart_data)

        else:
            session_key = request.session.session_key
            if not session_key:
                return Response({"error": "No guest session found"}, status=400)
            cart_data = redis_get_cart(session_key)
            cart_data.pop(str(product_id), None)
            save_cart(session_key, cart_data)

        return Response({"message": "Item removed from cart"}, status=200)

    # ------------------- CHECKOUT -------------------
    @swagger_auto_schema(
        operation_summary="Checkout",
        operation_description="Checkout cart for authenticated users. Guest must register/login to checkout.",
        responses={200: "Checkout initiated"}
    )
    @action(detail=False, methods=["post"])
    def checkout(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "Login required"}, status=401)

        cart = Cart.objects.filter(user=request.user, is_active=True).first()
        if not cart or not cart.items.exists():
            return Response({"error": "Cart is empty"}, status=400)

        checkout_cart_to_order.delay(cart.id, user_email=request.user.email, user_id=request.user.id)

        return Response({"message": "Checkout initiated", "order_cart_id": cart.id}, status=200)

    # ------------------- HELPER -------------------
    def load_cart(self, request):
        """
        Returns (cart_data, source)
        Authenticated: dict of {product_id: {quantity, price_snapshot, subtotal}}
        Guest: {"session_key": ..., "items": {...}}
        """
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
                    "subtotal": float(i.subtotal)
                } for i in db_cart.items.all()
            }
            save_cart(user_key, cart_data)
            return cart_data, "redis"

        session_key = request.session.session_key or request.session.create()
        cart_data = redis_get_cart(session_key) or {}
        return {"session_key": session_key, "items": cart_data}, "redis"








