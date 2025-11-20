from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from rest_framework.pagination import PageNumberPagination
from drf_yasg.utils import swagger_auto_schema

from .models import Order
from .serializers import OrderSerializer
from .permissions import IsOwnerOrAdmin
from carts.celery_tasks import checkout_cart_to_order


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

# ---------------- PAYMENT WEBHOOK ----------------
class PaymentWebhookAPIView(APIView):
    """
    Endpoint for payment gateway to notify payment status.
    """
    permission_classes = [permissions.AllowAny]  # Gateway posts here

    @swagger_auto_schema(
        operation_summary="Payment Webhook",
        operation_description="Payment gateway webhook to confirm payment. Updates order status and triggers receipt email.",
    )
    def post(self, request):
        order_id = request.data.get("order_id")
        payment_status = request.data.get("payment_status")  # "success" or "failed"
        amount_paid = request.data.get("amount_paid")

        order = get_object_or_404(Order, id=order_id)

        if payment_status == "success":
            order.payment_status = "paid"
            order.status = "processing"
            order.save()

            # Trigger Celery task to send email
            checkout_cart_to_order.delay(cart_id=None, user_email=order.user.email, user_id=order.user.id)

            return Response({"message": "Payment confirmed, email sent"}, status=status.HTTP_200_OK)
        else:
            order.payment_status = "failed"
            order.status = "pending"
            order.save()
            return Response({"message": "Payment failed"}, status=status.HTTP_400_BAD_REQUEST)





# Create your views here.
