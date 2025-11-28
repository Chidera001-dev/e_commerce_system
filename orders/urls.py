from django.urls import path

from .views import (
    OrderDetailAPIView,
    OrderListAPIView,
    PaymentWebhookAPIView,
)

urlpatterns = [
    path("orders/list/", OrderListAPIView.as_view(), name="order-list"),
    path(
        "orders/detail/<str:order_id>/",
        OrderDetailAPIView.as_view(),
        name="order-detail",
    ),
   
    path(
        "orders/paystack/webhook/",
        PaymentWebhookAPIView.as_view(),
        name="paystack-webhook",
    ),
]

# Register your URL patterns here.
