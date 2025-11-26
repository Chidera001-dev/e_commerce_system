from django.urls import path

from .views import (MeAPIView, ProfileDetailAPIView, UserDetailAPIView,
                    UserListCreateAPIView)

urlpatterns = [
    # ---------------- USER ROUTES ----------------
    # Admin-only: List all users or create new user
    # GET → list all users (admin only)
    # POST → create new user (admin only)
    path("users/", UserListCreateAPIView.as_view(), name="user-list-create"),
    # Admin-only: Get, update, or delete any user by UUID
    # GET/PATCH/DELETE → /users/<uuid>/
    path("users/<str:pk>/", UserDetailAPIView.as_view(), name="user-detail"),
    # Authenticated user: Get, update, or delete *their own* account
    # GET/PATCH/DELETE → /account/me/
    path("account/me/", MeAPIView.as_view(), name="me"),
    # ---------------- PROFILE ROUTES ----------------
    # Authenticated user: Get or update their own profile
    # GET/PATCH → /profiles/
    path("profiles/", ProfileDetailAPIView.as_view(), name="my-profile"),
    # Admin-only (or owner): Get or update a specific profile by UUID
    # GET/PATCH → /profiles/<uuid>/
    path("profiles/<str:uuid>/", ProfileDetailAPIView.as_view(), name="profile-detail"),
]
