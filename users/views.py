from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import ScopedRateThrottle

from .models import Profile, User
from .permissions import IsAdminUser, IsOwnerOrAdmin
from .serializers import (
    CustomUserCreateSerializer,
    CustomUserUpdateSerializer,
    ProfileSerializer,
)

# ------------------ USER VIEWS ------------------

class UserListCreateAPIView(APIView):
    """
    Admin can list all users or create a new one.
    Normal users cannot access this endpoint.
    """
    permission_classes = [IsAdminUser]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "users_admin"  
    @swagger_auto_schema(
        operation_summary="List all users (Admin only)",
        operation_description="Allows admin users to view all registered users.",
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
    permission_classes = [IsAdminUser]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "users_admin"

    def get_object(self, pk):
        return get_object_or_404(User, pk=pk)

    @swagger_auto_schema(
        operation_summary="Get user details (Admin only)",
        operation_description="Retrieve details of a specific user using their UUID.",
        responses={200: CustomUserCreateSerializer},
    )
    def get(self, request, pk):
        user = self.get_object(pk)
        self.check_object_permissions(request, user)
        serializer = CustomUserCreateSerializer(user)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Update user details (Admin only)",
        operation_description="Partially update user details using UUID.",
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
        operation_summary="Delete user (Admin only)",
        operation_description="Allows admin or the user to delete the user account.",
        responses={204: "User deleted successfully"},
    )
    def delete(self, request, pk):
        user = self.get_object(pk)
        self.check_object_permissions(request, user)
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeAPIView(APIView):
    """
    Authenticated users can view, update, or delete their own user details.
    """
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "users_me"  

    @swagger_auto_schema(
        operation_summary="Get current user details",
        operation_description="Returns the authenticated user's information.",
        responses={200: CustomUserUpdateSerializer},
    )
    def get(self, request):
        serializer = CustomUserUpdateSerializer(request.user)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Update current user details",
        operation_description="Allows the authenticated user to partially update their own data.",
        request_body=CustomUserUpdateSerializer,
        responses={200: CustomUserUpdateSerializer},
    )
    def patch(self, request):
        serializer = CustomUserUpdateSerializer(
            request.user, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="Delete current user account",
        operation_description="Deletes the authenticated user's account.",
        responses={204: "Account deleted successfully"},
    )
    def delete(self, request):
        request.user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ------------------ PROFILE VIEWS ------------------

class ProfileDetailAPIView(APIView):
    """
    - Admin can view or update any profile (using /profiles/<uuid>/)
    - Normal users can only view or update their own profile (using /profiles/)
    """
    permission_classes = [IsOwnerOrAdmin]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "profiles" 

    def get_object(self, request, uuid=None):
        if uuid:
            if not request.user.is_staff:
                raise PermissionDenied(
                    "You do not have permission to access other users' profiles."
                )
            return get_object_or_404(Profile, user__id=uuid)
        return get_object_or_404(Profile, user=request.user)

    @swagger_auto_schema(
        operation_summary="Get profile details",
        operation_description=(
            "Retrieve a user's profile.\n\n"
            "- Normal users: `/profiles/` → Get your own profile\n"
            "- Admins: `/profiles/<uuid>/` → Get any user's profile"
        ),
        responses={200: ProfileSerializer},
    )
    def get(self, request, uuid=None):
        profile = self.get_object(request, uuid)
        self.check_object_permissions(request, profile)
        serializer = ProfileSerializer(profile)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Update profile (Admin or Owner)",
        operation_description=(
            "Update profile details.\n\n"
            "- Normal users: `/profiles/` → Update your own profile\n"
            "- Admins: `/profiles/<uuid>/` → Update any user's profile"
        ),
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
