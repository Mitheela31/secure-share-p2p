"""
File metadata models for Secure File Transfer Application.
Stores file information for P2P transfer tracking.

Note: Actual file content is transferred P2P between clients.
This model only stores metadata for tracking and history purposes.
"""

from django.db import models
from django.conf import settings
import uuid
import os


def get_file_upload_path(instance, filename):
    """Generate upload path for files."""
    ext = filename.split('.')[-1]
    new_filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('uploads', str(instance.owner.id), new_filename)


class File(models.Model):
    """
    File metadata model.
    
    Frontend mock replacement:
    - Replaces hardcoded file lists in FileTransfer.tsx
    - Replaces mock file data in SenderDashboard.tsx
    - Provides real file metadata for TransferHistory.tsx
    
    API Response Example:
    {
        "id": 1,
        "name": "document.pdf",
        "original_name": "important_document.pdf",
        "size": 1048576,
        "size_formatted": "1.00 MB",
        "mime_type": "application/pdf",
        "checksum": "abc123def456...",
        "owner": {
            "id": 1,
            "username": "john_doe"
        },
        "uploaded_at": "2026-02-06T10:30:00Z",
        "is_encrypted": true
    }
    """
    
    # File identification
    id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(
        default=uuid.uuid4, 
        editable=False, 
        unique=True,
        help_text="Unique identifier for the file"
    )
    
    # File metadata
    name = models.CharField(
        max_length=255,
        help_text="Stored filename (may be sanitized)"
    )
    original_name = models.CharField(
        max_length=255,
        help_text="Original filename as uploaded"
    )
    size = models.BigIntegerField(
        help_text="File size in bytes"
    )
    mime_type = models.CharField(
        max_length=100,
        default='application/octet-stream',
        help_text="MIME type of the file"
    )
    
    # File integrity
    checksum = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="SHA-256 checksum for integrity verification"
    )
    
    # Encryption status
    is_encrypted = models.BooleanField(
        default=True,
        help_text="Whether file is encrypted for transfer"
    )
    encryption_algorithm = models.CharField(
        max_length=50,
        default='AES-256-GCM',
        help_text="Encryption algorithm used"
    )
    
    # Ownership
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='files',
        help_text="File owner (uploader)"
    )
    
    # Timestamps
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When file metadata was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Last update timestamp"
    )
    
    # Optional: Local storage path (for non-P2P scenarios)
    file_path = models.FileField(
        upload_to=get_file_upload_path,
        null=True,
        blank=True,
        help_text="Optional local storage path"
    )
    
    class Meta:
        db_table = 'files'
        ordering = ['-uploaded_at']
        verbose_name = 'File'
        verbose_name_plural = 'Files'
    
    def __str__(self):
        return f"{self.original_name} ({self.size_formatted})"
    
    @property
    def size_formatted(self):
        """Return human-readable file size."""
        size = self.size
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"
    
    @property
    def extension(self):
        """Return file extension."""
        return os.path.splitext(self.original_name)[1].lower()


class FileChunk(models.Model):
    """
    File chunk model for tracking chunked transfers.
    Used for large file transfers that are split into chunks.
    
    Frontend integration:
    - Tracks progress in ChunkProgress.tsx
    - Shows individual chunk status
    
    API Response Example:
    {
        "id": 1,
        "file_id": 1,
        "chunk_number": 1,
        "total_chunks": 10,
        "size": 1048576,
        "checksum": "abc123...",
        "status": "completed"
    }
    """
    
    CHUNK_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('transferring', 'Transferring'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.AutoField(primary_key=True)
    file = models.ForeignKey(
        File,
        on_delete=models.CASCADE,
        related_name='chunks',
        help_text="Parent file"
    )
    chunk_number = models.PositiveIntegerField(
        help_text="Chunk sequence number (1-indexed)"
    )
    total_chunks = models.PositiveIntegerField(
        help_text="Total number of chunks"
    )
    size = models.PositiveIntegerField(
        help_text="Chunk size in bytes"
    )
    offset = models.BigIntegerField(
        default=0,
        help_text="Byte offset in original file"
    )
    checksum = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="SHA-256 checksum for chunk"
    )
    status = models.CharField(
        max_length=20,
        choices=CHUNK_STATUS_CHOICES,
        default='pending',
        help_text="Chunk transfer status"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'file_chunks'
        ordering = ['file', 'chunk_number']
        unique_together = ['file', 'chunk_number']
        verbose_name = 'File Chunk'
        verbose_name_plural = 'File Chunks'
    
    def __str__(self):
        return f"{self.file.name} - Chunk {self.chunk_number}/{self.total_chunks}"
