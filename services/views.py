from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from django.core.mail import send_mail

from .models import Shipment, ShippingAddress
from .serializers import ShipmentSerializer, ShippingAddressSerializer
from .pagination import ServiceOffsetPagination
from .permissions import IsOwnerOrReadOnly , IsAdminOrReadOnly
from .shipping_service import calculate_shipping_fee, create_shipment_label

# -------------------------------
# Shipping Address Views
# -------------------------------
class ShippingAddressListCreateAPIView(generics.ListCreateAPIView):
    """
    List all shipping addresses or create a new one for the authenticated user.
    Users can create multiple addresses; one of them will be used at checkout.
    """
    serializer_class = ShippingAddressSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = ServiceOffsetPagination

    def get_queryset(self):
        # List all shipping addresses belonging to the authenticated user
            return ShippingAddress.objects.filter(user=self.request.user).order_by("-created_at")


    def perform_create(self, serializer):
        """
        Save the shipping address. It doesn't need to be attached to an order yet;
        the checkout will pick an existing address by its ID.
        """
        serializer.save()


class ShippingAddressDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a shipping address.
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
    Update shipment status (e.g., via webhook or manually by the owner).
    """
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Update Shipment Status",
        operation_description="Update delivery status, tracking number, or estimated delivery date.",
    )
    def post(self, request, shipment_id):
        try:
            shipment = Shipment.objects.get(id=shipment_id)
        except Shipment.DoesNotExist:
            return Response({"error": "Shipment not found"}, status=status.HTTP_404_NOT_FOUND)

        if shipment.order.user != request.user:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        allowed_fields = ["delivery_status", "tracking_number", "estimated_delivery_date", "courier_name"]
        for field in allowed_fields:
            if field in request.data:
                setattr(shipment, field, request.data[field])

        shipment.save()
        return Response(
            {"status": "Shipment updated", "shipment": ShipmentSerializer(shipment).data},
            status=status.HTTP_200_OK,
        )

# Create Shipment Label View
class CreateShipmentLabelAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    @swagger_auto_schema(
        operation_summary="Create Shipment Label",
        operation_description="Generate a shipping label and send email notification to the user.",
    )

    def post(self, request, shipment_id):
        try:
            shipment = Shipment.objects.get(id=shipment_id)
        except Shipment.DoesNotExist:
            return Response({"error": "Shipment not found"}, status=404)

        if shipment.order.payment_status != "paid":
            return Response({"error": "Cannot create shipment for unpaid order"}, status=400)

        try:
            label_url, tracking_number, estimated_delivery = create_shipment_label(shipment)
            shipment.shipping_label_url = label_url
            shipment.shipping_tracking_number = tracking_number
            shipment.estimated_delivery_date = estimated_delivery
            shipment.shipping_status = "in_transit"
            shipment.save()

            # Send email
            user_email = shipment.order.user.email if shipment.order.user else None
            if user_email:
                items_list = "\n".join([f"{i.product.name} x {i.quantity} = ₦{i.subtotal}" for i in shipment.order.items.all()])
                message = f"""
Hi {shipment.order.user.username if shipment.order.user else 'Customer'},

Your order has been shipped!

Order ID: {shipment.order.id}
Tracking Number: {shipment.shipping_tracking_number}
Courier: {shipment.shipping_provider or 'Shippo'}
Estimated Delivery: {shipment.estimated_delivery_date or 'Not available'}

Items:
{items_list}

Shipping Address:
{shipment.shipping_full_name}
{shipment.shipping_address_text}, {shipment.shipping_city}, {shipment.shipping_state}, {shipment.shipping_country}
Postal Code: {shipment.shipping_postal_code}

Thank you for shopping with us!
"""
                send_mail(subject=f"Your Order {shipment.order.id} Has Been Shipped!",
                          message=message,
                          from_email="no-reply@shop.com",
                          recipient_list=[user_email],
                          fail_silently=False)

        except Exception as e:
            return Response({"error": f"Failed to create shipment label or send email: {str(e)}"}, status=500)

        return Response({"status": "Shipment label created and email sent", "shipment": ShipmentSerializer(shipment).data}, status=200)