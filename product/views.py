from rest_framework import status, permissions, filters, generics
from rest_framework.views import APIView 
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from django_filters.rest_framework import DjangoFilterBackend
from .models import Product, Category
from .serializers import ProductSerializer, CategorySerializer
from .permissions import IsAdminOrVendor
from .filters import ProductFilter
from rest_framework.pagination import LimitOffsetPagination


# ---------------------- CATEGORY VIEWS ----------------------

class PublicCategoryListAPIView(APIView):
    """
    Public: list all categories
    """
    permission_classes = [permissions.AllowAny]

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
    """
    Public: retrieve category by slug
    """
    permission_classes = [permissions.AllowAny]

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
    """
    Admin/Vendor: list or create categories (internal)
    """
    permission_classes = [IsAdminOrVendor]

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
    """
    Admin/Vendor: retrieve/update/delete category via UUID (internal)
    """
    permission_classes = [IsAdminOrVendor]

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
    """
    Public endpoint:
    List all active products with filter, search, and ordering support.
    Example:
        /api/public/products/?category=clothing
        /api/public/products/?search=iphone
        /api/public/products/?ordering=-price
    """
    
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at']
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        return Product.objects.filter(is_active=True)

    @swagger_auto_schema(
        operation_summary="List products (public)",
        operation_description="Anyone can view available products.",
        responses={200: ProductSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class PublicProductDetailAPIView(APIView):
    """
    Public: retrieve product by slug
    """
    permission_classes = [permissions.AllowAny]

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
    """
    Admin/Vendor: list or create products (internal)
    """
    permission_classes = [IsAdminOrVendor]

    @swagger_auto_schema(
        operation_summary="List products (admin/vendor)",
        operation_description="Admins/Vendors can view all products internally.",
        responses={200: ProductSerializer(many=True)},
    )
    def get(self, request):
        products = Product.objects.all().order_by('-created_at')
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
    """
    Admin/Vendor: retrieve/update/delete product via UUID (internal)
    """
    permission_classes = [IsAdminOrVendor]

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



# Create your views here.
