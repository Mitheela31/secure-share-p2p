"""
Views for user listing and management.
Provides endpoints for listing and retrieving users.
"""

from rest_framework import generics, permissions, filters
from django.contrib.auth import get_user_model

from .serializers import UserSerializer

User = get_user_model()


class UserListView(generics.ListAPIView):
    """
    List All Users API.
    
    GET /api/v1/users/
    
    Frontend integration:
    - Replace mock user list in SenderDashboard.tsx
    - Used for recipient selection in file transfer
    - Shows online status for each user
    
    Query Parameters:
    - search: Filter by username or email
    - is_online: Filter by online status (true/false)
    
    Response (200 OK):
    {
        "count": 3,
        "next": null,
        "previous": null,
        "results": [
            {
                "id": 1,
                "username": "john_doe",
                "email": "john@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "is_online": true,
                "last_activity": "2026-02-06T10:30:00Z",
                "created_at": "2026-01-15T08:00:00Z"
            },
            {
                "id": 2,
                "username": "jane_smith",
                "email": "jane@example.com",
                "first_name": "Jane",
                "last_name": "Smith",
                "is_online": false,
                "last_activity": "2026-02-05T15:45:00Z",
                "created_at": "2026-01-20T09:00:00Z"
            }
        ]
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['username', 'created_at', 'last_activity']
    ordering = ['-is_online', '-last_activity']
    
    def get_queryset(self):
        """Return all users except the current user."""
        queryset = User.objects.exclude(id=self.request.user.id)
        
        # Filter by online status if provided
        is_online = self.request.query_params.get('is_online')
        if is_online is not None:
            is_online_bool = is_online.lower() == 'true'
            queryset = queryset.filter(is_online=is_online_bool)
        
        return queryset


class UserDetailView(generics.RetrieveAPIView):
    """
    Get Single User Details API.
    
    GET /api/v1/users/<id>/
    
    Frontend integration:
    - Get details of a specific user
    - Used when viewing transfer recipient info
    
    Response (200 OK):
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
    serializer_class = UserSerializer
    queryset = User.objects.all()


class OnlineUsersView(generics.ListAPIView):
    """
    List Online Users API.
    
    GET /api/v1/users/online/
    
    Frontend integration:
    - Show only users who are currently online
    - Used for real-time transfer availability
    
    Response (200 OK):
    {
        "count": 2,
        "results": [
            {
                "id": 1,
                "username": "john_doe",
                "email": "john@example.com",
                "is_online": true
            }
        ]
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer
    
    def get_queryset(self):
        """Return only online users except current user."""
        return User.objects.filter(is_online=True).exclude(id=self.request.user.id)
