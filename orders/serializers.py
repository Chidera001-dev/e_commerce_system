from rest_framework import serializers
from product.serializers import ProductSerializer
from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    product_detail = ProductSerializer(source="product", read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "product_detail",
            "quantity",
            "price_snapshot",
            "subtotal",
        ]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    shipment_created = serializers.BooleanField(read_only=True)  # new field

    class Meta:
        model = Order
        fields = [
            "id",
            "user",
            "cart",
            "status",
            "payment_status",
            "payment_method",
            "transaction_id",
            "reference",
            "total",
            # Shipping fields
            "shipping_full_name",
            "shipping_phone",
            "shipping_address",
            "shipping_city",
            "shipping_state",
            "shipping_country",
            "shipping_postal_code",
            "shipping_provider",
            "shipping_tracking_number",
            "shipping_label_url",
            "shipping_status",
            "shipping_cost",
            "shipment_created",
            # Timestamps
            "created_at",
            "updated_at",
            "items",
        ]
        read_only_fields = [
            "id",
            "total",
            "created_at",
            "updated_at",
            "items",
            "shipping_tracking_number",
            "shipping_status",
            "shipping_label_url",
            "reference",
            "transaction_id",
            "payment_status",
            "shipment_created",
        ]
