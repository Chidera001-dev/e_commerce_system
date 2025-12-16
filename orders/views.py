import hashlib
import hmac
import json

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from paystackapi.paystack import Paystack
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from carts.celery_tasks import process_order_after_payment
from carts.models import Cart
from services.models import Shipment

from .models import Order
from .pagination import OrderPagination
from .permissions import IsOwnerOrAdmin
from .serializers import OrderSerializer
from .utils import initialize_transaction, verify_transaction

paystack = Paystack(secret_key=settings.PAYSTACK_SECRET_KEY)


# ---------------- ORDER LIST ----------------
class OrderListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

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

        payload = json.loads(request.body)
        reference = payload.get("data", {}).get("reference")

        if not reference or not reference.startswith("ORD-"):
            return Response({"error": "Invalid reference"}, status=400)

        order_id = reference.replace("ORD-", "")

        #  ATOMIC + ROW LOCK = STRONG IDEMPOTENCY
        with transaction.atomic():
            order = Order.objects.select_for_update().filter(id=order_id).first()

            if not order:
                return Response({"message": "Order not found"}, status=200)

            if order.payment_status == "paid":
                return Response({"message": "Order already paid"}, status=200)

            #  Verify payment success
            if payload.get("event") != "charge.success":
                return Response({"message": "Ignoring non-success event"}, status=200)

            #  Mark payment as PAID immediately
            order.payment_status = "paid"
            order.save(update_fields=["payment_status"])

        #  Create shipment snapshot (outside lock)
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

        #  Trigger Celery ONCE
        process_order_after_payment.delay(
            order_id=order.id,
            user_email=order.user.email if order.user else None,
            user_id=order.user.id if order.user else None,
        )

        return Response(
            {"message": "Payment verified. Order processing started."},
            status=200,
        )
