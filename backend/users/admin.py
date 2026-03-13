from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserProfile, UserPrivateKey


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'


class UserPrivateKeyInline(admin.StackedInline):
    """Inline for viewing private key metadata (NOT the key itself)."""
    model = UserPrivateKey
    can_delete = False
    verbose_name_plural = 'Private Key'
    fk_name = 'user'
    readonly_fields = ['key_id', 'created_at', 'updated_at']
    
    # SECURITY: Never show the encrypted private key
    exclude = ['encrypted_private_key']


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom admin for User model."""

    inlines = (UserProfileInline, UserPrivateKeyInline)
    list_display = [
        'username',
        'email',
        'first_name',
        'last_name',
        'is_online',
        'last_activity',
        'is_staff',
    ]
    list_filter = ['is_online', 'is_staff', 'is_superuser', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['-created_at']

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Extended Info', {
            'fields': ('is_online', 'last_activity'),
        }),
    )

    readonly_fields = ['last_activity', 'created_at', 'updated_at']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin for UserProfile model."""
    list_display = ['user', 'key_created_at', 'has_public_key']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['key_created_at']

    def has_public_key(self, obj):
        return bool(obj.public_key)
    has_public_key.boolean = True
    has_public_key.short_description = 'Has Public Key'


@admin.register(UserPrivateKey)
class UserPrivateKeyAdmin(admin.ModelAdmin):
    """
    Admin for UserPrivateKey model.
    
    SECURITY: The encrypted private key is NEVER displayed in admin.
    Only metadata (user, key_id, timestamps) is shown.
    """
    list_display = ['user', 'key_id', 'created_at', 'updated_at']
    search_fields = ['user__username', 'key_id']
    readonly_fields = ['key_id', 'created_at', 'updated_at']
    
    # SECURITY: Exclude the encrypted private key from all views
    exclude = ['encrypted_private_key']
    
    def has_add_permission(self, request):
        """Prevent manual creation - keys should only be generated via registration."""
        return False
