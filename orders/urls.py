from django.urls import path
from .views import (
    OrderListAPIView,
    OrderDetailAPIView,
    OrderMarkShippedAPIView,
    PaymentWebhookAPIView
)

urlpatterns = [
    path("orders/", OrderListAPIView.as_view(), name="order-list"),
    path("orders/<str:order_id>/", OrderDetailAPIView.as_view(), name="order-detail"),
    path("orders/<str:order_id>/mark-shipped/", OrderMarkShippedAPIView.as_view(), name="order-mark-shipped"),
    path("orders/payment-webhook/", PaymentWebhookAPIView.as_view(), name="payment-webhook"),
]


