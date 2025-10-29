from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404

from .models import User, Profile
from .serializers import CustomUserCreateSerializer, ProfileSerializer
from .permissions import IsAdminUser, IsOwnerOrAdmin


class UserViewSet(viewsets.ModelViewSet):
    """
    Admin/staff can manage all users.
    Normal users can only see or update their own account.
    """
    queryset = User.objects.all()
    serializer_class = CustomUserCreateSerializer

    def get_permissions(self):
        # Admin-only actions (list, create, delete)
        if self.action in ["list", "create", "destroy"]:
            permission_classes = [permissions.IsAdminUser]
        # Own account actions
        elif self.action in ["retrieve", "partial_update", "update", "me"]:
            permission_classes = [IsOwnerOrAdmin]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [perm() for perm in permission_classes]

    def list(self, request, *args, **kwargs):
        """Only admin can list all users"""
        if not request.user.is_staff:
            return Response({"detail": "Not allowed."}, status=403)
        return super().list(request, *args, **kwargs)

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """Return the logged-in user's own info"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


class ProfileViewSet(viewsets.ModelViewSet):
    """
    Each user has one profile.
    - Admin can view all profiles.
    - Normal users can only view or update their own.
    """
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [IsOwnerOrAdmin]

    def get_object(self):
        """Return profile for current user if not admin"""
        user = self.request.user
        if user.is_staff:
            # Admin can access any profile by UUID
            return super().get_object()
        # Regular users only access their own profile
        return get_object_or_404(Profile, user=user)



# Create your views here.
