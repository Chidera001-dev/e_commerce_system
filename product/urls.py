from django.urls import path
from .views import (
    ProductListCreateAPIView,
    ProductDetailAPIView,
    CategoryListAPIView
)

urlpatterns = [
    path('categories/', CategoryListAPIView.as_view(), name='category-list'),
    path('products/', ProductListCreateAPIView.as_view(), name='product-list-create'),
    path('products/<str:uuid>/', ProductDetailAPIView.as_view(), name='product-detail'),
]
