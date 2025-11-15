from rest_framework.permissions import BasePermission

class CartPermission(BasePermission):
    """
    Permissions for cart operations.

    Allows:
    - Guests and authenticated users to view their cart
    - Add items to the cart
    - Merge guest cart into user cart
    - Checkout (requires login if needed)
    """

    def has_permission(self, request, view):
        # Allow everyone to access cart endpoints
        return True


