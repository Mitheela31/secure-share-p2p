"""
=============================================================================
PHASE 8: Audit Views for Activity Log Management
=============================================================================

Provides API endpoints for viewing and filtering activity logs.
Logs are read-only - they can only be created programmatically.

Endpoints:
- GET /api/v1/audit/logs/ - List activity logs (current user)
- GET /api/v1/audit/logs/all/ - List all logs (admin only)
- GET /api/v1/audit/stats/ - Activity statistics

=============================================================================
"""

from rest_framework import generics, permissions, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta

from .models import ActivityLog
from .serializers import ActivityLogSerializer, ActivityLogListSerializer
from api.responses import api_response, api_error


class IsAdminUser(permissions.BasePermission):
    """Only allow admin users."""
    def has_permission(self, request, view):
        return request.user and request.user.is_staff


class ActivityLogListView(generics.ListAPIView):
    """
    List activity logs for current user.
    
    GET /api/v1/audit/logs/
    
    Query Parameters:
    - action: Filter by action type (e.g., 'login', 'file_upload')
    - status: Filter by status ('success', 'failed', 'warning', 'error')
    - start_date: Filter logs after this date (YYYY-MM-DD)
    - end_date: Filter logs before this date (YYYY-MM-DD)
    - search: Search in description
    
    Response (200 OK):
    {
        "status": "success",
        "count": 50,
        "results": [
            {
                "id": 1,
                "action": "login",
                "action_display": "User Login",
                "description": "User logged in: john_doe",
                "status": "success",
                "timestamp": "2026-03-12T10:30:00Z"
            }
        ]
    }
    """
    serializer_class = ActivityLogListSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['description']
    ordering_fields = ['timestamp', 'action', 'status']
    ordering = ['-timestamp']
    
    def get_queryset(self):
        """
        Return activity logs for the current user.
        Apply optional filters from query parameters.
        """
        queryset = ActivityLog.objects.filter(user=self.request.user)
        
        # Filter by action type
        action = self.request.query_params.get('action')
        if action:
            queryset = queryset.filter(action=action)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(timestamp__date__gte=start_date)
        
        end_date = self.request.query_params.get('end_date')
        if end_date:
            queryset = queryset.filter(timestamp__date__lte=end_date)
        
        return queryset


class AllActivityLogsView(generics.ListAPIView):
    """
    List all activity logs (admin only).
    
    GET /api/v1/audit/logs/all/
    
    Requires staff/admin permissions.
    Provides access to system-wide activity logs.
    """
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['description', 'user__username', 'ip_address']
    ordering_fields = ['timestamp', 'action', 'status', 'user']
    ordering = ['-timestamp']
    
    def get_queryset(self):
        """Return all activity logs with optional filters."""
        queryset = ActivityLog.objects.select_related('user', 'related_file', 'related_transfer')
        
        # Filter by user
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Filter by action type
        action = self.request.query_params.get('action')
        if action:
            queryset = queryset.filter(action=action)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(timestamp__date__gte=start_date)
        
        end_date = self.request.query_params.get('end_date')
        if end_date:
            queryset = queryset.filter(timestamp__date__lte=end_date)
        
        return queryset


class ActivityLogDetailView(generics.RetrieveAPIView):
    """
    Get details of a specific activity log.
    
    GET /api/v1/audit/logs/<id>/
    
    Users can only view their own logs.
    Admins can view any log.
    """
    serializer_class = ActivityLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Return logs user is authorized to view."""
        if self.request.user.is_staff:
            return ActivityLog.objects.all()
        return ActivityLog.objects.filter(user=self.request.user)


class ActivityStatsView(APIView):
    """
    Get activity statistics for the current user.
    
    GET /api/v1/audit/stats/
    
    Response (200 OK):
    {
        "status": "success",
        "data": {
            "total_activities": 150,
            "activities_today": 12,
            "activities_week": 45,
            "by_action": {
                "login": 20,
                "file_upload": 30,
                "transfer_initiate": 25
            },
            "by_status": {
                "success": 140,
                "failed": 10
            },
            "recent_activity": [...]
        }
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get activity statistics."""
        user = request.user
        now = timezone.now()
        today = now.date()
        week_ago = now - timedelta(days=7)
        
        # Get user's logs
        user_logs = ActivityLog.objects.filter(user=user)
        
        # Calculate statistics
        stats = {
            'total_activities': user_logs.count(),
            'activities_today': user_logs.filter(timestamp__date=today).count(),
            'activities_week': user_logs.filter(timestamp__gte=week_ago).count(),
            'by_action': dict(
                user_logs.values('action')
                .annotate(count=Count('id'))
                .values_list('action', 'count')
            ),
            'by_status': dict(
                user_logs.values('status')
                .annotate(count=Count('id'))
                .values_list('status', 'count')
            ),
            'daily_activity': list(
                user_logs.filter(timestamp__gte=week_ago)
                .annotate(date=TruncDate('timestamp'))
                .values('date')
                .annotate(count=Count('id'))
                .order_by('date')
                .values('date', 'count')
            ),
        }
        
        return api_response(
            data=stats,
            message='Activity statistics retrieved successfully'
        )
