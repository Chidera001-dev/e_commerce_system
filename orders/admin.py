from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    readonly_fields = ('product', 'quantity', 'price_snapshot', 'subtotal')
    fields = ('product', 'quantity', 'price_snapshot', 'subtotal')
    extra = 0
    can_delete = False

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'cart', 'total', 'status', 'payment_status', 'created_at', 'updated_at')
    list_filter = ('status', 'payment_status', 'created_at', 'updated_at')
    search_fields = ('id', 'user__username', 'user__email', 'transaction_id')
    readonly_fields = ('cart', 'total', 'created_at', 'updated_at')
    inlines = [OrderItemInline]

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + (
                'user', 'status', 'payment_status',
                'payment_method', 'transaction_id', 'cart'
            )
        return self.readonly_fields


# Register your models here.
