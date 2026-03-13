"""
=============================================================================
PHASE 8: Activity Log Model for System Security and Logging
=============================================================================

This module implements comprehensive activity logging for the SecureShare
application. All significant user actions are recorded for:
- Security auditing
- Usage analytics
- Debugging and troubleshooting
- Compliance and accountability

LOGGED EVENTS:
- Authentication (login, logout, failed attempts)
- File operations (upload, download, delete)
- Transfer operations (initiate, accept, reject, complete)
- Key exchange events
- Account management

=============================================================================
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


class ActivityLog(models.Model):
    """
    Activity Log Model - Records all significant user actions in the system.
    
    This model provides a comprehensive audit trail for:
    1. Security monitoring - Track suspicious activities and unauthorized access attempts
    2. Usage analytics - Understand how users interact with the system
    3. Debugging - Trace issues back to specific actions
    4. Compliance - Meet regulatory requirements for data handling
    
    API Response Example:
    {
        "id": 1,
        "uuid": "550e8400-e29b-41d4-a716-446655440000",
        "user": {
            "id": 1,
            "username": "john_doe"
        },
        "action": "file_upload",
        "action_display": "File Upload",
        "description": "Uploaded file: document.pdf (1.5 MB)",
        "ip_address": "192.168.1.100",
        "user_agent": "Mozilla/5.0...",
        "status": "success",
        "timestamp": "2026-03-12T10:30:00Z",
        "metadata": {
            "file_id": 1,
            "file_name": "document.pdf",
            "file_size": 1572864
        }
    }
    """
    
    # =========================================================================
    # ACTION TYPE CHOICES
    # =========================================================================
    # Categorized by domain for easier filtering and reporting
    # =========================================================================
    
    ACTION_CHOICES = [
        # Authentication actions
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('login_failed', 'Login Failed'),
        ('password_change', 'Password Changed'),
        ('registration', 'User Registration'),
        
        # File operations
        ('file_upload', 'File Upload'),
        ('file_download', 'File Download'),
        ('file_delete', 'File Deleted'),
        ('file_view', 'File Viewed'),
        
        # Transfer operations
        ('transfer_initiate', 'Transfer Initiated'),
        ('transfer_accept', 'Transfer Accepted'),
        ('transfer_reject', 'Transfer Rejected'),
        ('transfer_complete', 'Transfer Completed'),
        ('transfer_failed', 'Transfer Failed'),
        ('transfer_cancel', 'Transfer Cancelled'),
        
        # Crypto operations
        ('key_exchange', 'Key Exchange'),
        ('key_generated', 'Keys Generated'),
        ('session_created', 'Session Created'),
        
        # Security events
        ('unauthorized_access', 'Unauthorized Access Attempt'),
        ('invalid_token', 'Invalid Token'),
        ('rate_limit_exceeded', 'Rate Limit Exceeded'),
        
        # Account operations
        ('profile_update', 'Profile Updated'),
        ('user_online', 'User Online'),
        ('user_offline', 'User Offline'),
    ]
    
    # Status choices for the action outcome
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ]
    
    # =========================================================================
    # MODEL FIELDS
    # =========================================================================
    
    # Primary identification
    id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        help_text="Unique identifier for the log entry"
    )
    
    # User who performed the action (nullable for anonymous/system actions)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_logs',
        help_text="User who performed the action"
    )
    
    # Action type
    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        db_index=True,
        help_text="Type of action performed"
    )
    
    # Human-readable description
    description = models.TextField(
        blank=True,
        help_text="Detailed description of the action"
    )
    
    # Action outcome status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='success',
        db_index=True,
        help_text="Outcome status of the action"
    )
    
    # Request metadata
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the request"
    )
    
    user_agent = models.TextField(
        blank=True,
        help_text="User agent string from the request"
    )
    
    # Additional context as JSON
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional structured data about the action"
    )
    
    # Related objects (optional foreign keys for efficient querying)
    related_file = models.ForeignKey(
        'files.File',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_logs',
        help_text="Related file if applicable"
    )
    
    related_transfer = models.ForeignKey(
        'transfers.Transfer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_logs',
        help_text="Related transfer if applicable"
    )
    
    # Timestamps
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When the action occurred"
    )
    
    class Meta:
        db_table = 'activity_logs'
        ordering = ['-timestamp']
        verbose_name = 'Activity Log'
        verbose_name_plural = 'Activity Logs'
        indexes = [
            models.Index(fields=['user', 'action']),
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['status', 'timestamp']),
        ]
    
    def __str__(self):
        user_str = self.user.username if self.user else 'Anonymous'
        return f"[{self.timestamp}] {user_str}: {self.get_action_display()}"
    
    # =========================================================================
    # CLASS METHODS FOR CREATING LOG ENTRIES
    # =========================================================================
    
    @classmethod
    def log(cls, action, user=None, description='', status='success',
            ip_address=None, user_agent='', metadata=None,
            related_file=None, related_transfer=None):
        """
        Create a new activity log entry.
        
        Args:
            action: Action type from ACTION_CHOICES
            user: User who performed the action (optional)
            description: Human-readable description
            status: Outcome status ('success', 'failed', 'warning', 'error')
            ip_address: Client IP address
            user_agent: Client user agent string
            metadata: Additional JSON data
            related_file: Related File object (optional)
            related_transfer: Related Transfer object (optional)
        
        Returns:
            ActivityLog instance
        
        Example:
            ActivityLog.log(
                action='file_upload',
                user=request.user,
                description=f"Uploaded file: {filename}",
                ip_address=get_client_ip(request),
                metadata={'file_id': file.id, 'file_size': file.size}
            )
        """
        return cls.objects.create(
            user=user,
            action=action,
            description=description,
            status=status,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata or {},
            related_file=related_file,
            related_transfer=related_transfer,
        )
    
    @classmethod
    def log_login(cls, user, ip_address=None, user_agent='', success=True):
        """Log a login attempt."""
        return cls.log(
            action='login' if success else 'login_failed',
            user=user if success else None,
            description=f"User {'logged in' if success else 'login failed'}: {user.username if user else 'Unknown'}",
            status='success' if success else 'failed',
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={'username': user.username if user else 'Unknown'}
        )
    
    @classmethod
    def log_logout(cls, user, ip_address=None):
        """Log a logout event."""
        return cls.log(
            action='logout',
            user=user,
            description=f"User logged out: {user.username}",
            ip_address=ip_address,
        )
    
    @classmethod
    def log_file_upload(cls, user, file_obj, ip_address=None):
        """Log a file upload."""
        return cls.log(
            action='file_upload',
            user=user,
            description=f"Uploaded file: {file_obj.original_name} ({file_obj.size_formatted})",
            ip_address=ip_address,
            metadata={
                'file_id': file_obj.id,
                'file_name': file_obj.original_name,
                'file_size': file_obj.size,
                'mime_type': file_obj.mime_type,
            },
            related_file=file_obj,
        )
    
    @classmethod
    def log_file_download(cls, user, file_obj, transfer=None, ip_address=None):
        """Log a file download."""
        return cls.log(
            action='file_download',
            user=user,
            description=f"Downloaded file: {file_obj.original_name}",
            ip_address=ip_address,
            metadata={
                'file_id': file_obj.id,
                'file_name': file_obj.original_name,
                'transfer_id': transfer.id if transfer else None,
            },
            related_file=file_obj,
            related_transfer=transfer,
        )
    
    @classmethod
    def log_transfer(cls, transfer, action, user, ip_address=None,
                     status='success', description=None):
        """Log a transfer-related action."""
        action_map = {
            'initiate': 'transfer_initiate',
            'accept': 'transfer_accept',
            'reject': 'transfer_reject',
            'complete': 'transfer_complete',
            'failed': 'transfer_failed',
            'cancel': 'transfer_cancel',
        }
        
        log_action = action_map.get(action, f'transfer_{action}')
        
        if description is None:
            description = f"Transfer {action}: {transfer.file.original_name} " \
                         f"from {transfer.sender.username} to {transfer.receiver.username}"
        
        return cls.log(
            action=log_action,
            user=user,
            description=description,
            status=status,
            ip_address=ip_address,
            metadata={
                'transfer_id': transfer.id,
                'transfer_uuid': str(transfer.uuid),
                'file_name': transfer.file.original_name,
                'sender': transfer.sender.username,
                'receiver': transfer.receiver.username,
            },
            related_file=transfer.file,
            related_transfer=transfer,
        )
    
    @classmethod
    def log_unauthorized_access(cls, user=None, resource_type='', resource_id=None,
                                 ip_address=None, user_agent=''):
        """Log an unauthorized access attempt."""
        return cls.log(
            action='unauthorized_access',
            user=user,
            description=f"Unauthorized access attempt to {resource_type} (ID: {resource_id})",
            status='warning',
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={
                'resource_type': resource_type,
                'resource_id': resource_id,
            }
        )


def get_client_ip(request):
    """
    Extract client IP address from request.
    
    Handles proxy headers (X-Forwarded-For) for accurate IP detection
    behind load balancers and reverse proxies.
    
    Args:
        request: Django request object
    
    Returns:
        str: Client IP address
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # X-Forwarded-For can contain multiple IPs; take the first (client) IP
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_user_agent(request):
    """
    Extract user agent string from request.
    
    Args:
        request: Django request object
    
    Returns:
        str: User agent string
    """
    return request.META.get('HTTP_USER_AGENT', '')
