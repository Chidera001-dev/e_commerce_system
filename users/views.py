from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import User, Profile
from .serializers import CustomUserCreateSerializer, ProfileSerializer
from .permissions import IsOwnerOrAdmin


# ------------------ USER VIEWS ------------------
class UserListCreateAPIView(APIView):
    """
    Admin can list and create users.
    Normal users are not allowed to access this endpoint.
    """
    permission_classes = [permissions.IsAdminUser]

    @swagger_auto_schema(
        operation_summary="List all users (Admin only)",
        operation_description="Allows admin users to view all registered users in the system.",
        responses={200: CustomUserCreateSerializer(many=True)},
    )
    def get(self, request):
        users = User.objects.all()
        serializer = CustomUserCreateSerializer(users, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Create a new user (Admin only)",
        operation_description="Allows admin users to create a new user account.",
        request_body=CustomUserCreateSerializer,
        responses={201: CustomUserCreateSerializer},
    )
    def post(self, request):
        serializer = CustomUserCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserDetailAPIView(APIView):
    """
    Retrieve, update, or delete a specific user.
    Only the user themselves or an admin can access this endpoint.
    """
    permission_classes = [IsOwnerOrAdmin]

    def get_object(self, pk):
        return get_object_or_404(User, pk=pk)

    @swagger_auto_schema(
        operation_summary="Get user details",
        operation_description="Retrieve details of a specific user using their UUID. Only the user or admin can access this.",
        responses={200: CustomUserCreateSerializer},
    )
    def get(self, request, pk):
        user = self.get_object(pk)
        self.check_object_permissions(request, user)
        serializer = CustomUserCreateSerializer(user)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Update user details (partial)",
        operation_description="Allows the user or an admin to partially update user details using their UUID.",
        request_body=CustomUserCreateSerializer,
        responses={200: CustomUserCreateSerializer},
    )
    def patch(self, request, pk):
        user = self.get_object(pk)
        self.check_object_permissions(request, user)
        serializer = CustomUserCreateSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="Delete a user",
        operation_description="Allows admin or the user themselves to delete a user account.",
        responses={204: "User deleted successfully"},
    )
    def delete(self, request, pk):
        user = self.get_object(pk)
        self.check_object_permissions(request, user)
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeAPIView(APIView):
    """
    Authenticated users can view their own user details.
    """
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get current user details",
        operation_description="Returns the authenticated user's own information.",
        responses={200: CustomUserCreateSerializer},
    )
    def get(self, request):
        serializer = CustomUserCreateSerializer(request.user)
        return Response(serializer.data)


# ------------------ PROFILE VIEWS ------------------
class ProfileDetailAPIView(APIView):
    """
    - Admin can view or update any profile.
    - Normal users can only view or update their own profile.
    """
    permission_classes = [IsOwnerOrAdmin]

    def get_object(self, request, uuid=None):
        user = request.user
        if user.is_staff and uuid:
            return get_object_or_404(Profile, pk=uuid)
        return get_object_or_404(Profile, user=user)

    @swagger_auto_schema(
        operation_summary="Get user profile",
        operation_description="Retrieve profile details by UUID. Normal users can only access their own profile.",
        responses={200: ProfileSerializer},
    )
    def get(self, request, uuid=None):
        profile = self.get_object(request, uuid)
        self.check_object_permissions(request, profile)
        serializer = ProfileSerializer(profile)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Update user profile (partial)",
        operation_description="Allows users to update their own profile, or admins to update any profile.",
        request_body=ProfileSerializer,
        responses={200: ProfileSerializer},
    )
    def patch(self, request, uuid=None):
        profile = self.get_object(request, uuid)
        self.check_object_permissions(request, profile)
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)





# Create your views here.
