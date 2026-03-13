"""
File serializers for API request/response handling.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import File, FileChunk

User = get_user_model()


class FileOwnerSerializer(serializers.ModelSerializer):
    """Minimal serializer for file owner information."""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email']


class FileSerializer(serializers.ModelSerializer):
    """
    Serializer for File model - full file metadata.
    
    Frontend mock replacement:
    - Replaces hardcoded file arrays in FileTransfer.tsx
    - Provides real file data for SenderDashboard.tsx
    
    Example Response:
    {
        "id": 1,
        "uuid": "550e8400-e29b-41d4-a716-446655440000",
        "name": "document.pdf",
        "original_name": "important_document.pdf",
        "size": 1048576,
        "size_formatted": "1.00 MB",
        "mime_type": "application/pdf",
        "checksum": "abc123def456...",
        "is_encrypted": true,
        "encryption_algorithm": "AES-256-GCM",
        "owner": {
            "id": 1,
            "username": "john_doe",
            "email": "john@example.com"
        },
        "uploaded_at": "2026-02-06T10:30:00Z",
        "extension": ".pdf"
    }
    """
    
    owner = FileOwnerSerializer(read_only=True)
    size_formatted = serializers.ReadOnlyField()
    extension = serializers.ReadOnlyField()
    
    class Meta:
        model = File
        fields = [
            'id',
            'uuid',
            'name',
            'original_name',
            'size',
            'size_formatted',
            'mime_type',
            'checksum',
            'is_encrypted',
            'encryption_algorithm',
            'owner',
            'uploaded_at',
            'extension',
        ]
        read_only_fields = ['id', 'uuid', 'owner', 'uploaded_at']


class FileCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating file metadata.
    
    Frontend integration:
    - Called when user selects file for transfer
    - Creates metadata record before P2P transfer starts
    
    Request Example:
    {
        "original_name": "important_document.pdf",
        "size": 1048576,
        "mime_type": "application/pdf",
        "checksum": "abc123def456...",
        "is_encrypted": true
    }
    """
    
    class Meta:
        model = File
        fields = [
            'original_name',
            'size',
            'mime_type',
            'checksum',
            'is_encrypted',
            'encryption_algorithm',
        ]
    
    def validate_size(self, value):
        """Validate file size is positive."""
        if value <= 0:
            raise serializers.ValidationError("File size must be positive.")
        # Optional: Add max size limit
        max_size = 10 * 1024 * 1024 * 1024  # 10 GB
        if value > max_size:
            raise serializers.ValidationError(
                f"File size exceeds maximum allowed ({max_size / (1024**3):.0f} GB)."
            )
        return value
    
    def validate_original_name(self, value):
        """Sanitize filename."""
        # Remove path components for security
        import os
        return os.path.basename(value)
    
    def create(self, validated_data):
        """Create file with owner from request context."""
        validated_data['owner'] = self.context['request'].user
        validated_data['name'] = validated_data['original_name']
        return super().create(validated_data)


class FileListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for file listings.
    
    Used in:
    - File selection dropdowns
    - Transfer history file references
    """
    
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    size_formatted = serializers.ReadOnlyField()
    
    class Meta:
        model = File
        fields = [
            'id',
            'uuid',
            'original_name',
            'size',
            'size_formatted',
            'mime_type',
            'owner_username',
            'uploaded_at',
        ]


class FileChunkSerializer(serializers.ModelSerializer):
    """
    Serializer for file chunks.
    
    Frontend integration:
    - Track chunk progress in ChunkProgress.tsx
    - Display individual chunk status
    
    Example Response:
    {
        "id": 1,
        "file_id": 1,
        "chunk_number": 1,
        "total_chunks": 10,
        "size": 1048576,
        "checksum": "abc123...",
        "status": "completed",
        "progress_percentage": 10.0
    }
    """
    
    file_id = serializers.IntegerField(source='file.id', read_only=True)
    progress_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = FileChunk
        fields = [
            'id',
            'file_id',
            'chunk_number',
            'total_chunks',
            'size',
            'offset',
            'checksum',
            'status',
            'created_at',
            'completed_at',
            'progress_percentage',
        ]
        read_only_fields = ['id', 'file_id', 'created_at']
    
    def get_progress_percentage(self, obj):
        """Calculate chunk's contribution to overall progress."""
        if obj.total_chunks == 0:
            return 0
        return round((obj.chunk_number / obj.total_chunks) * 100, 2)


class FileChunkCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating file chunks.
    
    Request Example:
    {
        "file": 1,
        "chunk_number": 1,
        "total_chunks": 10,
        "size": 1048576,
        "offset": 0,
        "checksum": "abc123..."
    }
    """
    
    class Meta:
        model = FileChunk
        fields = [
            'file',
            'chunk_number',
            'total_chunks',
            'size',
            'offset',
            'checksum',
        ]
    
    def validate(self, attrs):
        """Validate chunk number doesn't exceed total."""
        if attrs['chunk_number'] > attrs['total_chunks']:
            raise serializers.ValidationError({
                "chunk_number": "Chunk number cannot exceed total chunks."
            })
        if attrs['chunk_number'] < 1:
            raise serializers.ValidationError({
                "chunk_number": "Chunk number must be at least 1."
            })
        return attrs


class FileUploadSerializer(serializers.Serializer):
    """
    Serializer for actual file upload (optional, for non-P2P scenarios).
    
    Request: multipart/form-data with file
    """
    
    file = serializers.FileField()
    is_encrypted = serializers.BooleanField(default=True)
    
    def validate_file(self, value):
        """Validate uploaded file."""
        max_size = 100 * 1024 * 1024  # 100 MB for direct upload
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size exceeds maximum for direct upload ({max_size / (1024**2):.0f} MB)."
            )
        return value
