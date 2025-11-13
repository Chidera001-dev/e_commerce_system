from rest_framework import permissions

class IsAdminOrVendor(permissions.BasePermission):
    """
    Custom permission for e-commerce app:

    - Admins can create, update, or delete any object.
    - Vendors can create objects and update/delete only those they own.
    - Public users cannot use internal APIs (only public read views).
    """

    def has_permission(self, request, view):
        # User must be authenticated for internal API access
        if not request.user or not request.user.is_authenticated:
            return False

        # Safe methods (GET, HEAD, OPTIONS) allowed for read operations
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions allowed for Admins or Vendors only
        return request.user.is_staff or getattr(request.user, "is_vendor", False)

    def has_object_permission(self, request, view, obj):
        # Allow read-only access for safe methods
        if request.method in permissions.SAFE_METHODS:
            return True

        # Admin can modify any object
        if request.user.is_staff:
            return True

        # Vendor can modify only their own object
        # Check for 'owner' attribute (Product/Category)
        if getattr(request.user, "is_vendor", False):
            if hasattr(obj, "owner"):
                return obj.owner == request.user
            return False  # no owner field found — deny edit

        # Otherwise, deny permission
        return False




