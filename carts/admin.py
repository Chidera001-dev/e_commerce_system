from django.contrib import admin

from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0  # Do not show extra empty rows
    readonly_fields = ("price_snapshot", "subtotal", "added_at")
    fields = ("product", "quantity", "price_snapshot", "subtotal", "added_at")
    can_delete = True

    def subtotal(self, obj):
        return obj.subtotal


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "is_active", "total", "created_at", "updated_at")
    list_filter = ("is_active", "created_at", "updated_at")
    search_fields = ("user__username",)
    inlines = [CartItemInline]

    readonly_fields = ("total",)

    def total(self, obj):
        return obj.total


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "cart",
        "product",
        "quantity",
        "price_snapshot",
        "subtotal",
        "added_at",
    )
    list_filter = ("added_at",)
    search_fields = ("product__name", "cart__user__username")
    readonly_fields = ("subtotal", "price_snapshot", "added_at")


# Register your models here.
