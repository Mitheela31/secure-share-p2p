"""
User models for Secure File Transfer Application.
Custom user model with extended profile fields.

This model replaces frontend mock data for:
- User authentication state
- User profile information
- User listing in transfer recipient selection
"""

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import uuid


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser.
    
    Frontend mock replacement:
    - Replaces any hardcoded user data in AuthPage.tsx
    - Replaces user lists in SenderDashboard.tsx recipient selection
    - Provides real user data for TransferHistory.tsx
    
    API Response Example:
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
    
    id = models.AutoField(primary_key=True)
    email = models.EmailField(unique=True, help_text="User's email address")
    
    # Extended profile fields
    is_online = models.BooleanField(
        default=False, 
        help_text="Whether user is currently online"
    )
    last_activity = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Last activity timestamp"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Account creation timestamp"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Last profile update timestamp"
    )
    
    class Meta:
        db_table = 'users'
        ordering = ['-created_at']
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return f"{self.username} ({self.email})"
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = timezone.now()
        self.save(update_fields=['last_activity'])
    
    def set_online(self, status=True):
        """Set user online status."""
        self.is_online = status
        self.last_activity = timezone.now()
        self.save(update_fields=['is_online', 'last_activity'])


class UserProfile(models.Model):
    """
    User Profile model (extends Django User).
    
    Stores additional user information including public key for encryption.
    OneToOne relationship with the custom User model.
    """

    user = models.OneToOneField(
        'User',
        on_delete=models.CASCADE,
        related_name='profile',
        help_text="Associated user account"
    )
    public_key = models.TextField(
        blank=True,
        null=True,
        help_text="User's public key for end-to-end encryption (ECDH)"
    )
    key_created_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the public key was created"
    )

    class Meta:
        db_table = 'user_profiles'
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f"Profile for {self.user.username}"

    def set_public_key(self, key):
        """Set the user's public key and update timestamp."""
        self.public_key = key
        self.key_created_at = timezone.now()
        self.save(update_fields=['public_key', 'key_created_at'])

