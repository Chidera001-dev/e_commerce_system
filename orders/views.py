from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from rest_framework.pagination import PageNumberPagination
from drf_yasg.utils import swagger_auto_schema
from django.conf import settings

from .models import Order
from .serializers import OrderSerializer
from .permissions import IsOwnerOrAdmin
from carts.celery_tasks import checkout_cart_to_order
from paystackapi.paystack import Paystack

# ---------------- PAYSTACK HELPER ----------------
paystack = Paystack(secret_key=settings.PAYSTACK_SECRET_KEY)

def initialize_transaction(email, amount, reference):
    response = paystack.transaction.initialize(
        amount=int(amount * 100),  # Convert to kobo
        email=email,
        reference=reference
    )
    return response

def verify_transaction(reference):
    response = paystack.transaction.verify(reference)
    return response

# ---------------- PAGINATION ----------------
class OrderPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

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

# ---------------- PAYSTACK PAYMENT WEBHOOK ----------------
class PaymentWebhookAPIView(APIView):
    """
    Endpoint for Paystack webhook to confirm payment.
    """
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_summary="Paystack Payment Webhook",
        operation_description="Webhook to verify Paystack payment, update order status, and trigger receipt email."
    )
    def post(self, request):
        reference = request.data.get("reference")
        if not reference:
            return Response({"error": "Reference missing"}, status=400)

        order_id = reference.replace("ORD-", "")
        order = get_object_or_404(Order, id=order_id)

        verify_resp = verify_transaction(reference)
        if verify_resp['status'] and verify_resp['data']['status'] == "success":
            order.payment_status = "paid"
            order.status = "processing"
            order.save()
            # Trigger Celery task to send receipt email after successful payment
            checkout_cart_to_order.delay(cart_id=None, user_email=order.user.email, user_id=order.user.id)
            return Response({"message": "Payment verified and email sent"}, status=200)
        else:
            order.payment_status = "failed"
            order.status = "pending"
            order.save()
            return Response({"message": "Payment failed"}, status=400)
