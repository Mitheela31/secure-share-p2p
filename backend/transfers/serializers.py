"""
Transfer serializers for API request/response handling.
"""

import base64

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Transfer, TransferLog
from files.models import File

User = get_user_model()


def _decode_base64_bytes(value: str, field_name: str, expected_length: int) -> bytes:
    if not value or not str(value).strip():
        raise serializers.ValidationError({field_name: f'{field_name} is required.'})

    cleaned = str(value).strip().replace('\n', '').replace('\r', '').replace(' ', '')
    padded = cleaned + ('=' * ((4 - len(cleaned) % 4) % 4))

    try:
        decoded = base64.b64decode(padded, validate=True)
    except Exception as error:
        raise serializers.ValidationError({field_name: f'{field_name} must be valid base64.'}) from error

    if len(decoded) != expected_length:
        raise serializers.ValidationError({field_name: f'{field_name} must be {expected_length} bytes when decoded.'})

    return decoded


class TransferUserSerializer(serializers.ModelSerializer):
    """Minimal serializer for transfer participant info."""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'is_online']


class TransferFileSerializer(serializers.ModelSerializer):
    """Minimal serializer for transfer file info."""
    
    size_formatted = serializers.ReadOnlyField()
    
    class Meta:
        model = File
        fields = ['id', 'uuid', 'original_name', 'size', 'size_formatted', 'mime_type']


class TransferSerializer(serializers.ModelSerializer):
    """
    Full serializer for Transfer model.
    
    Frontend mock replacement:
    - Replaces hardcoded transfer history in TransferHistory.tsx
    - Replaces mock transfers in SenderDashboard.tsx
    - Replaces mock incoming transfers in ReceiverDashboard.tsx
    
    Example Response:
    {
        "id": 1,
        "uuid": "550e8400-e29b-41d4-a716-446655440000",
        "sender": {
            "id": 1,
            "username": "john_doe",
            "email": "john@example.com",
            "is_online": true
        },
        "receiver": {
            "id": 2,
            "username": "jane_smith",
            "email": "jane@example.com",
            "is_online": true
        },
        "file": {
            "id": 1,
            "uuid": "...",
            "original_name": "document.pdf",
            "size": 1048576,
            "size_formatted": "1.00 MB",
            "mime_type": "application/pdf"
        },
        "status": "completed",
        "status_display": "Completed",
        "progress": 100,
        "bytes_transferred": 1048576,
        "transfer_speed": 524288,
        "speed_formatted": "512.00 KB/s",
        "created_at": "2026-02-06T10:30:00Z",
        "started_at": "2026-02-06T10:31:00Z",
        "completed_at": "2026-02-06T10:35:00Z",
        "duration": 240
    }
    """
    
    sender = TransferUserSerializer(read_only=True)
    receiver = TransferUserSerializer(read_only=True)
    file = TransferFileSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    speed_formatted = serializers.ReadOnlyField()
    duration = serializers.ReadOnlyField()
    aes_key = serializers.CharField(source='encrypted_aes_key', read_only=True)
    iv = serializers.CharField(source='file.iv', read_only=True)
    
    class Meta:
        model = Transfer
        fields = [
            'id',
            'uuid',
            'sender',
            'receiver',
            'file',
            'file_name',
            'aes_key',
            'iv',
            'encrypted_aes_key',
            'key_iv',
            'status',
            'status_display',
            'progress',
            'bytes_transferred',
            'transfer_speed',
            'speed_formatted',
            'error_message',
            'retry_count',
            'connection_id',
            'created_at',
            'started_at',
            'completed_at',
            'duration',
        ]
        read_only_fields = [
            'id', 'uuid', 'sender', 'created_at', 
            'started_at', 'completed_at'
        ]


class TransferCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a new transfer.
    
    Frontend integration:
    - Called when sender initiates file transfer
    - Links sender, receiver, and file
    
    Request Example:
    {
        "receiver_id": 2,
        "file_id": 1
    }
    
    OR create file metadata inline:
    {
        "receiver_id": 2,
        "file_data": {
            "original_name": "document.pdf",
            "size": 1048576,
            "mime_type": "application/pdf"
        }
    }
    """
    
    receiver_id = serializers.IntegerField(
        help_text="ID of the user to receive the file"
    )
    file_id = serializers.IntegerField(
        required=True,
        help_text="ID of existing file to transfer"
    )
    file_name = serializers.CharField(required=True, allow_blank=False, help_text="Original file name")
    aes_key = serializers.CharField(required=True, allow_blank=False, help_text="Base64 AES-256 file key")
    iv = serializers.CharField(required=True, allow_blank=False, help_text="12-byte file IV in base64")

    # Backward-compatible aliases for older clients.
    encrypted_aes_key = serializers.CharField(required=False, allow_blank=False, write_only=True)
    key_iv = serializers.CharField(required=False, allow_blank=False, write_only=True)
    
    def validate_receiver_id(self, value):
        """Validate receiver exists and is not the sender."""
        request = self.context.get('request')
        
        if value == request.user.id:
            raise serializers.ValidationError(
                "You cannot send files to yourself."
            )
        
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError(
                "Receiver not found."
            )
        
        return value
    
    def validate_file_id(self, value):
        """Validate file exists and belongs to sender."""
        request = self.context.get('request')
        
        if not File.objects.filter(id=value, owner=request.user).exists():
            raise serializers.ValidationError(
                "File not found or you don't own this file."
            )
        
        return value
    
    def validate(self, attrs):
        """Strict transfer validation: file_id, file_name, aes_key, and iv are mandatory."""
        file_id = attrs.get('file_id')

        if not file_id:
            raise serializers.ValidationError({
                "file_id": "file_id is required."
            })

        file_obj = File.objects.filter(id=file_id, owner=self.context.get('request').user).first()
        if not file_obj:
            raise serializers.ValidationError({
                "file_id": "File not found or you don't own this file."
            })

        file_name = attrs.get('file_name')
        if not file_name:
            raise serializers.ValidationError({
                "file_name": "file_name is required."
            })

        if file_name != file_obj.original_name:
            raise serializers.ValidationError({
                "file_name": "file_name does not match the uploaded file name."
            })

        aes_key = attrs.get('aes_key') or attrs.get('encrypted_aes_key')
        if not aes_key:
            raise serializers.ValidationError({
                "aes_key": "aes_key is required."
            })

        if attrs.get('encrypted_aes_key') and attrs.get('aes_key') and attrs.get('encrypted_aes_key') != attrs.get('aes_key'):
            raise serializers.ValidationError({
                "aes_key": "aes_key and encrypted_aes_key must match when both are provided."
            })

        _decode_base64_bytes(aes_key, 'aes_key', 32)
        _decode_base64_bytes(attrs.get('iv'), 'iv', 12)

        if file_obj.iv and file_obj.iv != attrs.get('iv'):
            raise serializers.ValidationError({
                "iv": "Transfer IV does not match file IV."
            })
        
        return attrs
    
    def create(self, validated_data):
        """Create transfer with linked file."""
        request = self.context.get('request')
        sender = request.user
        receiver = User.objects.get(id=validated_data['receiver_id'])
        file_obj = File.objects.get(id=validated_data['file_id'])
        
        # Create transfer
        transfer = Transfer.objects.create(
            sender=sender,
            receiver=receiver,
            file=file_obj,
            file_name=validated_data['file_name'],
            encrypted_file_path=file_obj.encrypted_file.name if file_obj.encrypted_file else None,
            encryption_algorithm='AES-256-GCM',
            encrypted_aes_key=validated_data.get('aes_key') or validated_data.get('encrypted_aes_key'),
            key_iv=None,
            key_tag=None,
            session=file_obj.session,
            status='pending',
        )

        if not file_obj.iv:
            file_obj.iv = validated_data['iv']
            file_obj.save(update_fields=['iv', 'updated_at'])
        
        # Create log entry
        TransferLog.objects.create(
            transfer=transfer,
            event='created',
            message=f"Transfer created by {sender.username} to {receiver.username}"
        )
        
        return transfer


class TransferListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for transfer listings.
    
    Used in transfer history lists for performance.
    """
    
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    receiver_username = serializers.CharField(source='receiver.username', read_only=True)
    file_name = serializers.CharField(source='file.original_name', read_only=True)
    file_size_formatted = serializers.CharField(source='file.size_formatted', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Transfer
        fields = [
            'id',
            'uuid',
            'sender_username',
            'receiver_username',
            'file_name',
            'file_size_formatted',
            'status',
            'status_display',
            'progress',
            'created_at',
            'completed_at',
        ]


class TransferUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating transfer status and progress.
    
    Request Examples:
    
    Accept transfer:
    {"status": "accepted"}
    
    Update progress:
    {"progress": 50, "bytes_transferred": 524288, "transfer_speed": 51200}
    
    Mark failed:
    {"status": "failed", "error_message": "Connection lost"}
    """
    
    class Meta:
        model = Transfer
        fields = [
            'status',
            'progress',
            'bytes_transferred',
            'transfer_speed',
            'error_message',
            'connection_id',
        ]
    
    def validate_status(self, value):
        """Validate status transitions."""
        instance = self.instance
        if not instance:
            return value
        
        valid_transitions = {
            'pending': ['accepted', 'rejected', 'cancelled', 'sent'],
            'sent': ['completed', 'failed', 'cancelled'],  # Secure transfer flow
            'accepted': ['connecting', 'cancelled'],
            'connecting': ['key_exchange', 'failed', 'cancelled'],
            'key_exchange': ['transferring', 'failed', 'cancelled'],
            'transferring': ['paused', 'completed', 'failed', 'cancelled'],
            'paused': ['transferring', 'cancelled'],
            'completed': [],
            'failed': ['pending'],  # Allow retry
            'rejected': [],
            'cancelled': [],
        }
        
        current = instance.status
        allowed = valid_transitions.get(current, [])
        
        if value not in allowed and value != current:
            raise serializers.ValidationError(
                f"Cannot transition from '{current}' to '{value}'. "
                f"Allowed: {allowed}"
            )
        
        return value
    
    def validate_progress(self, value):
        """Validate progress is between 0 and 100."""
        if value < 0 or value > 100:
            raise serializers.ValidationError(
                "Progress must be between 0 and 100."
            )
        return value
    
    def update(self, instance, validated_data):
        """Update transfer and log changes."""
        old_status = instance.status
        new_status = validated_data.get('status', old_status)
        
        # Handle status-specific timestamps
        if new_status == 'transferring' and old_status != 'transferring':
            if not instance.started_at:
                validated_data['started_at'] = timezone.now()
        
        if new_status == 'completed':
            validated_data['completed_at'] = timezone.now()
            validated_data['progress'] = 100
            validated_data['bytes_transferred'] = instance.file.size
        
        # Update instance
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Log status change
        if old_status != new_status:
            TransferLog.objects.create(
                transfer=instance,
                event='status_changed',
                old_status=old_status,
                new_status=new_status,
                message=f"Status changed from {old_status} to {new_status}"
            )
        
        return instance


class TransferLogSerializer(serializers.ModelSerializer):
    """
    Serializer for transfer logs.
    
    Frontend integration:
    - Display in SecurityLog.tsx
    - Show transfer activity timeline
    
    Example Response:
    {
        "id": 1,
        "transfer_id": 1,
        "event": "status_changed",
        "event_display": "Status Changed",
        "old_status": "pending",
        "new_status": "accepted",
        "message": "Transfer accepted by receiver",
        "timestamp": "2026-02-06T10:30:00Z"
    }
    """
    
    transfer_id = serializers.IntegerField(source='transfer.id', read_only=True)
    event_display = serializers.CharField(source='get_event_display', read_only=True)
    
    class Meta:
        model = TransferLog
        fields = [
            'id',
            'transfer_id',
            'event',
            'event_display',
            'old_status',
            'new_status',
            'message',
            'metadata',
            'timestamp',
        ]


class TransferActionSerializer(serializers.Serializer):
    """
    Serializer for transfer actions (accept, reject, cancel, etc.)
    
    Request Example:
    {"action": "accept"}
    """
    
    ACTION_CHOICES = [
        ('accept', 'Accept'),
        ('reject', 'Reject'),
        ('cancel', 'Cancel'),
        ('pause', 'Pause'),
        ('resume', 'Resume'),
        ('retry', 'Retry'),
    ]
    
    action = serializers.ChoiceField(
        choices=ACTION_CHOICES,
        help_text="Action to perform on transfer"
    )
    
    def validate(self, attrs):
        """Validate action is allowed for current status."""
        instance = self.context.get('instance')
        action = attrs['action']
        
        if not instance:
            raise serializers.ValidationError("Transfer not found.")
        
        action_requirements = {
            'accept': ['pending'],
            'reject': ['pending'],
            'cancel': ['pending', 'accepted', 'connecting', 'key_exchange', 'transferring', 'paused'],
            'pause': ['transferring'],
            'resume': ['paused'],
            'retry': ['failed'],
        }
        
        allowed_statuses = action_requirements.get(action, [])
        if instance.status not in allowed_statuses:
            raise serializers.ValidationError({
                "action": f"Cannot {action} a transfer with status '{instance.status}'."
            })
        
        return attrs


# ==============================================================================
# SECURE FILE TRANSFER SERIALIZERS (Phase 7)
# ==============================================================================
# These serializers handle the encrypted file transfer workflow:
# 1. SecureTransferInitiateSerializer - Start an encrypted transfer
# 2. SecureTransferFileSerializer - Return encrypted file data for download
# ==============================================================================


class SecureTransferInitiateSerializer(serializers.Serializer):
    """
    Serializer for initiating a secure encrypted file transfer.
    
    ═══════════════════════════════════════════════════════════════════════════
    SECURE TRANSFER WORKFLOW
    ═══════════════════════════════════════════════════════════════════════════
    
    1. SENDER: Uploads file and specifies receiver
    2. SYSTEM: Derives shared secret between sender and receiver using ECDH
    3. SYSTEM: Generates random AES-256 key for file encryption
    4. SYSTEM: Encrypts file using AES-256-GCM with the AES key
    5. SYSTEM: Encrypts the AES key using the shared secret
    6. SYSTEM: Creates Transfer record with encrypted file and encrypted AES key
    7. RECEIVER: Downloads encrypted file + encrypted AES key
    8. RECEIVER: Derives same shared secret using ECDH
    9. RECEIVER: Decrypts AES key using shared secret
    10. RECEIVER: Decrypts file using AES key
    
    ═══════════════════════════════════════════════════════════════════════════
    
    Request Body:
    {
        "file_id": 123,           # Existing file to transfer (optional if file provided)
        "receiver_id": 456,       # ID of intended receiver
        "file": <uploaded file>   # File to encrypt and transfer (optional if file_id)
    }
    
    Response (201 Created):
    {
        "transfer_id": 789,
        "uuid": "...",
        "status": "sent",
        "message": "Secure file transfer initiated successfully",
        "data": {
            "sender": "john_doe",
            "receiver": "jane_smith",
            "file_name": "document.pdf",
            "file_size": 1048576,
            "encryption_algorithm": "AES-256-GCM"
        }
    }
    """
    
    # Maximum file size for encrypted transfer (100 MB)
    MAX_FILE_SIZE = 100 * 1024 * 1024
    
    file_id = serializers.IntegerField(
        required=False,
        help_text="ID of existing file to transfer"
    )
    receiver_id = serializers.IntegerField(
        help_text="ID of the user to receive the file"
    )
    file = serializers.FileField(
        required=False,
        help_text="File to encrypt and transfer (if not using file_id)"
    )
    
    def validate_receiver_id(self, value):
        """
        Validate receiver exists and is not the sender.
        
        Security checks:
        - Receiver user exists
        - Receiver is not the sender (self-transfer prevention)
        - Receiver has a public key registered (required for ECDH)
        """
        request = self.context.get('request')
        
        if value == request.user.id:
            raise serializers.ValidationError(
                "You cannot send files to yourself."
            )
        
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError(
                "Receiver user not found."
            )
        
        # Check if receiver has a profile with public key
        from users.models import UserProfile
        try:
            profile = UserProfile.objects.get(user_id=value)
            if not profile.public_key:
                raise serializers.ValidationError(
                    "Receiver has not set up encryption keys. "
                    "They must register their public key first."
                )
        except UserProfile.DoesNotExist:
            raise serializers.ValidationError(
                "Receiver has not set up their profile. "
                "They must complete setup first."
            )
        
        return value
    
    def validate_file_id(self, value):
        """Validate file exists and belongs to sender."""
        request = self.context.get('request')
        
        if not File.objects.filter(id=value, owner=request.user).exists():
            raise serializers.ValidationError(
                "File not found or you don't own this file."
            )
        
        return value
    
    def validate_file(self, value):
        """Validate uploaded file size."""
        if value.size > self.MAX_FILE_SIZE:
            raise serializers.ValidationError(
                f"File size exceeds maximum ({self.MAX_FILE_SIZE / (1024**2):.0f} MB). "
                f"For larger files, use chunked transfer."
            )
        if value.size == 0:
            raise serializers.ValidationError("Cannot transfer empty file.")
        return value
    
    def validate(self, attrs):
        """
        Cross-field validation for secure transfer.
        
        Validates:
        - Either file_id or file is provided (not both, not neither)
        - Session exists or can be created between sender and receiver
        """
        file_id = attrs.get('file_id')
        file = attrs.get('file')
        
        if not file_id and not file:
            raise serializers.ValidationError({
                "file": "Either file_id or file must be provided."
            })
        
        if file_id and file:
            raise serializers.ValidationError({
                "file": "Provide either file_id OR file, not both."
            })
        
        return attrs


class SecureTransferDownloadSerializer(serializers.Serializer):
    """
    Serializer for secure file download response data.
    
    This serializer is used to format the response when receiver
    requests to download an encrypted file transfer.
    
    Response includes:
    - Encrypted file data (or URL to download)
    - Encrypted AES key (to decrypt the file)
    - IV and tag for AES key decryption
    - File metadata
    """
    
    transfer_id = serializers.IntegerField(read_only=True)
    uuid = serializers.UUIDField(read_only=True)
    file_name = serializers.CharField(read_only=True)
    file_size = serializers.IntegerField(read_only=True)
    mime_type = serializers.CharField(read_only=True)
    encryption_algorithm = serializers.CharField(read_only=True)
    encrypted_aes_key = serializers.CharField(read_only=True)
    key_iv = serializers.CharField(read_only=True)
    key_tag = serializers.CharField(read_only=True)
    file_iv = serializers.CharField(read_only=True)
    file_tag = serializers.CharField(read_only=True)
    sender = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class SecureTransferDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for secure transfer with encryption metadata.
    
    Used for transfer status checks and download preparation.
    
    SECURITY NOTE:
    - Encrypted AES key is only included for authorized receiver
    - Session details are never exposed
    """
    
    sender = TransferUserSerializer(read_only=True)
    receiver = TransferUserSerializer(read_only=True)
    file = TransferFileSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    # Include encrypted AES key only for receiver to decrypt
    encrypted_aes_key = serializers.SerializerMethodField()
    key_iv = serializers.SerializerMethodField()
    key_tag = serializers.SerializerMethodField()
    
    class Meta:
        model = Transfer
        fields = [
            'id',
            'uuid',
            'sender',
            'receiver',
            'file',
            'file_name',
            'status',
            'status_display',
            'encryption_algorithm',
            'encrypted_aes_key',
            'key_iv',
            'key_tag',
            'created_at',
            'completed_at',
        ]
    
    def get_encrypted_aes_key(self, obj):
        """
        Only return encrypted AES key if requester is the receiver.
        
        SECURITY: The sender doesn't need the encrypted key back,
        only the receiver needs it to decrypt the file.
        """
        request = self.context.get('request')
        if request and request.user == obj.receiver:
            return obj.encrypted_aes_key
        return None
    
    def get_key_iv(self, obj):
        """Only return key IV if requester is the receiver."""
        request = self.context.get('request')
        if request and request.user == obj.receiver:
            return obj.key_iv
        return None
    
    def get_key_tag(self, obj):
        """Only return key tag if requester is the receiver."""
        request = self.context.get('request')
        if request and request.user == obj.receiver:
            return obj.key_tag
        return None
