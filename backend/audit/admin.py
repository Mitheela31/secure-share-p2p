"""
Admin configuration for Audit app.
Provides a comprehensive view of activity logs in Django Admin.
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import ActivityLog


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    """
    Admin interface for ActivityLog model.
    
    Features:
    - List view with filtering and search
    - Color-coded status display
    - Read-only enforcement (logs should not be modified)
    """
    
    list_display = (
        'timestamp',
        'user_display',
        'action',
        'status_badge',
        'ip_address',
        'description_preview',
    )
    
    list_filter = (
        'action',
        'status',
        'timestamp',
    )
    
    search_fields = (
        'user__username',
        'user__email',
        'description',
        'ip_address',
    )
    
    readonly_fields = (
        'uuid',
        'user',
        'action',
        'description',
        'status',
        'ip_address',
        'user_agent',
        'metadata',
        'related_file',
        'related_transfer',
        'timestamp',
    )
    
    ordering = ('-timestamp',)
    date_hierarchy = 'timestamp'
    list_per_page = 50
    
    def has_add_permission(self, request):
        """Logs should only be created programmatically."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Logs should not be modified after creation."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Only superusers can delete logs."""
        return request.user.is_superuser
    
    def user_display(self, obj):
        """Display username or 'Anonymous' for null users."""
        return obj.user.username if obj.user else 'Anonymous'
    user_display.short_description = 'User'
    
    def status_badge(self, obj):
        """Display status with color-coded badge."""
        colors = {
            'success': '#28a745',
            'failed': '#dc3545',
            'warning': '#ffc107',
            'error': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def description_preview(self, obj):
        """Show truncated description."""
        if len(obj.description) > 50:
            return f"{obj.description[:50]}..."
        return obj.description
    description_preview.short_description = 'Description'
