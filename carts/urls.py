from django.urls import path
from .views import (
    CartListAPIView, AddItemAPIView, UpdateItemAPIView,
    RemoveItemAPIView, MergeCartAPIView, CheckoutAPIView
)

urlpatterns = [
    path("cart/", CartListAPIView.as_view(), name="cart-list"),
    path("cart/add/", AddItemAPIView.as_view(), name="cart-add"),
    path("cart/update/", UpdateItemAPIView.as_view(), name="cart-update"),
    path("cart/remove/", RemoveItemAPIView.as_view(), name="cart-remove"),
    path("cart/merge/", MergeCartAPIView.as_view(), name="cart-merge"),
    path("cart/checkout/", CheckoutAPIView.as_view(), name="cart-checkout"),
]
