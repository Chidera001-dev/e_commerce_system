from rest_framework import permissions


class IsOwnerOrAdmin(permissions.BasePermission):
    """Allow access only to object owner or admin."""

    def has_object_permission(self, request, view, obj):
        return request.user.is_staff or obj == request.user or getattr(obj, "user", None) == request.user


class IsAdminUser(permissions.BasePermission):
    """Allow only admin users."""
    def has_permission(self, request, view):
        return request.user and request.user.is_staff
