from djoser.serializers import UserCreateSerializer
from rest_framework import serializers
from .models import User, Profile


# Extend Djoser serializer to add phone_number
class CustomUserCreateSerializer(UserCreateSerializer):
    phone_number = serializers.CharField(required=True)

    class Meta(UserCreateSerializer.Meta):
        model = User
        fields = ('id', 'email', 'username', 'password', 'phone_number')
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        # Create user with default behavior
        user = super().create(validated_data)
        return user
    
# For viewing or updating user info (used in /users/me/)
class CustomUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'phone_number')
        read_only_fields = ('id', 'email')  # email can't be changed 


# Profile serializer for profile update
class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['id', 'address', 'avatar', 'bio']

