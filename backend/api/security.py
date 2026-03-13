"""
=============================================================================
PHASE 8: Security Utilities
=============================================================================

Security validation utilities for file uploads and API endpoints.

This module provides:
1. File type validation (allowed/blocked mime types)
2. File size limit enforcement
3. Rate limiting utilities
4. Security headers middleware helpers

These utilities can be imported and used in views or as serializer validators.

=============================================================================
"""

import os
from functools import wraps
from rest_framework.response import Response
from rest_framework import status

# Try to import python-magic for file type detection (optional)
try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False

# =============================================================================
# FILE TYPE VALIDATION
# =============================================================================

# Allowed MIME types for file uploads
ALLOWED_MIME_TYPES = {
    # Documents
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'text/plain',
    'text/csv',
    'application/json',
    'application/xml',
    'text/xml',
    
    # Images
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp',
    'image/svg+xml',
    'image/bmp',
    'image/tiff',
    
    # Archives
    'application/zip',
    'application/x-rar-compressed',
    'application/x-7z-compressed',
    'application/gzip',
    'application/x-tar',
    
    # Media
    'audio/mpeg',
    'audio/wav',
    'audio/ogg',
    'video/mp4',
    'video/webm',
    'video/quicktime',
    
    # Other common types
    'application/octet-stream',  # Allow binary files (encrypted data)
}

# Blocked file extensions (dangerous executables)
BLOCKED_EXTENSIONS = {
    '.exe', '.bat', '.cmd', '.com', '.msi', '.scr',  # Windows executables
    '.sh', '.bash', '.csh', '.ksh', '.zsh',          # Unix scripts
    '.ps1', '.psm1', '.psd1',                        # PowerShell
    '.vbs', '.vbe', '.wsf', '.wsh', '.js',           # Script files
    '.jar', '.jnlp',                                  # Java
    '.dll', '.sys', '.drv',                          # System files
    '.reg',                                           # Registry files
    '.php', '.phtml', '.php3', '.php4', '.php5',     # Server scripts
    '.asp', '.aspx', '.asa', '.asax',
    '.pl', '.pm', '.cgi',
    '.py', '.pyc', '.pyw',                           # Python (optional - can be removed)
}


def validate_file_type(uploaded_file, use_magic=True):
    """
    Validate file type by checking extension and optionally MIME type.
    
    Args:
        uploaded_file: Django UploadedFile object
        use_magic: If True, use python-magic for content inspection
        
    Returns:
        tuple: (is_valid, error_message)
        
    Example:
        is_valid, error = validate_file_type(request.FILES['file'])
        if not is_valid:
            return Response({'error': error}, status=400)
    """
    filename = uploaded_file.name.lower()
    extension = os.path.splitext(filename)[1]
    
    # Check if extension is blocked
    if extension in BLOCKED_EXTENSIONS:
        return False, f"File type '{extension}' is not allowed for security reasons."
    
    # Check MIME type from file header
    mime_type = uploaded_file.content_type
    
    if use_magic and HAS_MAGIC:
        try:
            # Read first 2048 bytes to determine actual file type
            uploaded_file.seek(0)
            file_header = uploaded_file.read(2048)
            uploaded_file.seek(0)  # Reset for later use
            
            detected_mime = magic.from_buffer(file_header, mime=True)
            
            # Use detected MIME if available
            if detected_mime:
                mime_type = detected_mime
        except Exception:
            # If magic fails, fall back to provided content_type
            pass
    
    # Check if MIME type is allowed
    if mime_type and mime_type not in ALLOWED_MIME_TYPES:
        # Be lenient - encrypted files may not match expected types
        if mime_type.startswith('application/') or mime_type.startswith('text/'):
            pass  # Allow general application and text types
        else:
            return False, f"File type '{mime_type}' is not allowed."
    
    return True, None


def validate_filename(filename):
    """
    Validate and sanitize filename.
    
    Removes path traversal attempts and dangerous characters.
    
    Args:
        filename: Original filename string
        
    Returns:
        tuple: (sanitized_filename, error_message)
    """
    if not filename:
        return None, "Filename is required."
    
    # Remove path components (prevent path traversal)
    filename = os.path.basename(filename)
    
    # Remove null bytes
    filename = filename.replace('\x00', '')
    
    # Remove dangerous characters
    dangerous_chars = ['..', '/', '\\', '<', '>', ':', '"', '|', '?', '*']
    for char in dangerous_chars:
        filename = filename.replace(char, '_')
    
    # Ensure filename is not empty after sanitization
    if not filename or filename.startswith('.'):
        return None, "Invalid filename."
    
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255-len(ext)] + ext
    
    return filename, None


# =============================================================================
# FILE SIZE VALIDATION
# =============================================================================

# Size limits in bytes
FILE_SIZE_LIMITS = {
    'default': 10 * 1024 * 1024 * 1024,    # 10 GB
    'free_tier': 100 * 1024 * 1024,         # 100 MB
    'premium': 50 * 1024 * 1024 * 1024,     # 50 GB
}


def validate_file_size(file_size, tier='default'):
    """
    Validate file size against tier limits.
    
    Args:
        file_size: Size in bytes
        tier: User tier ('default', 'free_tier', 'premium')
        
    Returns:
        tuple: (is_valid, error_message)
    """
    limit = FILE_SIZE_LIMITS.get(tier, FILE_SIZE_LIMITS['default'])
    
    if file_size <= 0:
        return False, "File size must be positive."
    
    if file_size > limit:
        limit_mb = limit / (1024 * 1024)
        return False, f"File size exceeds maximum limit of {limit_mb:.0f} MB."
    
    return True, None


def format_file_size(size_bytes):
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        str: Formatted size string (e.g., "1.5 MB")
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024 ** 2):.2f} MB"
    else:
        return f"{size_bytes / (1024 ** 3):.2f} GB"


# =============================================================================
# SECURITY DECORATORS
# =============================================================================

def log_activity(action, get_description=None):
    """
    Decorator to automatically log view activity.
    
    Usage:
        @log_activity('file_upload', lambda req, res: f"Uploaded {res.data['name']}")
        def post(self, request):
            ...
    
    Args:
        action: Action type from ActivityLog.ACTION_CHOICES
        get_description: Optional function(request, response) -> str
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            response = view_func(self, request, *args, **kwargs)
            
            # Log on successful operations
            if response.status_code < 400:
                try:
                    from audit.models import ActivityLog, get_client_ip, get_user_agent
                    
                    description = None
                    if get_description:
                        try:
                            description = get_description(request, response)
                        except:
                            pass
                    
                    if not description:
                        description = f"{action.replace('_', ' ').title()} operation"
                    
                    ActivityLog.log(
                        action=action,
                        user=request.user if request.user.is_authenticated else None,
                        description=description,
                        status='success',
                        ip_address=get_client_ip(request),
                        user_agent=get_user_agent(request),
                    )
                except Exception:
                    pass  # Don't fail the view if logging fails
            
            return response
        return wrapper
    return decorator


def require_secure_connection(view_func):
    """
    Decorator to require HTTPS in production.
    
    In DEBUG mode, allows HTTP for local development.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        from django.conf import settings
        
        if not settings.DEBUG:
            if not request.is_secure():
                return Response({
                    'status': 'error',
                    'message': 'HTTPS is required for this endpoint.'
                }, status=status.HTTP_403_FORBIDDEN)
        
        return view_func(request, *args, **kwargs)
    return wrapper


# =============================================================================
# RESPONSE HELPER WITH SECURITY HEADERS
# =============================================================================

def secure_response(data, status_code=200, **kwargs):
    """
    Create a Response with security headers.
    
    Args:
        data: Response data
        status_code: HTTP status code
        **kwargs: Additional Response arguments
        
    Returns:
        Response with security headers set
    """
    response = Response(data, status=status_code, **kwargs)
    
    # Add security headers
    response['X-Content-Type-Options'] = 'nosniff'
    response['X-Frame-Options'] = 'DENY'
    response['X-XSS-Protection'] = '1; mode=block'
    response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    return response
