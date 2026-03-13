"""
Transfer models for Secure File Transfer Application.
Tracks sender-receiver relationships and transfer status.
"""

from django.db import models
from django.conf import settings
import uuid


class Transfer(models.Model):
    """
    Transfer model linking sender, receiver, and file.
    
    Frontend mock replacement:
    - Replaces hardcoded transfer history in TransferHistory.tsx
    - Replaces mock transfer data in SenderDashboard.tsx
    - Replaces mock incoming transfers in ReceiverDashboard.tsx
    
    API Response Example:
    {
        "id": 1,
        "uuid": "550e8400-e29b-41d4-a716-446655440000",
        "sender": {
            "id": 1,
            "username": "john_doe",
            "email": "john@example.com"
        },
        "receiver": {
            "id": 2,
            "username": "jane_smith",
            "email": "jane@example.com"
        },
        "file": {
            "id": 1,
            "original_name": "document.pdf",
            "size_formatted": "1.00 MB"
        },
        "status": "completed",
        "progress": 100,
        "created_at": "2026-02-06T10:30:00Z",
        "completed_at": "2026-02-06T10:35:00Z"
    }
    """
    
    # Transfer status choices
    STATUS_CHOICES = [
        ('pending', 'Pending'),           # Transfer created, waiting for receiver
        ('accepted', 'Accepted'),         # Receiver accepted, ready to start
        ('rejected', 'Rejected'),         # Receiver rejected transfer
        ('connecting', 'Connecting'),     # P2P connection establishing
        ('key_exchange', 'Key Exchange'), # Exchanging encryption keys
        ('transferring', 'Transferring'), # Active file transfer
        ('paused', 'Paused'),            # Transfer paused by user
        ('completed', 'Completed'),       # Transfer successful
        ('failed', 'Failed'),            # Transfer failed
        ('cancelled', 'Cancelled'),       # Transfer cancelled by sender
    ]
    
    # Primary identification
    id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        help_text="Unique transfer identifier"
    )
    
    # Participants
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_transfers',
        help_text="User sending the file"
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_transfers',
        help_text="User receiving the file"
    )
    
    # File reference
    file = models.ForeignKey(
        'files.File',
        on_delete=models.CASCADE,
        related_name='transfers',
        help_text="File being transferred"
    )

    # File name for transfer record
    file_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Original file name at time of transfer"
    )

    # Encrypted file path (where encrypted file is stored)
    encrypted_file_path = models.TextField(
        blank=True,
        null=True,
        help_text="Path to the encrypted file"
    )

    # Encryption algorithm used for this transfer
    encryption_algorithm = models.CharField(
        max_length=50,
        default='AES-256-GCM',
        help_text="Encryption algorithm used for this transfer"
    )

    # Transfer status and progress
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Current transfer status"
    )
    progress = models.PositiveSmallIntegerField(
        default=0,
        help_text="Transfer progress percentage (0-100)"
    )
    
    # Transfer speed and metrics
    bytes_transferred = models.BigIntegerField(
        default=0,
        help_text="Bytes transferred so far"
    )
    transfer_speed = models.FloatField(
        default=0,
        help_text="Current transfer speed in bytes/second"
    )
    
    # Error tracking
    error_message = models.TextField(
        blank=True,
        null=True,
        help_text="Error message if transfer failed"
    )
    retry_count = models.PositiveSmallIntegerField(
        default=0,
        help_text="Number of retry attempts"
    )
    
    # P2P connection info
    connection_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="WebRTC connection identifier"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When transfer was initiated"
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When actual transfer started"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When transfer completed"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Last update timestamp"
    )
    
    class Meta:
        db_table = 'transfers'
        ordering = ['-created_at']
        verbose_name = 'Transfer'
        verbose_name_plural = 'Transfers'
        indexes = [
            models.Index(fields=['sender', 'status']),
            models.Index(fields=['receiver', 'status']),
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.sender.username} → {self.receiver.username}: {self.file.original_name}"
    
    @property
    def duration(self):
        """Calculate transfer duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    @property
    def speed_formatted(self):
        """Return human-readable transfer speed."""
        speed = self.transfer_speed
        for unit in ['B/s', 'KB/s', 'MB/s', 'GB/s']:
            if speed < 1024.0:
                return f"{speed:.2f} {unit}"
            speed /= 1024.0
        return f"{speed:.2f} TB/s"
    
    def accept(self):
        """Accept the transfer request."""
        if self.status == 'pending':
            self.status = 'accepted'
            self.save(update_fields=['status', 'updated_at'])
            return True
        return False
    
    def reject(self):
        """Reject the transfer request."""
        if self.status == 'pending':
            self.status = 'rejected'
            self.save(update_fields=['status', 'updated_at'])
            return True
        return False
    
    def cancel(self):
        """Cancel the transfer."""
        if self.status in ['pending', 'accepted', 'connecting', 'key_exchange', 'transferring', 'paused']:
            self.status = 'cancelled'
            self.save(update_fields=['status', 'updated_at'])
            return True
        return False
    
    def start(self):
        """Mark transfer as started."""
        from django.utils import timezone
        if self.status in ['accepted', 'connecting', 'key_exchange']:
            self.status = 'transferring'
            self.started_at = timezone.now()
            self.save(update_fields=['status', 'started_at', 'updated_at'])
            return True
        return False
    
    def complete(self):
        """Mark transfer as completed."""
        from django.utils import timezone
        if self.status == 'transferring':
            self.status = 'completed'
            self.progress = 100
            self.completed_at = timezone.now()
            self.bytes_transferred = self.file.size
            self.save(update_fields=['status', 'progress', 'completed_at', 'bytes_transferred', 'updated_at'])
            return True
        return False
    
    def fail(self, error_message=None):
        """Mark transfer as failed."""
        self.status = 'failed'
        if error_message:
            self.error_message = error_message
        self.save(update_fields=['status', 'error_message', 'updated_at'])
        return True


class TransferLog(models.Model):
    """
    Transfer activity log for audit and debugging.
    
    Frontend integration:
    - Display in SecurityLog.tsx
    - Show transfer activity timeline
    
    API Response Example:
    {
        "id": 1,
        "transfer_id": 1,
        "event": "status_changed",
        "old_status": "pending",
        "new_status": "accepted",
        "message": "Transfer accepted by receiver",
        "timestamp": "2026-02-06T10:30:00Z"
    }
    """
    
    EVENT_TYPES = [
        ('created', 'Transfer Created'),
        ('status_changed', 'Status Changed'),
        ('progress_update', 'Progress Updated'),
        ('connection_established', 'Connection Established'),
        ('key_exchanged', 'Keys Exchanged'),
        ('chunk_completed', 'Chunk Completed'),
        ('error', 'Error Occurred'),
        ('retry', 'Retry Attempted'),
    ]
    
    id = models.AutoField(primary_key=True)
    transfer = models.ForeignKey(
        Transfer,
        on_delete=models.CASCADE,
        related_name='logs',
        help_text="Associated transfer"
    )
    event = models.CharField(
        max_length=30,
        choices=EVENT_TYPES,
        help_text="Type of event"
    )
    old_status = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Previous status (for status changes)"
    )
    new_status = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="New status (for status changes)"
    )
    message = models.TextField(
        blank=True,
        null=True,
        help_text="Log message details"
    )
    metadata = models.JSONField(
        blank=True,
        null=True,
        help_text="Additional event data"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="When event occurred"
    )
    
    class Meta:
        db_table = 'transfer_logs'
        ordering = ['-timestamp']
        verbose_name = 'Transfer Log'
        verbose_name_plural = 'Transfer Logs'
    
    def __str__(self):
        return f"[{self.timestamp}] {self.transfer} - {self.event}"
