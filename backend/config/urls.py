"""
URL configuration for Secure File Transfer Backend.
All API endpoints are defined here with proper REST naming conventions.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    # Admin panel
    path('admin/', admin.site.urls),
    
    # API v1 endpoints
    path('api/v1/auth/', include('users.urls')),
    path('api/v1/users/', include('users.urls_users')),
    path('api/v1/files/', include('files.urls')),
    path('api/v1/transfers/', include('transfers.urls')),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
