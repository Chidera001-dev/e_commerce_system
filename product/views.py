from rest_framework import generics, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Product, Category
from .serializers import ProductSerializer, CategorySerializer
from .permissions import IsAdminOrVendor
from .filters import ProductFilter


# ---------------------- CATEGORY VIEWS ----------------------

# Public: list all categories
class PublicCategoryListAPIView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]  # Anyone can view


# Public: retrieve category by slug
class PublicCategoryDetailAPIView(generics.RetrieveAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = "slug"  # Users retrieve via slug
    permission_classes = [permissions.AllowAny]


# Admin/Vendor: list or create categories (internal)
class CategoryListCreateAPIView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrVendor]  # Only admin/vendor can write

    def perform_create(self, serializer):
        serializer.save()


# Admin/Vendor: retrieve/update/delete category via short UUID
class CategoryDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = "id"  # internal UUID
    permission_classes = [IsAdminOrVendor]


# ---------------------- PRODUCT VIEWS ----------------------

# Public: list products with filters/search
class PublicProductListAPIView(generics.ListAPIView):
    queryset = Product.objects.filter(is_active=True).order_by('-created_at')
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at']


# Public: retrieve product by slug
class PublicProductDetailAPIView(generics.RetrieveAPIView):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    lookup_field = "slug"
    permission_classes = [permissions.AllowAny]


# Admin/Vendor: list/create products (internal)
class ProductListCreateAPIView(generics.ListCreateAPIView):
    queryset = Product.objects.all().order_by('-created_at')
    serializer_class = ProductSerializer
    permission_classes = [IsAdminOrVendor]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at']

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


# Admin/Vendor: retrieve/update/delete product via short UUID
class ProductDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    lookup_field = "id"  # internal UUID
    permission_classes = [IsAdminOrVendor]



# Create your views here.
