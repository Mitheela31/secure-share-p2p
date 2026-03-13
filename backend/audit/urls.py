"""
=============================================================================
PHASE 8: Audit App URL Configuration
=============================================================================

URL patterns for activity log management endpoints.

Endpoints:
- GET /api/v1/audit/logs/           - List user's activity logs
- GET /api/v1/audit/logs/all/       - List all logs (admin only)
- GET /api/v1/audit/logs/<id>/      - Get specific log details
- GET /api/v1/audit/stats/          - Activity statistics

=============================================================================
"""

from django.urls import path
from .views import (
    ActivityLogListView,
    AllActivityLogsView,
    ActivityLogDetailView,
    ActivityStatsView,
)

app_name = 'audit'

urlpatterns = [
    # User's activity logs
    path('logs/', ActivityLogListView.as_view(), name='activity-log-list'),
    
    # All logs (admin only)
    path('logs/all/', AllActivityLogsView.as_view(), name='activity-log-all'),
    
    # Single log detail
    path('logs/<int:pk>/', ActivityLogDetailView.as_view(), name='activity-log-detail'),
    
    # Activity statistics
    path('stats/', ActivityStatsView.as_view(), name='activity-stats'),
]
