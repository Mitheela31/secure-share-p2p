"""
User views for authentication and user management.
Provides REST API endpoints for registration, login, profile management.
"""

from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

from .serializers import (
    UserSerializer,
    UserRegistrationSerializer,
    CustomTokenObtainPairSerializer,
    UserProfileSerializer,
    PasswordChangeSerializer,
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """
    User Registration API.
    
    POST /api/v1/auth/register/
    
    Frontend integration:
    - Replace mock registration in AuthPage.tsx
    - Call this endpoint on form submission
    
    Request:
    {
        "username": "john_doe",
        "email": "john@example.com",
        "password": "SecurePass123!",
        "password_confirm": "SecurePass123!",
        "first_name": "John",
        "last_name": "Doe"
    }
    
    Response (201 Created):
    {
        "id": 1,
        "username": "john_doe",
        "email": "john@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "message": "User registered successfully"
    }
    """
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = UserRegistrationSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'message': 'User registered successfully'
        }, status=status.HTTP_201_CREATED)


class LoginView(TokenObtainPairView):
    """
    User Login API - Returns JWT tokens.
    
    POST /api/v1/auth/login/
    
    Frontend integration:
    - Replace mock login in AuthPage.tsx
    - Store tokens in localStorage/context
    
    Request:
    {
        "username": "john_doe",
        "password": "SecurePass123!"
    }
    
    Response (200 OK):
    {
        "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "user": {
            "id": 1,
            "username": "john_doe",
            "email": "john@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "is_online": true
        }
    }
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = CustomTokenObtainPairSerializer


class LogoutView(APIView):
    """
    User Logout API - Blacklists refresh token.
    
    POST /api/v1/auth/logout/
    
    Frontend integration:
    - Call on logout button click
    - Clear stored tokens after successful response
    
    Request:
    {
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
    }
    
    Response (200 OK):
    {
        "message": "Successfully logged out"
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            # Mark user as offline
            request.user.set_online(False)
            
            return Response({
                'message': 'Successfully logged out'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': 'Invalid token'
            }, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    User Profile API - Get/Update current user profile.
    
    GET /api/v1/auth/profile/
    PUT /api/v1/auth/profile/
    
    Frontend integration:
    - Fetch user profile after login
    - Update profile settings
    
    GET Response:
    {
        "id": 1,
        "username": "john_doe",
        "email": "john@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "is_online": true,
        "last_activity": "2026-02-06T10:30:00Z",
        "created_at": "2026-01-15T08:00:00Z"
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserProfileSerializer
    
    def get_object(self):
        return self.request.user


class PasswordChangeView(APIView):
    """
    Password Change API.
    
    POST /api/v1/auth/password/change/
    
    Request:
    {
        "old_password": "OldPass123!",
        "new_password": "NewPass456!",
        "new_password_confirm": "NewPass456!"
    }
    
    Response (200 OK):
    {
        "message": "Password changed successfully"
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return Response({
                'error': 'Current password is incorrect'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({
            'message': 'Password changed successfully'
        }, status=status.HTTP_200_OK)


class RefreshTokenView(TokenRefreshView):
    """
    Token Refresh API - Get new access token.
    
    POST /api/v1/auth/token/refresh/
    
    Request:
    {
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
    }
    
    Response (200 OK):
    {
        "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
    }
    """
    permission_classes = [permissions.AllowAny]
