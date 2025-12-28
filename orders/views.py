import hashlib
import hmac
import json

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import ScopedRateThrottle

from carts.celery_tasks import process_order_after_payment
from services.models import Shipment
from .models import Order
from .pagination import OrderPagination
from .permissions import IsOwnerOrAdmin
from .serializers import OrderSerializer
from ecommerce_api.core.throttles import ComboRateThrottle  


# ---------------- ORDER LIST ----------------
class OrderListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ComboRateThrottle]  
     
    @swagger_auto_schema(
        operation_summary="List Orders",
        operation_description="List all orders for authenticated user or all orders if admin. Supports pagination.",
        responses={200: OrderSerializer(many=True)},
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
    throttle_classes = [ComboRateThrottle]  

    @swagger_auto_schema(
        operation_summary="Order Detail",
        operation_description="Retrieve details of a specific order by ID. Users can only access their own orders.",
        responses={200: OrderSerializer()},
    )
    def get(self, request, order_id):
        order = get_object_or_404(Order, id=order_id)
        self.check_object_permissions(request, order)
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ---------------- PAYSTACK WEBHOOK ----------------
class PaymentWebhookAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle] 
    throttle_scope = "paystack_webhook"      

    @swagger_auto_schema(
        operation_summary="Paystack Webhook",
        operation_description="Verifies payment and triggers order processing.",
        responses={200: "Webhook processed successfully"},
    )
    def post(self, request):
        #  Verify Paystack signature
        if not settings.DEBUG:
            signature = request.headers.get("X-Paystack-Signature")
            if not signature:
                return Response({"error": "Signature missing"}, status=400)

            computed_sig = hmac.new(
                settings.PAYSTACK_SECRET_KEY.encode(),
                msg=request.body,
                digestmod=hashlib.sha512,
            ).hexdigest()

            if not hmac.compare_digest(signature, computed_sig):
                return Response({"error": "Invalid signature"}, status=400)

        #  Parse JSON payload safely
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return Response({"error": "Invalid JSON payload"}, status=400)

        reference = payload.get("data", {}).get("reference")
        if not reference or not reference.startswith("ORD-"):
            return Response({"error": "Invalid reference"}, status=400)

        order_id = reference.replace("ORD-", "")

        #  Atomic + row-lock for idempotency
        with transaction.atomic():
            order = Order.objects.select_for_update().filter(id=order_id).first()
            if not order:
                return Response({"message": "Order not found"}, status=200)

            if order.payment_status == "paid":
                return Response({"message": "Order already paid"}, status=200)

            if payload.get("event") != "charge.success":
                return Response({"message": "Ignoring non-success event"}, status=200)

            # Mark order as paid
            order.payment_status = "paid"
            order.save(update_fields=["payment_status"])

        # Create shipment snapshot (if missing)
        if not hasattr(order, "order_shipment"):
            Shipment.objects.create(
                order=order,
                shipping_full_name=order.shipping_full_name,
                shipping_address_text=order.shipping_address_text,
                shipping_city=order.shipping_city,
                shipping_state=order.shipping_state,
                shipping_country=order.shipping_country,
                shipping_postal_code=order.shipping_postal_code,
                shipping_phone=order.shipping_phone,
                shipping_fee=order.shipping_cost,
                delivery_status="pending",
            )

        #  Trigger Celery task (once)
        process_order_after_payment.delay(
            order_id=order.id,
            user_email=order.user.email if order.user else None,
            user_id=order.user.id if order.user else None,
        )

        return Response(
            {"message": "Payment verified. Order processing started."},
            status=200,
        )
