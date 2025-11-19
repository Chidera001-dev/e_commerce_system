from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema

from .models import Cart, CartItem
from product.models import Product
from .permissions import CartPermission
from .redis_cart import get_cart, get_cart_raw, save_cart, clear_cart
from .celery_tasks import checkout_cart_task


class CartListAPIView(APIView):
    """
    Retrieve current cart (guest or authenticated)
    """
    permission_classes = []

    # ------------------- HELPER -------------------
    def load_cart(self, request):
        """
        Load cart data for authenticated or guest user.
        Returns: (cart_data, key)
        """
        if request.user.is_authenticated:
            key = f"user:{request.user.id}"
            cached_cart = get_cart(key)
            if cached_cart:
                return cached_cart, key

            # Load from DB if not in Redis
            db_cart, _ = Cart.objects.get_or_create(user=request.user, is_active=True)
            cart_data = {
                str(i.product.id): {
                    "quantity": i.quantity,
                    "price_snapshot": float(i.price_snapshot),
                    "subtotal": float(i.subtotal)
                }
                for i in db_cart.items.all()
            }
            save_cart(key, cart_data)
            return cart_data, key
        else:
            # Guest
            session_key = request.session.session_key or request.session.create()
            cart_data = get_cart(session_key) or {}
            return cart_data, session_key

    @swagger_auto_schema(
        operation_summary="Get cart",
        operation_description="Retrieve current cart (guest or authenticated).",
        responses={200: "Cart retrieved successfully"}
    )
    def get(self, request):
        cart_data, _ = self.load_cart(request)
        total = sum(item.get("subtotal", 0) for item in cart_data.values())
        return Response({"items": cart_data, "total": total}, status=status.HTTP_200_OK)


class AddItemAPIView(APIView):
    permission_classes = []

    @swagger_auto_schema(
        operation_summary="Add item to cart",
        operation_description="Add a product to the cart. Authenticated writes DB + Redis; guest writes Redis.",
        responses={200: "Item added", 400: "Bad request"}
    )
    def post(self, request):
        product_id = request.data.get("product_id")
        if not product_id:
            return Response({"error": "product_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            quantity = int(request.data.get("quantity", 1))
            if quantity <= 0:
                raise ValueError
        except (ValueError, TypeError):
            return Response({"error": "quantity must be a positive integer"}, status=status.HTTP_400_BAD_REQUEST)

        product = get_object_or_404(Product, id=product_id)
        if product.stock < quantity:
            return Response({"error": "Not enough stock"}, status=status.HTTP_400_BAD_REQUEST)

        # Load cart
        cart_data, key = CartListAPIView().load_cart(request)

        if request.user.is_authenticated:
            # DB first
            db_cart, _ = Cart.objects.get_or_create(user=request.user, is_active=True)
            cart_item, created = CartItem.objects.get_or_create(
                cart=db_cart,
                product=product,
                defaults={"quantity": quantity, "price_snapshot": product.price}
            )
            if not created:
                cart_item.quantity = quantity
                cart_item.price_snapshot = product.price
                cart_item.save()

            # Sync Redis
            db_cart_data = {
                str(i.product.id): {
                    "quantity": i.quantity,
                    "price_snapshot": float(i.price_snapshot),
                    "subtotal": float(i.subtotal)
                }
                for i in db_cart.items.all()
            }
            save_cart(key, db_cart_data)
            return CartListAPIView().get(request)

        # Guest
        cart_data[str(product_id)] = {
            "quantity": quantity,
            "price_snapshot": float(product.price),
            "subtotal": quantity * float(product.price)
        }
        save_cart(key, cart_data)
        total = sum(i["subtotal"] for i in cart_data.values())
        return Response({"items": cart_data, "total": total}, status=status.HTTP_200_OK)


class UpdateItemAPIView(APIView):
    permission_classes = []

    @swagger_auto_schema(
        operation_summary="Update item quantity in cart",
        operation_description="Set the quantity of a product in the cart (authenticated or guest).",
        responses={200: "Item updated", 400: "Bad request"}
    )
    def post(self, request):
        product_id = request.data.get("product_id")
        if not product_id:
            return Response({"error": "product_id required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            quantity = int(request.data.get("quantity", 1))
            if quantity < 0:
                raise ValueError
        except (ValueError, TypeError):
            return Response({"error": "quantity must be an integer >= 0"}, status=status.HTTP_400_BAD_REQUEST)

        product = get_object_or_404(Product, id=product_id)
        cart_data, key = CartListAPIView().load_cart(request)

        if request.user.is_authenticated:
            db_cart, _ = Cart.objects.get_or_create(user=request.user, is_active=True)
            if quantity == 0:
                CartItem.objects.filter(cart=db_cart, product=product).delete()
            else:
                cart_item, created = CartItem.objects.get_or_create(
                    cart=db_cart,
                    product=product,
                    defaults={"quantity": quantity, "price_snapshot": product.price}
                )
                if not created:
                    cart_item.quantity = quantity
                    cart_item.price_snapshot = product.price
                    cart_item.save()

            db_cart_data = {
                str(i.product.id): {
                    "quantity": i.quantity,
                    "price_snapshot": float(i.price_snapshot),
                    "subtotal": float(i.subtotal)
                }
                for i in db_cart.items.all()
            }
            save_cart(key, db_cart_data)
            return CartListAPIView().get(request)

        # Guest
        if quantity == 0:
            cart_data.pop(str(product_id), None)
        else:
            cart_data[str(product_id)] = {
                "quantity": quantity,
                "price_snapshot": float(product.price),
                "subtotal": quantity * float(product.price)
            }
        save_cart(key, cart_data)
        total = sum(i["subtotal"] for i in cart_data.values())
        return Response({"items": cart_data, "total": total}, status=status.HTTP_200_OK)


class RemoveItemAPIView(APIView):
    permission_classes = []

    @swagger_auto_schema(
        operation_summary="Remove item from cart",
        operation_description="Remove a product from the cart (guest or authenticated).",
        responses={200: "Item removed"}
    )
    def post(self, request):
        product_id = request.data.get("product_id")
        if not product_id:
            return Response({"error": "product_id required"}, status=status.HTTP_400_BAD_REQUEST)

        cart_data, key = CartListAPIView().load_cart(request)

        if request.user.is_authenticated:
            db_cart = Cart.objects.filter(user=request.user, is_active=True).first()
            if db_cart:
                CartItem.objects.filter(cart=db_cart, product_id=product_id).delete()
                db_cart_data = {
                    str(i.product.id): {
                        "quantity": i.quantity,
                        "price_snapshot": float(i.price_snapshot),
                        "subtotal": float(i.subtotal)
                    }
                    for i in db_cart.items.all()
                }
                save_cart(key, db_cart_data)
                total = sum(i["subtotal"] for i in db_cart_data.values())
                return Response({"items": db_cart_data, "total": total}, status=status.HTTP_200_OK)
            else:
                return Response({"items": {}, "total": 0}, status=status.HTTP_200_OK)

        # Guest
        cart_data.pop(str(product_id), None)
        save_cart(key, cart_data)
        total = sum(i["subtotal"] for i in cart_data.values())
        return Response({"items": cart_data, "total": total}, status=status.HTTP_200_OK)


class MergeCartAPIView(APIView):
    permission_classes = [CartPermission]

    @swagger_auto_schema(
        operation_summary="Merge guest cart into user cart",
        operation_description="Merge anonymous session cart into authenticated user's DB cart after login.",
        responses={200: "Cart merged successfully", 401: "Not logged in"}
    )
    def post(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "Not logged in"}, status=status.HTTP_401_UNAUTHORIZED)

        session_key = request.session.session_key
        if not session_key:
            return Response({"message": "No anonymous session"}, status=status.HTTP_400_BAD_REQUEST)

        guest_cart = get_cart_raw(session_key) or {}
        if not guest_cart:
            return Response({"message": "No anonymous cart to merge"}, status=status.HTTP_200_OK)

        db_cart, _ = Cart.objects.get_or_create(user=request.user, is_active=True)

        for pid, item in guest_cart.items():
            product = get_object_or_404(Product, id=pid)
            cart_item, created = CartItem.objects.get_or_create(
                cart=db_cart,
                product=product,
                defaults={
                    "quantity": item.get("quantity", 0),
                    "price_snapshot": item.get("price_snapshot", product.price)
                }
            )
            if not created:
                cart_item.quantity = max(cart_item.quantity, int(item.get("quantity", 0)))
                cart_item.price_snapshot = product.price
                cart_item.save()

        # Sync Redis and clear guest cart
        user_key = f"user:{request.user.id}"
        db_cart_data = {
            str(i.product.id): {
                "quantity": i.quantity,
                "price_snapshot": float(i.price_snapshot),
                "subtotal": float(i.subtotal)
            }
            for i in db_cart.items.all()
        }
        save_cart(user_key, db_cart_data)
        clear_cart(session_key)

        return Response({"message": "Cart merged successfully"}, status=status.HTTP_200_OK)


class CheckoutAPIView(APIView):
    permission_classes = [CartPermission]

    @swagger_auto_schema(
        operation_summary="Checkout",
        operation_description="Checkout cart for authenticated users. Guest must register/login to checkout.",
        responses={200: "Checkout initiated", 401: "Not logged in", 400: "Cart empty"}
    )
    def post(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "Login required to checkout"}, status=status.HTTP_401_UNAUTHORIZED)

        cart_data, key = CartListAPIView().load_cart(request)
        db_cart, _ = Cart.objects.get_or_create(user=request.user, is_active=True)

        # Merge Redis values into DB cart
        for pid, item in cart_data.items():
            product = get_object_or_404(Product, id=pid)
            cart_item, created = CartItem.objects.get_or_create(
                cart=db_cart,
                product=product,
                defaults={
                    "quantity": item.get("quantity", 0),
                    "price_snapshot": item.get("price_snapshot", product.price)
                }
            )
            if not created:
                cart_item.quantity = int(item.get("quantity", cart_item.quantity))
                cart_item.price_snapshot = product.price
                cart_item.save()

        if not db_cart.items.exists():
            return Response({"error": "Your cart is empty"}, status=status.HTTP_400_BAD_REQUEST)

        # Trigger Celery
        checkout_cart_task.delay(
            cart_id=db_cart.id,
            redis_key=key,
            user_email=request.user.email,
            user_id=request.user.id
        )

        return Response({"message": "Checkout initiated"}, status=status.HTTP_200_OK)




   