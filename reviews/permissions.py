from datetime import timedelta
from django.utils import timezone
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwnerOrAdminDeleteOnly(BasePermission):
    """
    - Anyone can READ
    - Owner can EDIT within 7 days
    - Owner can DELETE
    - Admin can DELETE only
    """

    def has_object_permission(self, request, view, obj):

        # READ permissions → everyone
        if request.method in SAFE_METHODS:
            return True

        # Admin (staff)
        if request.user.is_staff:
            return request.method == "DELETE"

        # Owner permissions
        if obj.user == request.user:
            if request.method == "DELETE":
                return True

            if request.method in ["PUT", "PATCH"]:
                return timezone.now() - obj.created_at <= timedelta(days=7)

        return False
