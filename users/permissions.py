from rest_framework import permissions


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission for object-level control.

    - Admins (is_staff=True) can access or modify ANY object.
    - Normal users can only access or modify objects that belong to them.
    Works for both `User` and `Profile` models.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user

        # Allow admins to access everything
        if user and user.is_staff:
            return True

        # If the object IS the requesting user (e.g., User instance)
        if obj == user:
            return True

        # If the object has a related 'user' field (e.g., Profile.user)
        if hasattr(obj, "user") and obj.user == user:
            return True

        # Otherwise, deny permission
        return False


class IsAdminUser(permissions.BasePermission):
    """
    Permission for admin-only access.

    Allows access only if the user is authenticated and is_staff=True.
    Useful for admin endpoints like:
      - /users/
      - /users/<uuid>/
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_staff)


class IsAuthenticatedUser(permissions.BasePermission):
    """
    Simple permission for authenticated users only.
    Used for /users/me/ endpoints.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

