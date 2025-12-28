from rest_framework import permissions


class IsAdminOrVendor(permissions.BasePermission):
    """
    Internal API permission.

    - Admins: full access to all objects.
    - Vendors: access ONLY objects they own.
    - Regular users & anonymous users: NO access.
    """

    def has_permission(self, request, view):
        user = request.user

        # Must be authenticated
        if not user or not user.is_authenticated:
            return False

        # Only admins or vendors can access internal endpoints
        return user.is_staff or getattr(user, "is_vendor", False)

    def has_object_permission(self, request, view, obj):
        user = request.user

        # Admin can do anything
        if user.is_staff:
            return True

        # Vendor: object must belong to them
        if getattr(user, "is_vendor", False):
            return hasattr(obj, "owner") and obj.owner == user

        # Everything else is denied
        return False


class IsPublicEndpoint(permissions.BasePermission):
    """
    Public endpoints (no authentication required).
    """

    def has_permission(self, request, view):
        return True
