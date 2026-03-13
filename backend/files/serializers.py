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
        "has_encrypted_content": true,
        "is_decrypted": false,
        "downloaded_at": "2026-02-20T12:00:00Z",
        "download_count": 1,
        "session_id": 123,
        "owner": {
            "id": 1,
            "username": "john_doe",
            "email": "john@example.com"
        },
        "uploaded_at": "2026-02-06T10:30:00Z",
        "extension": ".pdf"
    }
    
    SECURITY NOTE:
    - IV and tag are NOT included (they're stored but not exposed by default)
    - encrypted_file path is NOT exposed
    - To download, use a dedicated secure endpoint
    """
    
    owner = FileOwnerSerializer(read_only=True)
    size_formatted = serializers.ReadOnlyField()
    extension = serializers.ReadOnlyField()
    has_encrypted_content = serializers.SerializerMethodField()
    session_id = serializers.PrimaryKeyRelatedField(source='session', read_only=True)
    
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
            'has_encrypted_content',
            'is_decrypted',
            'downloaded_at',
            'download_count',
            'session_id',
            'owner',
            'uploaded_at',
            'extension',
        ]
        read_only_fields = ['id', 'uuid', 'owner', 'uploaded_at', 'is_decrypted', 'downloaded_at', 'download_count']
    
    def get_has_encrypted_content(self, obj):
        """Check if file has encrypted content stored."""
        return bool(obj.encrypted_file)


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


class SecureFileUploadSerializer(serializers.Serializer):
    """
    Serializer for secure encrypted file upload.
    
    FLOW:
    1. User uploads file + receiver_id
    2. Server validates active session exists between sender and receiver
    3. Server derives AES-256 key from session's shared secret
    4. Server encrypts file using AES-256-GCM
    5. Server stores: encrypted file, IV, authentication tag
    6. Original plaintext is NEVER stored
    
    Request: multipart/form-data
    {
        "file": <file>,
        "receiver_id": 123
    }
    
    Response:
    {
        "status": "success",
        "message": "File encrypted and stored securely",
        "file_id": 456
    }
    
    MEMORY SAFETY NOTE:
    Files are loaded entirely into memory for AES-GCM encryption.
    Max size is limited to prevent memory exhaustion attacks.
    """
    
    # Maximum file size for encrypted upload (100 MB)
    # This limit ensures server memory safety during encryption
    # AES-GCM requires full message in memory for authentication
    MAX_ENCRYPTED_UPLOAD_SIZE = 100 * 1024 * 1024  # 100 MB
    
    file = serializers.FileField(
        help_text="File to encrypt and upload"
    )
    receiver_id = serializers.IntegerField(
        help_text="ID of the intended receiver (must have active session)"
    )
    
    def validate_file(self, value):
        """
        Validate uploaded file.
        
        Security checks:
        - File size within limits (memory safety)
        - File is not empty
        """
        if value.size > self.MAX_ENCRYPTED_UPLOAD_SIZE:
            raise serializers.ValidationError(
                f"File size exceeds maximum for encrypted upload "
                f"({self.MAX_ENCRYPTED_UPLOAD_SIZE / (1024**2):.0f} MB). "
                f"For larger files, use chunked transfer."
            )
        if value.size == 0:
            raise serializers.ValidationError("Cannot upload empty file.")
        return value
    
    def validate_receiver_id(self, value):
        """Validate receiver exists."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("Receiver user not found.")
        return value
    
    def validate(self, attrs):
        """
        Cross-field validation.
        
        Validates:
        - Receiver is not the sender
        - Active session exists between sender and receiver
        """
        request = self.context.get('request')
        if not request or not request.user:
            raise serializers.ValidationError("Authentication required.")
        
        receiver_id = attrs.get('receiver_id')
        
        # Cannot send to yourself
        if request.user.id == receiver_id:
            raise serializers.ValidationError({
                "receiver_id": "Cannot send encrypted file to yourself."
            })
        
        # Validate active session exists
        from crypto.models import SessionKey
        
        session = SessionKey.objects.filter(
            sender=request.user,
            receiver_id=receiver_id,
            is_active=True
        ).first()
        
        if not session:
            raise serializers.ValidationError({
                "receiver_id": "No active session with this receiver. Please initiate key exchange first."
            })
        
        # Check session validity (not expired)
        if not session.is_valid:
            raise serializers.ValidationError({
                "receiver_id": "Session has expired. Please initiate a new key exchange."
            })
        
        # Attach session to validated data for use in view
        attrs['session'] = session
        
        return attrs
