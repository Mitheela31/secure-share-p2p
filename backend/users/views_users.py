"""
Views for user listing and management.
Provides endpoints for listing and retrieving users.
"""

from rest_framework import generics, permissions, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from .serializers import UserSerializer

User = get_user_model()

# ---------------------------------------------------------------------------
# ONLINE PRESENCE THRESHOLD
# ---------------------------------------------------------------------------
# A user is considered "online" only when their last heartbeat (last_seen)
# arrived within this window.  The frontend sends a heartbeat every 30 s,
# so 60 s gives one full missed beat before a user is considered offline.
# This value must match ONLINE_THRESHOLD_SECONDS in serializers.py.
# ---------------------------------------------------------------------------
ONLINE_THRESHOLD_SECONDS = 60


def online_since():
    """Return the cutoff datetime below which a user is considered offline."""
    return timezone.now() - timedelta(seconds=ONLINE_THRESHOLD_SECONDS)


class UserListView(generics.ListAPIView):
    """
    List All Users API.
    
    GET /api/v1/users/
    GET /api/v1/users/?is_online=true  — only truly active users
    GET /api/v1/users/?search=alice    — search by username / email
    
    "Online" means last_seen within the last 60 seconds.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['username', 'created_at', 'last_seen']
    ordering = ['-last_seen']
    
    def get_queryset(self):
        """
        Return users excluding the requester.
        When is_online=true is passed, filter by last_seen timestamp
        instead of the stored boolean to get accurate presence data.
        """
        queryset = User.objects.exclude(id=self.request.user.id)
        
        is_online_param = self.request.query_params.get('is_online')
        if is_online_param is not None:
            if is_online_param.lower() == 'true':
                # Only users who sent a heartbeat in the last 60 seconds
                queryset = queryset.filter(last_seen__gte=online_since())
            else:
                # Users with no recent heartbeat (or never sent one)
                queryset = queryset.filter(
                    last_seen__isnull=True
                ) | queryset.filter(last_seen__lt=online_since())
        
        return queryset


class UserDetailView(generics.RetrieveAPIView):
    """
    Get Single User Details API.
    
    GET /api/v1/users/<id>/
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer
    queryset = User.objects.all()


class OnlineUsersView(generics.ListAPIView):
    """
    List Currently Online Users API.
    
    GET /api/v1/users/online/
    
    Returns only users who have sent a heartbeat in the last 60 seconds.
    This is the authoritative "available receivers" list — it will never
    include users whose browsers are closed or who are idle for > 60 s,
    because presence is derived from last_seen timestamp, not a flag.
    
    Response (200 OK):
    {
        "count": 2,
        "results": [
            {
                "id": 2,
                "username": "alice",
                "is_online": true,
                "last_seen": "2026-03-13T10:30:00Z"
            }
        ]
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer
    
    def get_queryset(self):
        """
        Return only users whose last heartbeat is within 60 seconds.
        Excludes the requesting user (they are choosing a receiver, not themselves).
        """
        # Compute the cutoff once for consistency within this request
        cutoff = online_since()
        return (
            User.objects
            .filter(last_seen__gte=cutoff)       # active in last 60 s
            .exclude(id=self.request.user.id)    # not the requester
            .order_by('-last_seen')
        )


class HeartbeatView(APIView):
    """
    User Heartbeat API — keeps the current user marked as online.
    
    POST /api/v1/users/heartbeat/
    
    The frontend calls this every 30 seconds while the user is logged in.
    Each call:
      1. Stamps user.last_seen = now()   (the truth of presence)
      2. Returns the computed online status and count of active users
    
    There is NO explicit cleanup step needed — presence is evaluated live
    from last_seen at query time, so stale users "fall off" automatically
    without any background job.
    
    Response (200 OK):
    {
        "message": "Heartbeat received",
        "is_online": true,
        "last_seen": "2026-03-13T10:30:00Z",
        "online_users_count": 3
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        user = request.user

        # ---------------------------------------------------------------
        # Update last_seen — this is the single source of truth for presence.
        # update_last_seen() also syncs last_activity and is_online for
        # backward-compatibility with any legacy code that reads is_online.
        # ---------------------------------------------------------------
        user.update_last_seen()

        # Count currently online users (including this user, excluding nobody)
        # Useful for the frontend to show "N users online" badges.
        online_count = User.objects.filter(last_seen__gte=online_since()).count()

        return Response({
            'message': 'Heartbeat received',
            'is_online': True,
            'last_seen': user.last_seen.isoformat(),
            'online_users_count': online_count,
        }, status=status.HTTP_200_OK)


class CleanupStaleUsersView(APIView):
    """
    Cleanup Stale Users API — sync the legacy is_online boolean.
    
    POST /api/v1/users/cleanup/
    
    Because online status is now computed from last_seen, this endpoint is
    no longer needed for correctness.  It is kept for backward-compatibility
    and to repair the is_online boolean flag if needed (e.g., after a deploy).
    
    Response (200 OK):
    {
        "message": "Cleanup completed",
        "users_marked_offline": 3,
        "threshold_seconds": 60
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        # Allow overriding the threshold via request body (default 60 s)
        threshold_seconds = int(
            request.data.get('threshold_seconds',
            request.data.get('threshold_minutes', 1) * 60  # legacy param
            if 'threshold_minutes' in request.data
            else ONLINE_THRESHOLD_SECONDS)
        )

        cutoff = timezone.now() - timedelta(seconds=threshold_seconds)

        # Sync is_online boolean for users whose last_seen has expired
        stale = User.objects.filter(is_online=True).exclude(last_seen__gte=cutoff)
        count = stale.count()
        stale.update(is_online=False)

        return Response({
            'message': 'Cleanup completed',
            'users_marked_offline': count,
            'threshold_seconds': threshold_seconds,
        }, status=status.HTTP_200_OK)



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


class HeartbeatView(APIView):
    """
    User Heartbeat API - Keep user online and update activity.
    
    POST /api/v1/users/heartbeat/
    
    Frontend integration:
    - Call this endpoint every 30-60 seconds while user is active
    - Updates last_activity timestamp
    - Keeps is_online status active
    - Automatically marks stale users as offline
    
    Response (200 OK):
    {
        "message": "Activity updated",
        "is_online": true,
        "last_activity": "2026-03-12T10:30:00Z",
        "stale_users_cleaned": 2
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        user = request.user
        
        # Update current user's activity
        user.set_online(True)
        
        # Clean up stale users (those who haven't sent heartbeat recently)
        threshold = timezone.now() - timedelta(minutes=STALE_USER_THRESHOLD_MINUTES)
        stale_users = User.objects.filter(
            is_online=True,
            last_activity__lt=threshold
        ).exclude(id=user.id)
        
        stale_count = stale_users.count()
        stale_users.update(is_online=False)
        
        return Response({
            'message': 'Activity updated',
            'is_online': user.is_online,
            'last_activity': user.last_activity.isoformat(),
            'stale_users_cleaned': stale_count
        }, status=status.HTTP_200_OK)


class CleanupStaleUsersView(APIView):
    """
    Cleanup Stale Users API - Mark inactive users as offline.
    
    POST /api/v1/users/cleanup/
    
    Frontend integration:
    - Can be called manually or automatically
    - Marks users with no recent activity as offline
    
    Request (optional):
    {
        "threshold_minutes": 5
    }
    
    Response (200 OK):
    {
        "message": "Cleanup completed",
        "users_marked_offline": 3,
        "threshold_minutes": 5
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        threshold_minutes = request.data.get('threshold_minutes', STALE_USER_THRESHOLD_MINUTES)
        
        threshold = timezone.now() - timedelta(minutes=threshold_minutes)
        stale_users = User.objects.filter(
            is_online=True,
            last_activity__lt=threshold
        )
        
        count = stale_users.count()
        stale_users.update(is_online=False)
        
        return Response({
            'message': 'Cleanup completed',
            'users_marked_offline': count,
            'threshold_minutes': threshold_minutes
        }, status=status.HTTP_200_OK)
