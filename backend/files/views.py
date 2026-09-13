"""
File views for file metadata management.
"""

import base64
import hashlib
import logging
from django.core.files.base import ContentFile
from django.http import FileResponse
from django.utils import timezone
from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404

from .models import File, FileChunk
from .serializers import (
    FileSerializer,
    FileCreateSerializer,
    FileListSerializer,
    FileChunkSerializer,
    FileChunkCreateSerializer,
    FileUploadSerializer,
    SecureFileUploadSerializer,
)

logger = logging.getLogger(__name__)


def _decode_iv_for_validation(iv_raw):
    """Decode IV from base64 or comma-separated bytes and enforce 12-byte nonce."""
    if iv_raw is None:
        raise ValueError('IV missing')

    value = str(iv_raw).strip()
    if not value:
        raise ValueError('IV missing')

    if ',' in value:
        try:
            parts = [int(part.strip()) for part in value.split(',') if part.strip()]
        except ValueError as error:
            raise ValueError('Invalid IV format') from error

        iv_bytes = bytes(parts)
    else:
        try:
            padded = value + ('=' * ((4 - len(value) % 4) % 4))
            iv_bytes = base64.b64decode(padded, validate=True)
        except Exception as error:
            raise ValueError('Invalid IV format') from error

    if len(iv_bytes) != 12:
        raise ValueError('Invalid IV length')

    return iv_bytes


def _user_can_download_file(user, file_obj):
    """
    Academic note:
    Access control is enforced server-side before any file bytes are returned.
    A download is allowed only when the authenticated user is either:
    1. The sender / uploader (file.owner)
    2. The intended receiver bound to the encryption session
    3. The receiver recorded on a transfer linked to this file

    The transfer lookup is required because some flows resolve the receiver
    from the Transfer record even when the file/session relation is not
    sufficient on its own.
    """
    is_owner = file_obj.owner == user
    is_session_receiver = bool(file_obj.session and file_obj.session.receiver == user)
    is_transfer_receiver = file_obj.transfers.filter(receiver=user).exists()
    is_receiver = is_session_receiver or is_transfer_receiver
    return is_owner, is_receiver


def _build_encrypted_file_download_response(file_obj):
    """Return encrypted bytes only. Plaintext is never returned by backend."""
    file_obj.encrypted_file.open('rb')
    response = FileResponse(
        file_obj.encrypted_file,
        as_attachment=True,
        filename=f"{file_obj.uuid}.enc",
        content_type='application/octet-stream',
    )
    response['Content-Disposition'] = f'attachment; filename="{file_obj.uuid}.enc"'
    response['X-Content-Type-Options'] = 'nosniff'
    response['X-Encrypted-Content'] = 'true'
    return response


def _build_download_response(request, file_obj):
    """
    Shared download flow used by all file download endpoints.

    Strict production flow:
    1. Verify requester is sender or intended receiver
    2. Return encrypted bytes only
    3. Never return plaintext from backend
    """
    user = request.user
    is_owner, is_receiver = _user_can_download_file(user, file_obj)

    if not file_obj.encrypted_file:
        logger.error(
            'Download rejected because encrypted_file is missing: user=%s file_id=%s',
            user.id,
            file_obj.id,
        )
        return Response({
            'status': 'error',
            'message': 'No encrypted content available for this file.'
        }, status=status.HTTP_404_NOT_FOUND)

    if not (is_owner or is_receiver):
        logger.warning(
            f"Unauthorized download attempt: user={user.id}, file={file_obj.id}"
        )
        return Response({
            'status': 'error',
            'message': 'You are not authorized to download this file.'
        }, status=status.HTTP_403_FORBIDDEN)

    if not file_obj.is_encrypted:
        return Response({
            'status': 'error',
            'message': 'Backend only serves encrypted content for this endpoint.'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        file_obj.download_count += 1
        if not file_obj.downloaded_at:
            file_obj.downloaded_at = timezone.now()
        file_obj.save(update_fields=['download_count', 'downloaded_at', 'updated_at'])
    except Exception as error:
        logger.warning('Failed to update encrypted download metadata: file=%s error=%s', file_obj.id, str(error))

    return _build_encrypted_file_download_response(file_obj)

    return Response({
        'status': 'error',
        'message': 'No downloadable content is available for this file.'
    }, status=status.HTTP_404_NOT_FOUND)


class FileListCreateView(generics.ListCreateAPIView):
    """
    List user's files or create new file metadata.
    
    GET /api/v1/files/
    POST /api/v1/files/
    
    Frontend integration:
    - Replace mock file list in FileTransfer.tsx
    - Create file metadata when user selects file for transfer
    
    GET Response (200 OK):
    {
        "count": 5,
        "next": null,
        "previous": null,
        "results": [
            {
                "id": 1,
                "uuid": "550e8400-e29b-41d4-a716-446655440000",
                "original_name": "document.pdf",
                "size": 1048576,
                "size_formatted": "1.00 MB",
                "mime_type": "application/pdf",
                "owner_username": "john_doe",
                "uploaded_at": "2026-02-06T10:30:00Z"
            }
        ]
    }
    
    POST Request:
    {
        "original_name": "document.pdf",
        "size": 1048576,
        "mime_type": "application/pdf",
        "checksum": "abc123def456..."
    }
    
    POST Response (201 Created):
    {
        "id": 1,
        "uuid": "550e8400-e29b-41d4-a716-446655440000",
        "name": "document.pdf",
        "original_name": "document.pdf",
        "size": 1048576,
        "size_formatted": "1.00 MB",
        ...
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['original_name', 'mime_type']
    ordering_fields = ['uploaded_at', 'size', 'original_name']
    ordering = ['-uploaded_at']
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return FileCreateSerializer
        return FileListSerializer
    
    def get_queryset(self):
        """Return files owned by current user."""
        return File.objects.filter(owner=self.request.user)
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        file_obj = serializer.save()
        
        # Return full file data
        response_serializer = FileSerializer(file_obj)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class FileDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Get, update, or delete a specific file.
    
    GET /api/v1/files/<id>/
    PUT /api/v1/files/<id>/
    DELETE /api/v1/files/<id>/
    
    Frontend integration:
    - Get file details for transfer preview
    - Delete file after successful transfer (optional)
    
    GET Response (200 OK):
    {
        "id": 1,
        "uuid": "550e8400-e29b-41d4-a716-446655440000",
        "name": "document.pdf",
        "original_name": "document.pdf",
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
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = FileSerializer
    
    def get_queryset(self):
        """Return files owned by current user."""
        return File.objects.filter(owner=self.request.user)


class FileByUUIDView(generics.RetrieveAPIView):
    """
    Get file by UUID.
    
    GET /api/v1/files/uuid/<uuid>/
    
    Frontend integration:
    - Used when sharing file links via UUID
    - Receiver can get file info before accepting transfer
    
    SECURITY: Only the file owner OR the intended receiver (via session)
    can access file metadata. This prevents unauthorized information disclosure.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = FileSerializer
    lookup_field = 'uuid'
    
    def get_queryset(self):
        """
        Return files that the current user is authorized to view.
        
        A user can view a file if:
        1. They are the owner (uploader)
        2. They are the intended receiver (session.receiver)
        """
        from django.db.models import Q
        user = self.request.user
        
        return File.objects.filter(
            Q(owner=user) |  # Owner can always see their files
            Q(session__receiver=user, session__is_active=True)  # Receiver of active session
        ).distinct()


class FileUploadView(APIView):
    """
    Direct file upload (for non-P2P scenarios).
    
    POST /api/v1/files/upload/
    
    Content-Type: multipart/form-data
    
    Note: For P2P transfers, use FileListCreateView to create metadata only.
    This endpoint is for direct server-side uploads.
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            logger.error('Encrypted file upload rejected: no file provided by user=%s', request.user.id)
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        original_name = request.data.get('original_filename')
        if original_name is None or str(original_name).strip() == '':
            uploaded_name = getattr(uploaded_file, 'name', '') or ''
            original_name = uploaded_name[:-4] if uploaded_name.endswith('.enc') else uploaded_name
        original_name = str(original_name).strip()
        if not original_name:
            return Response({'error': 'Original filename missing'}, status=status.HTTP_400_BAD_REQUEST)

        hasher = hashlib.sha256()
        for chunk in uploaded_file.chunks():
            hasher.update(chunk)
        checksum = hasher.hexdigest()
        try:
            uploaded_file.seek(0)
        except Exception:
            pass

        logger.info(
            'Uploading encrypted file for storage: user=%s filename=%s size=%s',
            request.user.id,
            original_name,
            uploaded_file.size,
        )

        file_obj = File.objects.create(
            name=original_name,
            original_name=original_name,
            size=uploaded_file.size,
            mime_type='application/octet-stream',
            checksum=checksum,
            is_encrypted=True,
            encryption_algorithm='AES-256-GCM',
            owner=request.user,
            encrypted_file=uploaded_file,
            iv=None,
            tag=None,
            file_path=None,
        )

        logger.info('Encrypted file stored successfully: file_id=%s encrypted_file=%s', file_obj.id, bool(file_obj.encrypted_file))

        return Response({
            "id": file_obj.id,
        }, status=status.HTTP_201_CREATED)


class FileChunkListView(generics.ListCreateAPIView):
    """
    List or create file chunks.
    
    GET /api/v1/files/<file_id>/chunks/
    POST /api/v1/files/<file_id>/chunks/
    
    Frontend integration:
    - Track chunk progress in ChunkProgress.tsx
    - Create chunk records when splitting large files
    
    GET Response:
    {
        "count": 10,
        "results": [
            {
                "id": 1,
                "chunk_number": 1,
                "total_chunks": 10,
                "size": 1048576,
                "status": "completed",
                "progress_percentage": 10.0
            }
        ]
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return FileChunkCreateSerializer
        return FileChunkSerializer
    
    def get_queryset(self):
        file_id = self.kwargs.get('file_id')
        return FileChunk.objects.filter(
            file_id=file_id,
            file__owner=self.request.user
        )
    
    def create(self, request, *args, **kwargs):
        file_id = self.kwargs.get('file_id')
        file_obj = get_object_or_404(
            File, 
            id=file_id, 
            owner=request.user
        )
        
        data = request.data.copy()
        data['file'] = file_obj.id
        
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        chunk = serializer.save()
        
        response_serializer = FileChunkSerializer(chunk)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class FileChunkUpdateView(generics.UpdateAPIView):
    """
    Update chunk status.
    
    PATCH /api/v1/files/<file_id>/chunks/<chunk_id>/
    
    Frontend integration:
    - Update chunk status during transfer
    - Mark chunks as completed/failed
    
    Request:
    {
        "status": "completed"
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = FileChunkSerializer
    
    def get_queryset(self):
        file_id = self.kwargs.get('file_id')
        return FileChunk.objects.filter(
            file_id=file_id,
            file__owner=self.request.user
        )
    
    def get_object(self):
        queryset = self.get_queryset()
        chunk_id = self.kwargs.get('chunk_id')
        return get_object_or_404(queryset, id=chunk_id)


class FileProgressView(APIView):
    """
    Get file transfer progress.
    
    GET /api/v1/files/<file_id>/progress/
    
    Frontend integration:
    - Display overall file progress
    - Used in progress bars
    
    Response:
    {
        "file_id": 1,
        "file_name": "document.pdf",
        "total_chunks": 10,
        "completed_chunks": 7,
        "failed_chunks": 0,
        "pending_chunks": 3,
        "progress_percentage": 70.0,
        "status": "in_progress"
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, file_id):
        file_obj = get_object_or_404(
            File, 
            id=file_id, 
            owner=request.user
        )
        
        chunks = file_obj.chunks.all()
        total = chunks.count()
        
        if total == 0:
            return Response({
                'file_id': file_obj.id,
                'file_name': file_obj.original_name,
                'total_chunks': 0,
                'completed_chunks': 0,
                'failed_chunks': 0,
                'pending_chunks': 0,
                'progress_percentage': 0,
                'status': 'no_chunks'
            })
        
        completed = chunks.filter(status='completed').count()
        failed = chunks.filter(status='failed').count()
        pending = chunks.filter(status='pending').count()
        transferring = chunks.filter(status='transferring').count()
        
        # Determine overall status
        if failed > 0:
            status_str = 'has_failures'
        elif completed == total:
            status_str = 'completed'
        elif transferring > 0:
            status_str = 'transferring'
        elif pending > 0:
            status_str = 'pending'
        else:
            status_str = 'unknown'
        
        progress = (completed / total) * 100 if total > 0 else 0
        
        return Response({
            'file_id': file_obj.id,
            'file_name': file_obj.original_name,
            'total_chunks': total,
            'completed_chunks': completed,
            'failed_chunks': failed,
            'pending_chunks': pending,
            'transferring_chunks': transferring,
            'progress_percentage': round(progress, 2),
            'status': status_str
        })


class SecureFileUploadView(APIView):
    """
    Secure encrypted file upload with AES-256-GCM.
    
    POST /api/v1/files/secure-upload/
    
    ═══════════════════════════════════════════════════════════════════════════
    AES-256-GCM ENCRYPTION FLOW
    ═══════════════════════════════════════════════════════════════════════════
    
    1. AUTHENTICATION: User must be authenticated via JWT
    2. VALIDATION: Verify active session exists with receiver
    3. KEY DERIVATION: Derive AES-256 key from shared secret using HKDF
       - Input: SessionKey.shared_secret (from ECDH exchange)
       - Output: 32-byte AES key (NEVER stored in database)
    4. ENCRYPTION: Encrypt file bytes with AES-256-GCM
       - Generate random 12-byte IV (nonce)
       - Encrypt plaintext → ciphertext
       - Generate 16-byte authentication tag
    5. STORAGE: Store encrypted data
       - encrypted_file: Ciphertext (FileField)
       - iv: Initialization vector (hex-encoded)
       - tag: Authentication tag (hex-encoded)
       - PLAINTEXT IS NEVER STORED
    6. RESPONSE: Return file_id for receiver to download
    
    ═══════════════════════════════════════════════════════════════════════════
    WHY AES-GCM?
    ═══════════════════════════════════════════════════════════════════════════
    
    AES-GCM (Galois/Counter Mode) provides:
    - CONFIDENTIALITY: AES-256 encryption
    - INTEGRITY: Built-in authentication tag
    - AUTHENTICITY: Tag verification prevents tampering
    
    Alternative modes like CBC require separate HMAC for integrity.
    GCM combines encryption + authentication in one operation.
    
    ═══════════════════════════════════════════════════════════════════════════
    
    Request Headers:
        Authorization: Bearer <jwt_token>
        Content-Type: multipart/form-data
    
    Request Body:
        file: <uploaded file>
        receiver_id: <int> (must have active session)
    
    Success Response (201):
    {
        "status": "success",
        "message": "File encrypted and stored securely",
        "data": {
            "file_id": 123,
            "uuid": "...",
            "original_name": "document.pdf",
            "size": 1048576,
            "encryption_algorithm": "AES-256-GCM",
            "receiver_id": 456
        }
    }
    
    Error Responses:
    - 400: Validation error (no session, invalid receiver, etc.)
    - 401: Unauthorized (no/invalid JWT)
    - 500: Encryption failure (logged, generic message to user)
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        """
        Handle secure encrypted file upload.
        
        This method:
        1. Validates request data via serializer
        2. Derives AES key from session's shared secret
        3. Encrypts file using AES-256-GCM
        4. Stores encrypted file with IV and tag
        5. Returns file metadata (never the key!)
        """
        # Step 1: Validate request via serializer
        serializer = SecureFileUploadSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        # Extract validated data
        uploaded_file = serializer.validated_data['file']
        receiver_id = serializer.validated_data['receiver_id']
        session = serializer.validated_data['session']  # Attached by serializer
        
        try:
            # Step 2: Read file into memory
            # SECURITY: File bytes are held in memory only during encryption
            file_bytes = uploaded_file.read()
            
            # Calculate checksum of ORIGINAL file (before encryption)
            checksum = hashlib.sha256(file_bytes).hexdigest()
            
            # Step 3: Decode shared secret from session
            # SessionKey.shared_secret is base64-encoded
            shared_secret = base64.b64decode(session.shared_secret)
            
            # Step 4: Derive AES-256 key using HKDF
            # CRITICAL: This key is NEVER stored, only used in memory
            from crypto.utils import derive_aes_session_key, encrypt_file
            
            aes_key = derive_aes_session_key(
                shared_secret=shared_secret,
                context=f"file-encryption:{session.id}".encode('utf-8')
            )
            
            # Step 5: Encrypt file using AES-256-GCM
            # Returns: (ciphertext, iv, tag)
            ciphertext, iv, tag = encrypt_file(file_bytes, aes_key)
            
            # Step 6: Encode IV and tag as hex for storage
            iv_hex = iv.hex()
            tag_hex = tag.hex()
            
            # Step 7: Create encrypted file content
            # Django ContentFile wraps bytes for FileField storage
            encrypted_content = ContentFile(
                ciphertext,
                name=f"{uploaded_file.name}.enc"
            )
            
            # Step 8: Create File record with encrypted data
            file_obj = File.objects.create(
                name=uploaded_file.name,
                original_name=uploaded_file.name,
                size=len(file_bytes),  # Original size
                mime_type=uploaded_file.content_type or 'application/octet-stream',
                checksum=checksum,
                is_encrypted=True,
                encryption_algorithm='AES-256-GCM',
                encrypted_file=encrypted_content,
                iv=iv_hex,
                tag=tag_hex,
                is_decrypted=False,
                session=session,
                owner=request.user,
            )
            
            # SECURITY: Clear sensitive data from memory
            # Python doesn't guarantee immediate clearing, but this helps
            del file_bytes
            del aes_key
            del shared_secret
            del ciphertext
            
            # Log success (no sensitive data!)
            logger.info(
                f"Encrypted file uploaded: "
                f"file_id={file_obj.id}, "
                f"user={request.user.id}, "
                f"receiver={receiver_id}, "
                f"size={file_obj.size}"
            )
            
            # Step 9: Return success response
            return Response({
                'status': 'success',
                'message': 'File encrypted and stored securely',
                'data': {
                    'file_id': file_obj.id,
                    'uuid': str(file_obj.uuid),
                    'original_name': file_obj.original_name,
                    'size': file_obj.size,
                    'size_formatted': file_obj.size_formatted,
                    'encryption_algorithm': file_obj.encryption_algorithm,
                    'checksum': checksum,
                    'receiver_id': receiver_id,
                    'session_id': session.id,
                    'uploaded_at': file_obj.uploaded_at.isoformat()
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            # Log the actual error for debugging (server-side only)
            logger.error(
                f"Encrypted file upload failed: "
                f"user={request.user.id}, "
                f"receiver={receiver_id}, "
                f"error={str(e)}"
            )
            
            # SECURITY: Return generic error message to prevent information leakage
            return Response({
                'status': 'error',
                'message': 'File encryption failed. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SecureFileDownloadView(APIView):
    """
    Secure encrypted file download with AES-256-GCM decryption.
    
    GET /api/v1/files/<uuid>/secure-download/
    
    ═══════════════════════════════════════════════════════════════════════════
    AES-256-GCM DECRYPTION FLOW
    ═══════════════════════════════════════════════════════════════════════════
    
    1. AUTHENTICATION: User must be authenticated via JWT
    2. AUTHORIZATION: Only file owner OR intended receiver can access
    3. SESSION VALIDATION: Session must be active and not expired
    4. KEY DERIVATION: Derive AES-256 key from shared secret using HKDF
       - Same derivation as Phase 5 encryption (deterministic)
       - Both parties derive identical key from shared secret
    5. DECRYPTION: Decrypt ciphertext using AES-256-GCM
       - Read encrypted file from storage
       - Convert IV and tag from hex
       - Decrypt and verify authentication tag
       - If tag invalid → tampering detected → 400 error
    6. RESPONSE: Return decrypted file as download
       - FileResponse with proper Content-Disposition header
       - Original filename preserved
       - DECRYPTED DATA NEVER STORED ON DISK
    
    ═══════════════════════════════════════════════════════════════════════════
    WHY GCM ENSURES INTEGRITY
    ═══════════════════════════════════════════════════════════════════════════
    
    AES-GCM generates a 128-bit authentication tag during encryption:
    - Tag = f(key, IV, ciphertext, AAD)
    - During decryption, GCM recomputes the tag
    - If recomputed tag ≠ stored tag → InvalidTag exception
    - This detects ANY modification to ciphertext, IV, or associated data
    
    ═══════════════════════════════════════════════════════════════════════════
    ACCESS CONTROL
    ═══════════════════════════════════════════════════════════════════════════
    
    Who can download?
    1. File owner (sender) - uploaded the file
    2. Session receiver - intended recipient via ECDH session
    
    Both parties share the same ECDH-derived secret, so both can:
    - Derive the same AES-256 key
    - Decrypt the file
    
    ═══════════════════════════════════════════════════════════════════════════
    
    Request Headers:
        Authorization: Bearer <jwt_token>
    
    Success Response (200):
        Binary file download with headers:
        - Content-Type: <original mime type>
        - Content-Disposition: attachment; filename="original_filename.ext"
    
    Error Responses:
        - 400: Decryption failed (tag verification failed, corrupted data)
        - 403: Forbidden (not authorized, session invalid/expired)
        - 404: File not found
        - 500: Server error
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, uuid):
        try:
            file_obj = File.objects.select_related('session', 'owner').get(uuid=uuid)
        except File.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'File not found.'
            }, status=status.HTTP_404_NOT_FOUND)

        return _build_download_response(request, file_obj)


class FileDownloadView(APIView):
    """
    Download file by database ID.

    GET /api/v1/files/<file_id>/download/

    This is the receiver-facing endpoint used by the React dashboard.
    It performs the same security checks as the UUID secure-download route,
    then returns the file as a browser attachment so the OS stores it in the
    user's default Downloads folder.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, file_id):
        file_obj = get_object_or_404(
            File.objects.select_related('session', 'owner'),
            id=file_id,
        )
        return _build_download_response(request, file_obj)
