"""
=============================================================================
PHASE 8: Activity Logging Signals
=============================================================================

Django signals for automatic activity logging.

This module hooks into Django's signal system to automatically log:
- User login/logout events
- Model creation/modification events
- Transfer status changes

SIGNAL FLOW:
1. User performs action (login, upload file, etc.)
2. Django emits signal (e.g., user_logged_in)
3. Signal receiver captures event
4. ActivityLog entry is created

=============================================================================
"""

from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from .models import ActivityLog, get_client_ip, get_user_agent

User = get_user_model()


# =============================================================================
# AUTHENTICATION SIGNALS
# =============================================================================

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """
    Log successful user login.
    
    This signal is automatically called by Django when a user logs in
    via the authentication system.
    
    Args:
        sender: The class that sent the signal
        request: The HttpRequest object
        user: The user who logged in
    """
    ip_address = get_client_ip(request) if request else None
    user_agent = get_user_agent(request) if request else ''
    
    ActivityLog.log_login(
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
        success=True
    )


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """
    Log user logout.
    
    Called when a user logs out via the authentication system.
    
    Args:
        sender: The class that sent the signal
        request: The HttpRequest object
        user: The user who logged out
    """
    if user:
        ip_address = get_client_ip(request) if request else None
        ActivityLog.log_logout(
            user=user,
            ip_address=ip_address
        )


@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    """
    Log failed login attempt.
    
    Important for security monitoring - tracks potential brute force attacks.
    
    Args:
        sender: The class that sent the signal
        credentials: The credentials used in the failed attempt
        request: The HttpRequest object
    """
    ip_address = get_client_ip(request) if request else None
    user_agent = get_user_agent(request) if request else ''
    username = credentials.get('username', 'Unknown')
    
    ActivityLog.log(
        action='login_failed',
        user=None,  # No user since login failed
        description=f"Failed login attempt for username: {username}",
        status='failed',
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={'username': username}
    )


# =============================================================================
# USER REGISTRATION SIGNAL
# =============================================================================

@receiver(post_save, sender=User)
def log_user_registration(sender, instance, created, **kwargs):
    """
    Log new user registration.
    
    Called when a new User instance is created.
    
    Args:
        sender: The User model class
        instance: The User instance that was saved
        created: Boolean indicating if this is a new instance
    """
    if created:
        ActivityLog.log(
            action='registration',
            user=instance,
            description=f"New user registered: {instance.username}",
            status='success',
            metadata={
                'user_id': instance.id,
                'username': instance.username,
                'email': instance.email,
            }
        )


# =============================================================================
# HELPER FUNCTION FOR VIEW-BASED LOGGING
# =============================================================================

def log_file_activity(request, file_obj, action, description=None):
    """
    Helper function to log file-related activities from views.
    
    Call this from file views after successful operations.
    
    Args:
        request: The HttpRequest object
        file_obj: The File model instance
        action: Action type ('file_upload', 'file_download', 'file_delete')
        description: Custom description (auto-generated if not provided)
    
    Example:
        from audit.signals import log_file_activity
        
        # In your view after file upload:
        log_file_activity(request, file_obj, 'file_upload')
    """
    if description is None:
        action_verbs = {
            'file_upload': 'Uploaded',
            'file_download': 'Downloaded',
            'file_delete': 'Deleted',
            'file_view': 'Viewed',
        }
        verb = action_verbs.get(action, 'Accessed')
        description = f"{verb} file: {file_obj.original_name} ({file_obj.size_formatted})"
    
    ActivityLog.log(
        action=action,
        user=request.user if request.user.is_authenticated else None,
        description=description,
        status='success',
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        metadata={
            'file_id': file_obj.id,
            'file_uuid': str(file_obj.uuid),
            'file_name': file_obj.original_name,
            'file_size': file_obj.size,
            'mime_type': file_obj.mime_type,
        },
        related_file=file_obj,
    )


def log_transfer_activity(request, transfer, action, description=None, status='success'):
    """
    Helper function to log transfer-related activities from views.
    
    Call this from transfer views after successful operations.
    
    Args:
        request: The HttpRequest object
        transfer: The Transfer model instance
        action: Action type ('initiate', 'accept', 'reject', 'complete', etc.)
        description: Custom description (auto-generated if not provided)
        status: Log status ('success', 'failed', 'warning')
    
    Example:
        from audit.signals import log_transfer_activity
        
        # In your view after transfer initiation:
        log_transfer_activity(request, transfer, 'initiate')
    """
    ActivityLog.log_transfer(
        transfer=transfer,
        action=action,
        user=request.user if request.user.is_authenticated else None,
        ip_address=get_client_ip(request),
        status=status,
        description=description,
    )
