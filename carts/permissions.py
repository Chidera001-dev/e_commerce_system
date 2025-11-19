from rest_framework import permissions

class CartPermission(permissions.BasePermission):
    """
    Custom permission for cart API.
    - Authenticated users can checkout and merge cart.
    - Guest users can only read/add/update/remove items in Redis.
    """

    def has_permission(self, request, view):
        if view.__class__.__name__ in ["CheckoutAPIView", "MergeCartAPIView"]:
            return request.user and request.user.is_authenticated
        return True



