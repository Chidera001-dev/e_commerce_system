from django.contrib import admin
from django.contrib import admin
from .models import Product, Category

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "category", "owner", "is_active", "created_at")
    search_fields = ("name", "description")
    list_filter = ("category", "is_active", "created_at")

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}


# Register your models here.
