from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404

from .models import Shipment, ShippingAddress
from .serializers import ShipmentSerializer, ShippingAddressSerializer
from .pagination import ServiceOffsetPagination
from .permissions import IsOwnerOrReadOnly, IsAdminOrReadOnly
from .shipping_service import calculate_shipping_fee, create_shipment_label


# -------------------------------
# Shipping Address Views
# -------------------------------
class ShippingAddressListCreateAPIView(generics.ListCreateAPIView):
    """
    List all shipping addresses for the authenticated user, or create a new one.
    Only the owner can list/create.
    """
    serializer_class = ShippingAddressSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    pagination_class = ServiceOffsetPagination

    def get_queryset(self):
        return ShippingAddress.objects.filter(user=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ShippingAddressDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a shipping address.
    Only the owner can modify; read-only for others.
    """
    serializer_class = ShippingAddressSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    lookup_field = "id"

    def get_queryset(self):
        return ShippingAddress.objects.filter(user=self.request.user)


# -------------------------------
# Shipment Views
# -------------------------------
class ShipmentListAPIView(generics.ListAPIView):
    """
    List shipments:
    - Admins see all shipments.
    - Regular users see only their own shipments.
    """
    serializer_class = ShipmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = ServiceOffsetPagination

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Shipment.objects.all().order_by("-created_at")
        return Shipment.objects.filter(order__user=user).order_by("-created_at")


class ShipmentDetailAPIView(generics.RetrieveAPIView):
    """
    Read shipment details. 
    Accessible to both admins and order owners; owners are read-only.
    """
    serializer_class = ShipmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    lookup_field = "id"

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Shipment.objects.all()
        return Shipment.objects.filter(order__user=user)


class ShipmentStatusUpdateAPIView(APIView):
    """
    Only admins can update shipment status.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]

    @swagger_auto_schema(
        operation_summary="Update Shipment Status",
        operation_description="Admins can update delivery status, tracking number, estimated delivery date, or courier name."
    )
    def post(self, request, shipment_id):
        shipment = get_object_or_404(Shipment, id=shipment_id)

        if not request.user.is_staff:
            return Response(
                {"error": "Permission denied: Only admins can update shipment details."},
                status=status.HTTP_403_FORBIDDEN
            )

        allowed_fields = ["delivery_status", "tracking_number", "estimated_delivery_date", "courier_name"]
        for field in allowed_fields:
            if field in request.data:
                setattr(shipment, field, request.data[field])

        shipment.save()
        return Response(
            {"status": "Shipment updated", "shipment": ShipmentSerializer(shipment).data},
            status=status.HTTP_200_OK
        )


class CreateShipmentLabelAPIView(APIView):
    """
    Admins can generate shipment labels for US orders.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]

    @swagger_auto_schema(
        operation_summary="Create Shipment Label",
        operation_description="Generate a shipping label, download PDF, and notify customer."
    )
    def post(self, request, shipment_id):
        shipment = get_object_or_404(Shipment, id=shipment_id)
        order = shipment.order

        if order.payment_status != "paid":
            return Response({"error": "Cannot create shipment for unpaid order."}, status=status.HTTP_400_BAD_REQUEST)

        if order.shipping_country != "US":
            return Response({"error": "Shipping label creation is restricted to US-only shipments."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            label_data = create_shipment_label(order=order, shipment=shipment)
            shipment.shipping_label_url = label_data.get("label_url")
            shipment.shipping_tracking_number = label_data.get("tracking_number")
            shipment.delivery_status = label_data.get("status", "in_transit")
            shipment.courier_name = label_data.get("carrier", "Shippo")
            shipment.label_created = True
            shipment.save()
        except Exception as e:
            return Response({"error": f"Failed to create shipment label: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Notify customer
        user = order.user
        if user and user.email:
            currency_symbol = "₦" if getattr(order, "currency", "NGN").upper() == "NGN" else "$"
            items_list = "\n".join([f"• {item.product.name} x{item.quantity} — {currency_symbol}{item.subtotal}" for item in order.items.all()])
            email_body = f"""
Hello {user.username},

Your order has been shipped!

Order ID: {order.id}
Tracking Number: {shipment.shipping_tracking_number}
Courier: {shipment.courier_name}
Shipping Label: {shipment.shipping_label_url}

Items:
{items_list}

Shipping To:
{order.shipping_full_name}
{order.shipping_address_text}
{order.shipping_city}, {order.shipping_state}, {order.shipping_country}
Postal Code: {order.shipping_postal_code}

Thank you for shopping with us!
            """
            send_mail(subject=f"Your Order #{order.id} Has Been Shipped", message=email_body,
                      from_email="no-reply@shop.com", recipient_list=[user.email], fail_silently=False)

        return Response({"status": "Shipment label generated successfully and customer notified.", "shipment": ShipmentSerializer(shipment).data}, status=status.HTTP_200_OK)
