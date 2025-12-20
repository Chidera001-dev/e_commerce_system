from django.contrib import admin
from django.contrib import admin
from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "product",
        "user",
        "rating",
        "is_approved",
        "is_deleted",
        "created_at",
    )
    list_filter = ("is_approved", "is_deleted", "rating", "created_at")
    search_fields = ("product__name", "user__username", "comment")
    readonly_fields = ("id", "user", "product", "order", "created_at")

    actions = ["soft_delete_reviews", "approve_reviews"]

    def soft_delete_reviews(self, request, queryset):
        queryset.update(is_deleted=True)
        self.message_user(request, "Selected reviews have been soft-deleted.")
    soft_delete_reviews.short_description = "Soft delete selected reviews"

    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)
        self.message_user(request, "Selected reviews have been approved.")
    approve_reviews.short_description = "Approve selected reviews"

    # Prevent admin from editing reviews directly
    def has_change_permission(self, request, obj=None):
        return False  # admin cannot edit reviews


# Register your models here.
