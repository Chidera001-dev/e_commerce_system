from rest_framework import serializers
from .models import Review
from orders.models import OrderItem


class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Review
        fields = [
            "id",
            "user",
            "product",
            "order",
            "rating",
            "comment",
            "created_at",
        ]
        read_only_fields = ["id", "user", "created_at"]

    def validate(self, attrs):
        request = self.context["request"]
        user = request.user
        order = attrs["order"]
        product = attrs["product"]

        #  Order must belong to user
        if order.user != user:
            raise serializers.ValidationError("This order does not belong to you.")

        #  Order must be delivered
        if order.status != "delivered":
            raise serializers.ValidationError(
                "You can only review products after delivery."
            )

        #  Product must exist in order items
        if not OrderItem.objects.filter(order=order, product=product).exists():
            raise serializers.ValidationError(
                "This product was not part of the selected order."
            )

        return attrs

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)
