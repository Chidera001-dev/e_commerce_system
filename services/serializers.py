from rest_framework import serializers
from orders.models import Order, OrderItem
from .models import Shipment, ShippingAddress

# -------------------------------
# Order Item Serializer
# -------------------------------
class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "product_name",
            "quantity",
            "price_snapshot",
            "subtotal",
        ]

# -------------------------------
# Order Serializer
# -------------------------------
class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "user",
            "status",
            "payment_status",
            "total",
            "payment_method",
            "reference",
            "transaction_id",
            "created_at",
            "updated_at",
            "items",
        ]
        read_only_fields = [
            "total",
            "created_at",
            "updated_at",
            "reference",
            "transaction_id",
        ]

# -------------------------------
# Shipping Address Serializer
# -------------------------------
class ShippingAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingAddress
        fields = [
            "id",
            "order",
            "full_name",
            "phone",
            "address",
            "address2",
            "city",
            "state",
            "postal_code",
            "country",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

# -------------------------------
# Shipment Serializer
# -------------------------------
class ShipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shipment
        fields = [
            "id",
            "order",
            "shipping_full_name",
            "shipping_phone",
            "shipping_address_text",
            "shipping_city",
            "shipping_state",
            "shipping_country",
            "shipping_postal_code",
            "shipping_method",
            "shipping_fee",
            "delivery_status",
            "tracking_number",
            "estimated_delivery_date",
            "courier_name",
            "label_created",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "courier_name",
            "tracking_number",
            "delivery_status",
            "label_created",
        ]
