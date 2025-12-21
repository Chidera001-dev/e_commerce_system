from rest_framework import serializers

from reviews.serializers import ReviewSerializer

from .models import Category, Product


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description"]


class ProductSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source="owner.username")
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source="category", write_only=True
    )
    slug = serializers.ReadOnlyField()  # slug as read-only

    # Add reviews and average_rating here
    reviews = ReviewSerializer(many=True, read_only=True)
    average_rating = serializers.FloatField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "owner",
            "category",
            "category_id",
            "slug",
            "name",
            "description",
            "price",
            "stock",
            "image",
            "is_active",
            "created_at",
            "updated_at",
            "reviews",
            "average_rating",
        ]

    read_only_fields = ["id", "owner", "slug", "created_at", "updated_at"]
    

