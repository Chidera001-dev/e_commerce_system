from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema

from .models import Order
from .serializers import OrderSerializer
from .permissions import IsOwnerOrAdmin
from .pagination import OrderPagination
from carts.models import Cart
from carts.celery_tasks import process_order_after_payment
from .utils import initialize_transaction, verify_transaction

# ---------------- ORDER LIST ----------------
class OrderListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="List Orders",
        operation_description="List all orders for authenticated user or all orders if admin. Supports pagination.",
        responses={200: OrderSerializer(many=True)}
    )
    def get(self, request):
        user = request.user
        qs = Order.objects.prefetch_related("items__product").order_by("-created_at")
        if not user.is_staff:
            qs = qs.filter(user=user)

        paginator = OrderPagination()
        result_page = paginator.paginate_queryset(qs, request)
        serializer = OrderSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)

# ---------------- ORDER DETAIL ----------------
class OrderDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    @swagger_auto_schema(
        operation_summary="Order Detail",
        operation_description="Retrieve details of a specific order by ID. Users can only access their own orders.",
        responses={200: OrderSerializer()}
    )
    def get(self, request, order_id):
        order = get_object_or_404(Order, id=order_id)
        self.check_object_permissions(request, order)
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)

# ---------------- MARK SHIPPED ----------------
class OrderMarkShippedAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    @swagger_auto_schema(
        operation_summary="Mark Order as Shipped",
        operation_description="Admin endpoint to mark an order as shipped."
    )
    def post(self, request, order_id):
        order = get_object_or_404(Order, id=order_id)
        order.status = "shipped"
        order.save()
        return Response({"message": f"Order {order.id} marked as shipped"}, status=status.HTTP_200_OK)

# ---------------- PAYSTACK INITIALIZE ----------------
class PaystackInitializeAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Initialize Paystack Payment",
        operation_description="Generate authorization URL for frontend to redirect user for payment."
    )
    def post(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, user=request.user)
        reference = f"ORD-{order.id}"
        response = initialize_transaction(order.user.email, order.total, reference)

        if response['status']:
            return Response({
                "authorization_url": response['data']['authorization_url'],
                "access_code": response['data']['access_code'],
                "reference": reference
            }, status=200)
        return Response({"error": response['message']}, status=400)

# ---------------- PAYMENT WEBHOOK ----------------
class PaymentWebhookAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        payload = request.data
        event = payload.get("event")
        reference = payload.get("data", {}).get("reference")
        
        if not reference:
            return Response({"error": "Reference missing"}, status=400)
        
        if not reference.startswith("CART-"):
            return Response({"error": "Invalid reference"}, status=400)

        # Extract cart_id from reference
        cart_id = reference.replace("CART-", "")
        cart = get_object_or_404(Cart, id=cart_id)

        # Find the pending order for this cart
        order = Order.objects.filter(user=cart.user, status="pending", total=cart.total).first()
        if not order:
            return Response({"error": "Order not found"}, status=400)

        # Trigger Celery task
        process_order_after_payment.delay(
            cart_id=cart.id,
            order_id=order.id,
            user_email=cart.user.email,
            user_id=cart.user.id
        )

        return Response({"message": "Payment verified. Order processing started."}, status=200)
