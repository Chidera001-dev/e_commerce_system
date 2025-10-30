from rest_framework import permissions


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission:
    - Admin (is_staff=True) can access or modify any object.
    - Normal users can only access or modify objects that belong to them.
    Works for both User and Profile models.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user

        # Admins always have access
        if user and user.is_staff:
            return True

        # If the object IS the user themselves
        if obj == user:
            return True

        # If the object has a "user" attribute (e.g., Profile.user)
        if hasattr(obj, "user") and obj.user == user:
            return True

        # Otherwise, deny permission
        return False


class IsAdminUser(permissions.BasePermission):
    """
    Allow access only to admin users.
    Used for endpoints like /users/ (list/create).
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_staff)

