from django.shortcuts import render
from rest_framework import generics
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from .models import Review
from .serializers import ReviewSerializer
from .permissions import IsOwnerOrAdminDeleteOnly


class ReviewListCreateView(generics.ListCreateAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        product_id = self.request.query_params.get("product")

        queryset = Review.objects.filter(
            is_approved=True,
            is_deleted=False
        )

        if product_id:
            queryset = queryset.filter(product_id=product_id)

        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ReviewDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        IsOwnerOrAdminDeleteOnly,
    ]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Review.objects.all()

        return Review.objects.filter(
            is_approved=True,
            is_deleted=False
        )

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save()


# Create your views here.
