from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Profile

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("email", "username", "is_staff", "is_superuser", "is_vendor", "is_active")
    list_filter = ("is_staff", "is_superuser", "is_vendor")
    search_fields = ("email", "username")
    ordering = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "username", "password")}),
        ("Roles", {"fields": ("is_vendor", "is_staff", "is_superuser", "is_active")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "address", "bio")




# Register your models here.
