from rest_framework import permissions

class IsAdminOrVendor(permissions.BasePermission):
    """
    Custom permission for e-commerce app:

    - Only authenticated users can access internal APIs.
    - Admins can create, update, delete any object.
    - Vendors can create objects and modify only their own.
    - Public users cannot use internal APIs; they only have read access via public views.
    """

    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        # Safe methods (GET, HEAD, OPTIONS) are allowed for internal read endpoints if needed
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions: only admins or vendors
        return request.user.is_staff or getattr(request.user, "is_vendor", False)

    def has_object_permission(self, request, view, obj):
        # Safe methods allowed for internal read
        if request.method in permissions.SAFE_METHODS:
            return True

        # Admins can modify any object
        if request.user.is_staff:
            return True

        # Vendors can modify only their own objects
        return getattr(request.user, "is_vendor", False) and obj.owner == request.user


