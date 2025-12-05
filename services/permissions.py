from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission:
    - Owners can read and edit their own objects.
    - Others have no access.
    Works for ShippingAddress (obj.user) and Shipment (obj.order.user).
    """
    def has_object_permission(self, request, view, obj):
        # Determine owner
        if hasattr(obj, "user"):
            owner = obj.user
        elif hasattr(obj, "order") and hasattr(obj.order, "user"):
            owner = obj.order.user
        else:
            return False  # Cannot determine owner, deny access

        # Owner can read or edit
        return owner == request.user


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
