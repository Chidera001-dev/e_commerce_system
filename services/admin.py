from django.contrib import admin
from .models import Shipment, ShippingAddress


@admin.register(ShippingAddress)
class ShippingAddressAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "full_name",
        "phone",
        "city",
        "state",
        "country",
        "created_at",
        "updated_at",
    )
    search_fields = (
        "full_name",
        "phone",
        "city",
        "state",
        "country",
        "order__id",
    )
    list_filter = ("country", "state", "city", "created_at")
    readonly_fields = ("id", "created_at", "updated_at")
    fieldsets = (
    (None, {"fields": ("full_name", "phone")}),
    ("Address", {"fields": ("address", "address2", "city", "state", "postal_code", "country")}),
    ("Timestamps", {"fields": ("created_at", "updated_at")}),
)


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "shipping_method",
        "shipping_fee",
        "delivery_status",
        "tracking_number",
        "courier_name",
        "estimated_delivery_date",
        "created_at",
        "updated_at",
    )
    search_fields = ("order__id", "tracking_number", "courier_name")
    list_filter = ("delivery_status", "shipping_method", "courier_name", "created_at")
    readonly_fields = ("id", "created_at", "updated_at", "tracking_number", "courier_name", "estimated_delivery_date")

    fieldsets = (
        (None, {"fields": ("order", "shipping_method", "shipping_fee")}),
        ("Status & Tracking", {"fields": ("delivery_status", "tracking_number", "courier_name", "estimated_delivery_date")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


# Register your models here.
