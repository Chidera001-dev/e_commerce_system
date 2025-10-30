from django.urls import path, include
from .views import (
    UserListCreateAPIView,
    UserDetailAPIView,
    MeAPIView,
    ProfileDetailAPIView,
)

urlpatterns = [
    # User management
    path("users/", UserListCreateAPIView.as_view(), name="user-list-create"),
    path("users/<str:pk>/", UserDetailAPIView.as_view(), name="user-detail"),

    # Current authenticated user
    path("users/me/", MeAPIView.as_view(), name="me"),

    # Profile management
    path("profiles/", ProfileDetailAPIView.as_view(), name="my-profile"),
    path("profiles/<str:uuid>/", ProfileDetailAPIView.as_view(), name="profile-detail"),

    
]



