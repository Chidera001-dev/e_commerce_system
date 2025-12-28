from rest_framework import serializers
from reviews.serializers import ReviewSerializer
from .models import Category, Product


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description"]


class ProductSerializer(serializers.ModelSerializer):
    #  Secure ownership assignment (WRITE)
    owner = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )

    #  Human-readable owner (READ)
    owner_username = serializers.ReadOnlyField(source="owner.username")

    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="category",
        write_only=True
    )

    slug = serializers.ReadOnlyField()

    # Reviews
    reviews = ReviewSerializer(many=True, read_only=True)
    average_rating = serializers.FloatField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "owner",            
            "owner_username",  
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

        read_only_fields = [
            "id",
            "slug",
            "created_at",
            "updated_at",
        ]

    def validate_is_active(self, value):
        """
        Prevent vendors from deactivating products they don't own.
        Admins can modify freely.
        """
        user = self.context["request"].user
        if getattr(user, "is_vendor", False):
            # Only allow active status if the vendor owns the object
            if self.instance and self.instance.owner != user and not value:
                raise serializers.ValidationError(
                    "Vendors cannot deactivate products they don't own."
                )
        return value


    

