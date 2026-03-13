from django.contrib import admin
from .models import SessionKey


@admin.register(SessionKey)
class SessionKeyAdmin(admin.ModelAdmin):
    """
    Admin for SessionKey model.
    
    SECURITY: The shared_secret field is NEVER displayed in admin.
    This prevents accidental exposure of cryptographic material.
    """
    list_display = ['id', 'sender', 'receiver', 'created_at', 'is_active']
    list_filter = ['created_at', 'is_active']
    search_fields = ['sender__username', 'receiver__username']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    # SECURITY: Exclude the shared secret from all admin views
    exclude = ['shared_secret']
    
    def has_add_permission(self, request):
        """Prevent manual creation - sessions should only be created via key exchange."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent editing sessions - they are cryptographically bound."""
        return False
