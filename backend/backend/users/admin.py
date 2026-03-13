from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom admin for User model."""

    inlines = (UserProfileInline,)
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
