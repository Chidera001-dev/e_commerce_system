from rest_framework import permissions

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to allow:
    - Users to access only their own orders
    - Admins to access any order
    """

    def has_object_permission(self, request, view, obj):
        # Admins can access everything
        if request.user.is_staff:
            return True

        # Regular users can only access their own orders
        return obj.user == request.user
