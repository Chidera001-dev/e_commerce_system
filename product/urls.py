from django.urls import path
from .views import (
    # Category Views
    PublicCategoryListAPIView,
    PublicCategoryDetailAPIView,
    CategoryListCreateAPIView,
    CategoryDetailAPIView,
    # Product Views
    PublicProductListAPIView,
    PublicProductDetailAPIView,
    ProductListCreateAPIView,
    ProductDetailAPIView,
)

urlpatterns = [

    # ---------------------- PUBLIC CATEGORY ----------------------
    path("public/categories/", PublicCategoryListAPIView.as_view(), name="public-category-list"),
    path("public/categories/<slug:slug>/", PublicCategoryDetailAPIView.as_view(), name="public-category-detail"),

    # ---------------------- ADMIN/VENDOR CATEGORY ----------------------
    path("categories/", CategoryListCreateAPIView.as_view(), name="category-list-create"),
    path("categories/<str:id>/", CategoryDetailAPIView.as_view(), name="category-detail"),

    # ---------------------- PUBLIC PRODUCT ----------------------
    path("public/products/", PublicProductListAPIView.as_view(), name="public-product-list"),
    path("public/products/<slug:slug>/", PublicProductDetailAPIView.as_view(), name="public-product-detail"),

    # ---------------------- ADMIN/VENDOR PRODUCT ----------------------
    path("products/", ProductListCreateAPIView.as_view(), name="product-list-create"),
    path("products/<str:id>/", ProductDetailAPIView.as_view(), name="product-detail"),
]
