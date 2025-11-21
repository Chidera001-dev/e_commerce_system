from django.contrib import admin
from .models import Order, OrderItem

# Inline for OrderItem in the Order admin
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    readonly_fields = ('product', 'quantity', 'price_snapshot', 'subtotal')
    fields = ('product', 'quantity', 'price_snapshot', 'subtotal')
    extra = 0
    can_delete = False

# Admin for Order
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'total', 'status', 'payment_status', 'created_at', 'updated_at')
    list_filter = ('status', 'payment_status', 'created_at', 'updated_at')
    search_fields = ('id', 'user__username', 'user__email', 'transaction_id')
    readonly_fields = ('total', 'created_at', 'updated_at')
    inlines = [OrderItemInline]

    def get_readonly_fields(self, request, obj=None):
        """
        Make all fields readonly once order is created
        """
        if obj:  # editing an existing order
            return self.readonly_fields + ('user', 'status', 'payment_status', 'payment_method', 'transaction_id')
        return self.readonly_fields


# Register your models here.
