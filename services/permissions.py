from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission for users to access their own shipping addresses or shipments.
    Read-only access for other users.
    """

    def has_object_permission(self, request, view, obj):
        # Safe methods (GET, HEAD, OPTIONS) allowed for owner
        if request.method in permissions.SAFE_METHODS:
            return obj.order.user == request.user if hasattr(obj, "order") else True
        
        # Editing allowed only for the owner (shipping address)
        if hasattr(obj, "order"):
            return obj.order.user == request.user
        return False

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Only admin/staff can modify objects (POST/PUT/PATCH/DELETE).
    Others have read-only access.
    """

    def has_permission(self, request, view):
        # Safe methods allowed for everyone
        if request.method in permissions.SAFE_METHODS:
            return True
        # Only staff/admin can modify
        return request.user.is_staff or request.user.is_superuser


