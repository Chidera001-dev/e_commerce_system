
from rest_framework.permissions import BasePermission

class IsAuthenticatedOrGuest(BasePermission):
    """
    Allow all users to view and add items,
    but only authenticated users can perform checkout.
    """

    def has_permission(self, request, view):
        # Allow list/add_item/merge_cart for everyone
        if view.action in ["list", "add_item", "merge_cart"]:
            return True
        # Only authenticated users for checkout
        if view.action == "checkout":
            return request.user and request.user.is_authenticated
        return False
