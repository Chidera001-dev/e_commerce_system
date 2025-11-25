from rest_framework import permissions


class IsAdminOrVendor(permissions.BasePermission):
    """
    Custom permission for internal API endpoints.

    - Admins can create, update, or delete any object.
    - Vendors can create objects and update/delete only those they own.
    - Regular users and unauthenticated users cannot access internal endpoints.
    """

    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        # Admins and vendors have full access
        if request.user.is_staff or getattr(request.user, "is_vendor", False):
            return True

        # Regular users CANNOT access internal endpoints
        return False

    def has_object_permission(self, request, view, obj):
        # Safe methods allowed for read (in internal admin/vendor context)
        if request.method in permissions.SAFE_METHODS:
            return True

        # Admin can modify anything
        if request.user.is_staff:
            return True

        # Vendor can modify only their own object (if owner field exists)
        if getattr(request.user, "is_vendor", False):
            if hasattr(obj, "owner"):
                return obj.owner == request.user

        # Otherwise, deny
        return False


class IsPublicEndpoint(permissions.BasePermission):
    """
    Allows unrestricted access to public endpoints.
    """

    def has_permission(self, request, view):
        return True
