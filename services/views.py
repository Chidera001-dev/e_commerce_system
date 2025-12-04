from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404

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
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]

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
    
class CreateShipmentLabelAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]

    @swagger_auto_schema(
        operation_summary="Create Shipment Label",
        operation_description="Generate a US-only shipping label, download the PDF, and notify the customer via email."
    )
    def post(self, request, shipment_id):
        # ---------------------------------------------------
        # 1. Retrieve Shipment
        # ---------------------------------------------------
        shipment = get_object_or_404(Shipment, id=shipment_id)
        order = shipment.order

        # ---------------------------------------------------
        # 2. Validate payment status
        # ---------------------------------------------------
        if order.payment_status != "paid":
            return Response(
                {"error": "Cannot create shipment for unpaid order."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ---------------------------------------------------
        # 3. Enforce US-only shipment
        # ---------------------------------------------------
        if order.shipping_country != "US":
            return Response(
                {"error": "Shipping label creation is restricted to US-only shipments."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ---------------------------------------------------
        # 4. Generate the label via Shippo
        # ---------------------------------------------------
        try:
            label_data = create_shipment_label(order=order, shipment=shipment)

            shipment.shipping_label_url = label_data.get("label_url")
            shipment.shipping_tracking_number = label_data.get("tracking_number")
            shipment.delivery_status = label_data.get("status", "in_transit")
            shipment.courier_name = label_data.get("carrier", "Shippo")
            shipment.label_created = True
            shipment.save()

        except Exception as e:
            return Response(
                {"error": f"Failed to create shipment label: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # ---------------------------------------------------
        # 5. Send Email Notification
        # ---------------------------------------------------
        user = order.user
        if user and user.email:
            currency_symbol = "₦" if getattr(order, "currency", "NGN").upper() == "NGN" else "$"
            items_list = "\n".join([
                f"• {item.product.name} x{item.quantity} — {currency_symbol}{item.subtotal}"
                for item in order.items.all()
            ])

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

            send_mail(
                subject=f"Your Order #{order.id} Has Been Shipped",
                message=email_body,
                from_email="no-reply@shop.com",
                recipient_list=[user.email],
                fail_silently=False,
            )

        # ---------------------------------------------------
        # 6. Success Response
        # ---------------------------------------------------
        return Response(
            {
                "status": "Shipment label generated successfully and customer notified.",
                "shipment": ShipmentSerializer(shipment).data,
            },
            status=status.HTTP_200_OK
        )