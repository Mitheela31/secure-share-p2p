"""
Cryptographic models for secure key exchange.
Stores session keys and shared secrets between users.
"""

from datetime import timedelta
from django.db import models
from django.conf import settings
from django.utils import timezone


def default_expiry():
    """Default session expiry: 7 days from creation."""
    return timezone.now() + timedelta(days=7)


class SessionKey(models.Model):
    """
    Session key / shared secret model.

    Stores the negotiated shared secret between a sender and receiver.
    The shared secret is hex-encoded for storage.
    
    SECURITY NOTES:
    - shared_secret should NEVER be exposed in API responses or admin
    - Sessions expire after 7 days by default
    - Sessions can be revoked by setting is_active=False
    """

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='session_keys_sent',
        help_text="User who initiated the session"
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='session_keys_received',
        help_text="User who receives the session"
    )
    shared_secret = models.TextField(
        help_text="Hex-encoded shared secret (NEVER expose in API/admin)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this session is active (can be revoked)"
    )
    expires_at = models.DateTimeField(
        default=default_expiry,
        help_text="When this session expires"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the session key was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the session was last modified"
    )

    class Meta:
        db_table = 'session_keys'
        ordering = ['-created_at']
        verbose_name = 'Session Key'
        verbose_name_plural = 'Session Keys'
        indexes = [
            models.Index(fields=['sender', 'receiver']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['is_active']),
        ]
        # Ensure only one active session between any sender-receiver pair
        constraints = [
            models.UniqueConstraint(
                fields=['sender', 'receiver'],
                condition=models.Q(is_active=True),
                name='unique_active_session_per_pair'
            )
        ]

    def __str__(self):
        status = "active" if self.is_active else "revoked"
        return f"{self.sender.username} → {self.receiver.username} ({status})"
    
    @property
    def is_expired(self):
        """Check if this session has expired."""
        return timezone.now() > self.expires_at
    
    @property
    def is_valid(self):
        """Check if this session is both active and not expired."""
        return self.is_active and not self.is_expired
    
    def revoke(self):
        """Revoke this session."""
        self.is_active = False
        self.save(update_fields=['is_active', 'updated_at'])
