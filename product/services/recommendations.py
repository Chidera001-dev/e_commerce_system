from django.db.models import Avg
from product.models import Product

def get_similar_products(product, limit=6):
    """
    Returns similar products based on:
    - Same category
    - Excluding current product
    - Highest average rating
    """
    return (
        Product.objects.filter(category=product.category, is_active=True)
        .exclude(id=product.id)
        .annotate(avg_rating=Avg("reviews__rating"))
        .order_by("-avg_rating", "-created_at")[:limit]
    )

