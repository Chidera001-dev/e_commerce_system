from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from services.shipping_service import calculate_shipping_fee, create_shipment_label

from .models import Shipment, ShippingAddress
from .pagination import ServiceOffsetPagination
from .permissions import IsOwnerOrReadOnly
from .serializers import ShipmentSerializer, ShippingAddressSerializer


# -------------------------------
# Shipping Address Views
# -------------------------------
class ShippingAddressListCreateAPIView(generics.ListCreateAPIView):
    """
    List all shipping addresses or create a new one for the authenticated user.
    """

    serializer_class = ShippingAddressSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = ServiceOffsetPagination

    def get_queryset(self):
        return ShippingAddress.objects.filter(order__user=self.request.user).order_by(
            "-created_at"
        )

    def perform_create(self, serializer):
        serializer.save()


class ShippingAddressDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a shipping address.
    """

    serializer_class = ShippingAddressSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    lookup_field = "id"

    def get_queryset(self):
        return ShippingAddress.objects.filter(order__user=self.request.user)


# -------------------------------
# Shipment Views
# -------------------------------
class ShipmentListAPIView(generics.ListAPIView):
    """
    List all shipments for the authenticated user.
    """

    serializer_class = ShipmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = ServiceOffsetPagination

    def get_queryset(self):
        return Shipment.objects.filter(order__user=self.request.user).order_by(
            "-created_at"
        )


class ShipmentDetailAPIView(generics.RetrieveAPIView):
    """
    Retrieve shipment details by ID.
    """

    serializer_class = ShipmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    lookup_field = "id"

    def get_queryset(self):
        return Shipment.objects.filter(order__user=self.request.user)


class ShipmentStatusUpdateAPIView(APIView):
    """
    Update shipment status (e.g., via Shippo webhook or user update if allowed).
    """

    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Update Shipment Status",
        operation_description="Update the delivery_status, tracking_number, or estimated_delivery_date of a shipment.",
    )
    def post(self, request, shipment_id):
        try:
            shipment = Shipment.objects.get(id=shipment_id)
        except Shipment.DoesNotExist:
            return Response(
                {"error": "Shipment not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Only owner can update
        if shipment.order.user != request.user:
            return Response(
                {"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN
            )

        # Allowed fields
        allowed_fields = [
            "delivery_status",
            "tracking_number",
            "estimated_delivery_date",
            "courier_name",
        ]
        for field in allowed_fields:
            if field in request.data:
                setattr(shipment, field, request.data[field])

        shipment.save()
        return Response(
            {
                "status": "Shipment updated",
                "shipment": ShipmentSerializer(shipment).data,
            },
            status=status.HTTP_200_OK,
        )


# -------------------------------
# Shippo Integration Example
# -------------------------------
class CreateShipmentLabelAPIView(APIView):
    """
    Create a shipment label via Shippo API and update Shipment record.
    """

    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Create Shipment Label",
        operation_description="Generate shipment label using Shippo and attach label URL to shipment.",
    )
    def post(self, request, shipment_id):
        try:
            shipment = Shipment.objects.get(id=shipment_id)
        except Shipment.DoesNotExist:
            return Response(
                {"error": "Shipment not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if shipment.order.user != request.user:
            return Response(
                {"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN
            )

        # Call Shippo helper
        label_url, tracking_number, estimated_delivery = create_shipment_label(shipment)
        shipment.shipping_fee = calculate_shipping_fee(shipment)
        shipment.tracking_number = tracking_number
        shipment.estimated_delivery_date = estimated_delivery
        shipment.save()

        return Response(
            {
                "status": "Shipment label created",
                "shipment": ShipmentSerializer(shipment).data,
            },
            status=status.HTTP_200_OK,
        )


# Create your views here.
