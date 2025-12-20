from django.urls import path
from reviews.views import ReviewDetailView  
from reviews.views import ReviewListCreateView


urlpatterns = [
    path("reviews/", ReviewListCreateView.as_view()),
    path("reviews/<str:pk>/", ReviewDetailView.as_view()),
]
