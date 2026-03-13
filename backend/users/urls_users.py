"""
User management URL configuration.
User listing and detail endpoints.
"""

from django.urls import path
from .views_users import (
    UserListView,
    UserDetailView,
    OnlineUsersView,
    HeartbeatView,
    CleanupStaleUsersView,
)

urlpatterns = [
    path('', UserListView.as_view(), name='user-list'),
    path('online/', OnlineUsersView.as_view(), name='online-users'),
    path('heartbeat/', HeartbeatView.as_view(), name='user-heartbeat'),
    path('cleanup/', CleanupStaleUsersView.as_view(), name='cleanup-stale-users'),
    path('<int:pk>/', UserDetailView.as_view(), name='user-detail'),
]
