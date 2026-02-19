"""
Cryptographic models for secure key exchange.
Stores session keys and shared secrets between users.
"""

from django.db import models
from django.conf import settings


class SessionKey(models.Model):
    """
    Session key / shared secret model.

    Stores the negotiated shared secret between a sender and receiver.
    The shared secret should be encrypted or encoded before storage.
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
        help_text="Encrypted or encoded shared secret"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the session key was created"
    )

    class Meta:
        db_table = 'session_keys'
        ordering = ['-created_at']
        verbose_name = 'Session Key'
        verbose_name_plural = 'Session Keys'
        indexes = [
            models.Index(fields=['sender', 'receiver']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.sender.username} → {self.receiver.username} ({self.created_at:%Y-%m-%d %H:%M})"
