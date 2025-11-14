from rest_framework.exceptions import ValidationError
import django_filters
from .models import Product

class ProductFilter(django_filters.FilterSet):

    # Filter by category slug
    category = django_filters.CharFilter(
        field_name="category__slug",
        lookup_expr="iexact"
    )

    # Filter by owner username
    owner = django_filters.CharFilter(
        field_name="owner__username",
        lookup_expr="iexact"
    )

    # Filter by product name (case-insensitive contains)
    name = django_filters.CharFilter(
        field_name="name",
        lookup_expr="icontains"
    )

    # Price range filters
    min_price = django_filters.NumberFilter(
        field_name="price",
        lookup_expr="gte"
    )
    max_price = django_filters.NumberFilter(
        field_name="price",
        lookup_expr="lte"
    )

    # Stock availability: only items with stock > 0
    in_stock = django_filters.BooleanFilter(
        method="filter_in_stock"
    )
    def filter_in_stock(self, queryset, name, value):
        if value:
            return queryset.filter(stock__gt=0)
        return queryset

    # Created date range filters
    created_after = django_filters.DateTimeFilter(
        field_name="created_at",
        lookup_expr="gte"
    )
    created_before = django_filters.DateTimeFilter(
        field_name="created_at",
        lookup_expr="lte"
    )

    # Updated date range filters
    updated_after = django_filters.DateTimeFilter(
        field_name="updated_at",
        lookup_expr="gte"
    )
    updated_before = django_filters.DateTimeFilter(
        field_name="updated_at",
        lookup_expr="lte"
    )
  

    class Meta:
        model = Product
        fields = [
            "category",
            "owner",
            "name",
            "min_price",
            "max_price",
            "in_stock",
            "created_after",
            "created_before",
            "updated_after",
            "updated_before",
            "is_active",
        ]

    def __init__(self, data=None, queryset=None, *args, **kwargs):
        if data:
            # allow DRF filters like 'ordering' and 'search'
            allowed_extras = {'ordering', 'search', 'limit', 'offset', 'page'}
            unknown_params = set(data.keys()) - set(self.get_filters().keys()) - allowed_extras
            if unknown_params:
                raise ValidationError(f"Unknown filter parameters: {', '.join(unknown_params)}")
        super().__init__(data, queryset, *args, **kwargs)




