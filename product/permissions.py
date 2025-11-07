from rest_framework import permissions

class IsAdminOrVendor(permissions.BasePermission):
    """
    Only admin or vendor users can create or modify products.
    Normal users can only view products.
    """

    def has_permission(self, request, view):
        # Allow GET for everyone
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Allow create/update/delete only for admins or vendors
        return request.user.is_staff or getattr(request.user, 'is_vendor', False)

    def has_object_permission(self, request, view, obj):
        # Allow read-only access for everyone
        if request.method in permissions.SAFE_METHODS:
            return True

        # Allow write access for admins or owners
        return request.user.is_staff or obj.owner == request.user
