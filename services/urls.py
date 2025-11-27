from django.urls import path
from .views import (
    ShippingAddressListCreateAPIView,
    ShippingAddressDetailAPIView,
    ShipmentListAPIView,
    ShipmentDetailAPIView,
    ShipmentStatusUpdateAPIView,
    CreateShipmentLabelAPIView,
)

urlpatterns = [
    # -------------------------------
    # Shipping Address Endpoints
    # -------------------------------
    path(
        "shipping-addresses/",
        ShippingAddressListCreateAPIView.as_view(),
        name="shipping-address-list-create"
    ),
    path(
        "shipping-addresses/<str:id>/",
        ShippingAddressDetailAPIView.as_view(),
        name="shipping-address-detail"
    ),

    # -------------------------------
    # Shipment Endpoints
    # -------------------------------
    path(
        "shipments/",
        ShipmentListAPIView.as_view(),
        name="shipment-list"
    ),
    path(
        "shipments/<str:id>/",
        ShipmentDetailAPIView.as_view(),
        name="shipment-detail"
    ),
    path(
        "shipments/<str:shipment_id>/update-status/",
        ShipmentStatusUpdateAPIView.as_view(),
        name="shipment-update-status"
    ),
    path(
        "shipments/<str:shipment_id>/create-label/",
        CreateShipmentLabelAPIView.as_view(),
        name="shipment-create-label"
    ),
]
