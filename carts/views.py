from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema

from .models import Cart, CartItem
from product.models import Product
from .serializers import CartSerializer
from .permissions import CartPermission
from .redis_cart import get_cart, save_cart, clear_cart
from .celery_tasks import checkout_cart


class CartViewSet(viewsets.ViewSet):
    permission_classes = [CartPermission]

    # ------------------- GET CART -------------------
    @swagger_auto_schema(
        operation_summary="Get cart",
        operation_description="Retrieve the current authenticated user's cart or the guest session cart.",
        responses={200: "Returns items and total amount"}
    )
    def list(self, request):
        cart, source = self.get_cart(request)
        items = cart.get("items", cart)
        total = sum(item["subtotal"] for item in items.values())
        return Response({"items": items, "total": total})

    # ------------------- ADD ITEM -------------------
    @swagger_auto_schema(
        operation_summary="Add item to cart",
        operation_description="Add a product to the cart (supports both authenticated and guest users).",
        responses={200: "Item added to cart"}
    )
    def add_item(self, request):
        product_id = int(request.data.get("product_id"))
        quantity = int(request.data.get("quantity", 1))
        product = get_object_or_404(Product, id=product_id)

        if product.stock < quantity:
            return Response({"error": "Not enough stock"}, status=status.HTTP_400_BAD_REQUEST)

        cart, source = self.get_cart(request)

        if request.user.is_authenticated:
            user_key = f"user:{request.user.id}"

            # Update Redis
            if str(product_id) in cart:
                cart[str(product_id)]["quantity"] += quantity
            else:
                cart[str(product_id)] = {
                    "quantity": quantity,
                    "price_snapshot": float(product.price),
                    "subtotal": float(product.price * quantity)
                }
            cart[str(product_id)]["subtotal"] = cart[str(product_id)]["quantity"] * cart[str(product_id)]["price_snapshot"]
            save_cart(user_key, cart)

            # Update DB
            db_cart, _ = Cart.objects.get_or_create(user=request.user, is_active=True)
            item, created = CartItem.objects.get_or_create(
                cart=db_cart,
                product=product,
                defaults={"quantity": quantity, "price_snapshot": product.price}
            )
            if not created:
                item.quantity += quantity
                item.save()

        else:
            # Anonymous users
            items = cart["items"]
            if str(product_id) in items:
                items[str(product_id)]["quantity"] += quantity
            else:
                items[str(product_id)] = {
                    "quantity": quantity,
                    "price_snapshot": float(product.price),
                    "subtotal": float(product.price * quantity)
                }
            items[str(product_id)]["subtotal"] = items[str(product_id)]["quantity"] * items[str(product_id)]["price_snapshot"]
            save_cart(cart["session_key"], items)

        return self.list(request)

    # ------------------- MERGE CART -------------------
    @swagger_auto_schema(
        operation_summary="Merge guest cart into user cart",
        operation_description="Merge a guest cart into an authenticated user cart after login.",
        responses={200: "Cart merged successfully"}
    )
    def merge_cart(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "Not logged in"}, status=400)

        session_key = request.session.session_key
        redis_cart = get_cart(session_key)
        if not redis_cart:
            return Response({"message": "No anonymous cart to merge"})

        cart, _ = Cart.objects.get_or_create(user=request.user, is_active=True)
        for product_id_str, item in redis_cart.items():
            product_id = int(product_id_str)
            product = get_object_or_404(Product, id=product_id)

            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={"quantity": item["quantity"], "price_snapshot": item["price_snapshot"]}
            )
            if not created:
                cart_item.quantity += item["quantity"]
                cart_item.save()

        # Update Redis
        user_key = f"user:{request.user.id}"
        db_cart_data = {
            str(i.product.id): {
                "quantity": i.quantity,
                "price_snapshot": float(i.price_snapshot),
                "subtotal": float(i.subtotal)
            }
            for i in cart.items.all()
        }
        save_cart(user_key, db_cart_data)

        clear_cart(session_key)
        return Response({"message": "Cart merged successfully"})

    # ------------------- CHECKOUT -------------------
    @swagger_auto_schema(
        operation_summary="Checkout",
        operation_description="Checkout cart for authenticated or guest users. Guest must provide an email.",
        responses={200: "Checkout initiated"}
    )
    def checkout(self, request):
        if request.user.is_authenticated:
            cart = Cart.objects.filter(user=request.user, is_active=True).first()
            if not cart:
                return Response({"error": "No active cart"}, status=400)

            checkout_cart.delay(cart.id, user_email=request.user.email, user_id=request.user.id)

        else:
            session_key = request.session.session_key
            cart_data = get_cart(session_key)
            if not cart_data:
                return Response({"error": "No cart found"}, status=400)

            temp_cart = Cart.objects.create(is_active=False)
            for product_id_str, item in cart_data.items():
                product = get_object_or_404(Product, id=int(product_id_str))
                CartItem.objects.create(
                    cart=temp_cart,
                    product=product,
                    quantity=item["quantity"],
                    price_snapshot=item["price_snapshot"]
                )

            checkout_cart.delay(temp_cart.id, user_email=request.data.get("email"))
            clear_cart(session_key)

        return Response({"message": "Checkout initiated"}, status=200)

    # ------------------- HELPER -------------------
    def get_cart(self, request):
        if request.user.is_authenticated:
            user_key = f"user:{request.user.id}"
            cached_cart = get_cart(user_key)
            if cached_cart:
                return cached_cart, "redis"

            cart, _ = Cart.objects.get_or_create(user=request.user, is_active=True)
            cart_data = {
                str(item.product.id): {
                    "quantity": item.quantity,
                    "price_snapshot": float(item.price_snapshot),
                    "subtotal": float(item.subtotal)
                } for item in cart.items.all()
            }
            save_cart(user_key, cart_data)
            return cart_data, "redis"

        else:
            session_key = request.session.session_key or request.session.create()
            cart_data = get_cart(session_key)
            return {"session_key": session_key, "items": cart_data}, "redis"



# Create your views here.
