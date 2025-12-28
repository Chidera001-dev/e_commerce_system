from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from rest_framework import filters, generics, permissions, status
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Avg
from rest_framework.throttling import ScopedRateThrottle
from ecommerce_api.core.throttles import ComboRateThrottle

from .filters import ProductFilter
from .models import Category, Product
from .permissions import IsAdminOrVendor
from .serializers import CategorySerializer, ProductSerializer
from .services.recommendations import get_similar_products


# ---------------------- CATEGORY VIEWS ----------------------

class PublicCategoryListAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ComboRateThrottle]

    @swagger_auto_schema(
        operation_summary="List all categories (public)",
        operation_description="Anyone can view all categories.",
        responses={200: CategorySerializer(many=True)},
    )
    def get(self, request):
        categories = Category.objects.all()
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)


class PublicCategoryDetailAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ComboRateThrottle]

    @swagger_auto_schema(
        operation_summary="Get category details (public)",
        operation_description="Retrieve a category by slug for public/SEO-friendly URLs.",
        responses={200: CategorySerializer},
    )
    def get(self, request, slug):
        category = get_object_or_404(Category, slug=slug)
        serializer = CategorySerializer(category)
        return Response(serializer.data)


class CategoryListCreateAPIView(APIView):
    permission_classes = [IsAdminOrVendor]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "categories_admin"

    @swagger_auto_schema(
        operation_summary="List categories (admin/vendor)",
        operation_description="Admins/Vendors can view all categories internally.",
        responses={200: CategorySerializer(many=True)},
    )
    def get(self, request):
        categories = Category.objects.all()
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Create a category",
        operation_description="Admins/Vendors can create a new category.",
        request_body=CategorySerializer,
        responses={201: CategorySerializer},
    )
    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CategoryDetailAPIView(APIView):
    permission_classes = [IsAdminOrVendor]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "categories_admin"

    def get_object(self, id):
        return get_object_or_404(Category, id=id)

    @swagger_auto_schema(
        operation_summary="Get category details (admin/vendor)",
        operation_description="Retrieve category by internal UUID.",
        responses={200: CategorySerializer},
    )
    def get(self, request, id):
        category = self.get_object(id)
        self.check_object_permissions(request, category)
        serializer = CategorySerializer(category)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Update category (admin/vendor)",
        operation_description="Update category details by UUID.",
        request_body=CategorySerializer,
        responses={200: CategorySerializer},
    )
    def patch(self, request, id):
        category = self.get_object(id)
        self.check_object_permissions(request, category)
        serializer = CategorySerializer(category, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="Delete category (admin/vendor)",
        operation_description="Delete category by internal UUID.",
        responses={204: "Category deleted successfully"},
    )
    def delete(self, request, id):
        category = self.get_object(id)
        self.check_object_permissions(request, category)
        category.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------- PRODUCT VIEWS ----------------------

class PublicProductListAPIView(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ComboRateThrottle]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = ProductFilter
    search_fields = ["name", "description"]
    ordering_fields = ["price", "created_at"]
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        return Product.objects.filter(is_active=True)


class PublicProductDetailAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ComboRateThrottle]

    @swagger_auto_schema(
        operation_summary="Get product details (public)",
        operation_description="Retrieve product details using slug for public display.",
        responses={200: ProductSerializer},
    )
    def get(self, request, slug):
        product = get_object_or_404(Product, slug=slug, is_active=True)
        serializer = ProductSerializer(product)
        return Response(serializer.data)


class ProductListCreateAPIView(APIView):
    permission_classes = [IsAdminOrVendor]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "products_admin"

    @swagger_auto_schema(
        operation_summary="List products (admin/vendor)",
        operation_description="Admins/Vendors can view all products internally.",
        responses={200: ProductSerializer(many=True)},
    )
    def get(self, request):
        products = Product.objects.all().order_by("-created_at")
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Create a product",
        operation_description="Admins/Vendors can create a new product internally.",
        request_body=ProductSerializer,
        responses={201: ProductSerializer},
    )
    def post(self, request):
        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(owner=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductDetailAPIView(APIView):
    permission_classes = [IsAdminOrVendor]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "products_admin"

    def get_object(self, id):
        return get_object_or_404(Product, id=id)

    @swagger_auto_schema(
        operation_summary="Get product details (admin/vendor)",
        operation_description="Retrieve product by internal UUID.",
        responses={200: ProductSerializer},
    )
    def get(self, request, id):
        product = self.get_object(id)
        self.check_object_permissions(request, product)
        serializer = ProductSerializer(product)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Update product (admin/vendor)",
        operation_description="Update product details by UUID.",
        request_body=ProductSerializer,
        responses={200: ProductSerializer},
    )
    def patch(self, request, id):
        product = self.get_object(id)
        self.check_object_permissions(request, product)
        serializer = ProductSerializer(product, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="Delete product (admin/vendor)",
        operation_description="Delete product by internal UUID.",
        responses={204: "Product deleted successfully"},
    )
    def delete(self, request, id):
        product = self.get_object(id)
        self.check_object_permissions(request, product)
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ----------------- Homepage Top Recommendations -----------------

class HomepageRecommendationListView(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ComboRateThrottle]

    def get_queryset(self):
        return Product.objects.filter(is_active=True).annotate(
            avg_rating=Avg("reviews__rating")
        ).order_by("-avg_rating", "-created_at")[:6]


# ----------------- Product-Specific Recommendations -----------------

class ProductRecommendationListView(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ComboRateThrottle]

    def get_queryset(self):
        product_id = self.kwargs.get("id")
        product = get_object_or_404(Product, id=product_id)
        return get_similar_products(product)
