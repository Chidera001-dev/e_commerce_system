from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission: only the user associated with the order can view or edit shipping/shipment.
    """

    def has_object_permission(self, request, view, obj):
        # Safe methods are always allowed
        if request.method in permissions.SAFE_METHODS:
            return True

        # Only the owner of the order can modify
        return hasattr(obj, 'order') and obj.order.user == request.user
