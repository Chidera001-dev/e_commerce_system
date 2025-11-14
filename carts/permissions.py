from rest_framework.permissions import BasePermission

class CartPermission(BasePermission):
    """
    Allow all users (guest or authenticated) to:
    - view cart
    - add items
    - merge cart
    - checkout
    """

    def has_permission(self, request, view):
        # All actions are allowed for everyone
        return True

