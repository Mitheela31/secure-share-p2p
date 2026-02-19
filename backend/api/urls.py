"""
API app URL configuration.
Aggregates all app endpoints under /api/v1/
"""

from django.urls import path, include

urlpatterns = [
    # Authentication endpoints
    path('auth/', include('users.urls')),

    # User management endpoints
    path('users/', include('users.urls_users')),

    # File management endpoints
    path('files/', include('files.urls')),

    # Transfer endpoints
    path('transfers/', include('transfers.urls')),

    # Crypto endpoints
    path('crypto/', include('crypto.urls')),
]
