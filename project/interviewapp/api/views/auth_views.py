"""
Authentication views for MockMate REST APIs.
"""

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..serializers.auth_serializers import (
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
)


class RegisterAPIView(APIView):
    """
    POST /api/v1/auth/register/
    Registers a new user and user profile matching application rules,
    returning user metadata and a SimpleJWT access/refresh token pair.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        user_data = UserSerializer(result["user"]).data
        return Response(
            {
                "message": "User registered successfully.",
                "user": user_data,
                "tokens": result["tokens"],
            },
            status=status.HTTP_201_CREATED,
        )


class LoginAPIView(APIView):
    """
    POST /api/v1/auth/login/
    Authenticates an existing candidate via username (or email) and password,
    returning user metadata and a SimpleJWT access/refresh token pair.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.validated_data

        user_data = UserSerializer(result["user"]).data
        return Response(
            {
                "message": "Login successful.",
                "user": user_data,
                "tokens": result["tokens"],
            },
            status=status.HTTP_200_OK,
        )


class MeAPIView(APIView):
    """
    GET /api/v1/auth/me/
    Returns the profile and metadata for the currently authenticated candidate.
    Requires Bearer JWT token in Authorization header.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

