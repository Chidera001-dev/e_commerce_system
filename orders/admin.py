from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    readonly_fields = ("product", "quantity", "price_snapshot", "subtotal")
    fields = ("product", "quantity", "price_snapshot", "subtotal")
    extra = 0
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "cart",
        "total",
        "status",
        "payment_status",
        "shipping_provider",
        "shipping_status",
        "shipping_tracking_number",
        "created_at",
    )

    list_filter = (
        "status",
        "payment_status",
        "shipping_status",
        "shipping_provider",
        "created_at",
    )

    search_fields = (
        "id",
        "user__username",
        "user__email",
        "transaction_id",
        "shipping_tracking_number",
    )

    readonly_fields = (
        "cart",
        "total",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        ("Order Info", {
            "fields": ("user", "cart", "total", "status", "payment_status")
        }),
        ("Payment", {
            "fields": ("payment_method", "transaction_id")
        }),
        ("Shipping", {
            "fields": (
                "shipping_provider",
                "shipping_cost",
                "shipping_full_name",
                "shipping_phone",
                "shipping_address",
                "shipping_city",
                "shipping_state",
                "shipping_country",
                "shipping_postal_code",
                "shipping_tracking_number",
                "shipping_status",
            )
        }),
        ("Dates", {
            "fields": ("created_at", "updated_at")
        }),
    )

    inlines = [OrderItemInline]

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + (
                "user",
                "status",
                "payment_status",
                "payment_method",
                "transaction_id",
                "cart",
                "shipping_provider",
                "shipping_cost",
                "shipping_full_name",
                "shipping_phone",
                "shipping_address",
                "shipping_city",
                "shipping_state",
                "shipping_country",
                "shipping_postal_code",
                "shipping_tracking_number",
                "shipping_status",
            )
        return self.readonly_fields




# Register your models here.
