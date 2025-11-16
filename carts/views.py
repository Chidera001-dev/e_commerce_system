from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action

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
    @action(detail=False, methods=["post"])
    def add_item(self, request):
        product_id = request.data.get("product_id")
        quantity = int(request.data.get("quantity", 1))
        product = get_object_or_404(Product, id=product_id)

        if product.stock < quantity:
            return Response({"error": "Not enough stock"}, status=400)

        cart, source = self.get_cart(request)

    # AUTHENTICATED USER
        if request.user.is_authenticated:
            user_key = f"user:{request.user.id}"

       
        # Do NOT add quantities twice. Replace or set.
            cart[str(product_id)] = {
                "quantity": quantity,
                "price_snapshot": float(product.price),
                "subtotal": float(product.price * quantity)
            }
            save_cart(user_key, cart)

        # --- UPDATE DATABASE CORRECTLY ---
            db_cart, _ = Cart.objects.get_or_create(user=request.user, is_active=True)
            item, created = CartItem.objects.get_or_create(
                cart=db_cart,
                product=product,
                defaults={"quantity": quantity, "price_snapshot": product.price}
            )

        # Replace quantity instead of +=
            if not created:
                item.quantity = quantity
                item.price_snapshot = product.price
                item.save()

        else:
            # GUEST USER
            items = cart["items"]
            items[str(product_id)] = {
                "quantity": quantity,
                "price_snapshot": float(product.price),
             "subtotal": float(product.price * quantity)
            }

            save_cart(cart["session_key"], items)

        return self.list(request)

  

    # ------------------- MERGE CART -------------------
    @swagger_auto_schema(
        operation_summary="Merge guest cart into user cart",
        operation_description="Merge a guest cart into an authenticated user cart after login.",
        responses={200: "Cart merged successfully"}
    )
    @action(detail=False, methods=["post"])
    def merge_cart(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "Not logged in"}, status=400)

        session_key = request.session.session_key
        redis_cart = get_cart(session_key)

        if not redis_cart:
            return Response({"message": "No anonymous cart to merge"})

        cart, _ = Cart.objects.get_or_create(user=request.user, is_active=True)

    
        for product_id_str, item in redis_cart.items():
            product = get_object_or_404(Product, id=product_id_str)

            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={
                    "quantity": item["quantity"],
                    "price_snapshot": item["price_snapshot"]
                }
            )

            if not created:
                cart_item.quantity = item["quantity"]   
                cart_item.price_snapshot = item["price_snapshot"]
                cart_item.save()

        # ---- SYNC REDIS WITH DATABASE ----
        user_key = f"user:{request.user.id}"
        db_cart_data = {
            str(i.product.id): {
                "quantity": i.quantity,
                "price_snapshot": float(i.price_snapshot),
                "subtotal": float(i.subtotal)
            }
            for i in cart.items.all()
        }

        (user_key, db_cart_data)

        clear_cart(session_key)
        return Response({"message": "Cart merged successfully"})


    # ------------------- CHECKOUT -------------------
    @swagger_auto_schema(
        operation_summary="Checkout",
        operation_description="Checkout cart for authenticated users. Guest must register or login first.",
        responses={200: "Checkout initiated"}
    )
    @action(detail=False, methods=["post"])
    def checkout(self, request):
        if not request.user.is_authenticated:
            return Response(
                {"error": "You must be logged in to checkout. Please sign up or log in."},
                status=401
            )

        user = request.user
        user_key = f"user:{user.id}"

    #  Get Redis cart
        cached_cart = get_cart(user_key)

    #  Merge Redis → DB
        cart, _ = Cart.objects.get_or_create(user=user, is_active=True)

        if cached_cart:
            for product_id_str, item in cached_cart.items():
                product = get_object_or_404(Product, id=product_id_str)

                cart_item, created = CartItem.objects.get_or_create(
                    cart=cart,
                    product=product,
                    defaults={
                        "quantity": item["quantity"],
                        "price_snapshot": item["price_snapshot"]
                    }
                )

                if not created:
                    cart_item.quantity = item["quantity"]    
                    cart_item.price_snapshot = item["price_snapshot"]
                    cart_item.save()


        # Clear Redis after merge
            clear_cart(user_key)

    #  If cart still empty, stop checkout
        if not cart.items.exists():
            return Response({"error": "Your cart is empty"}, status=400)

    #  Run Celery checkout task
        checkout_cart.delay(cart.id, user_email=user.email, user_id=user.id)

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

