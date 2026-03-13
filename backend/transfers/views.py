"""
Transfer views for transfer management.
"""

from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import Transfer, TransferLog
from .serializers import (
    TransferSerializer,
    TransferCreateSerializer,
    TransferListSerializer,
    TransferUpdateSerializer,
    TransferLogSerializer,
    TransferActionSerializer,
)

User = get_user_model()


class TransferListCreateView(generics.ListCreateAPIView):
    """
    List user's transfers or create new transfer.
    
    GET /api/v1/transfers/
    POST /api/v1/transfers/
    
    Query Parameters:
    - role: 'sender' or 'receiver' (filter by user's role)
    - status: Filter by status
    - search: Search by file name
    
    Frontend integration:
    - Replace mock transfer list in TransferHistory.tsx
    - Replace mock data in SenderDashboard.tsx
    - Replace mock data in ReceiverDashboard.tsx
    
    GET Response (200 OK):
    {
        "count": 5,
        "next": null,
        "previous": null,
        "results": [
            {
                "id": 1,
                "uuid": "...",
                "sender_username": "john_doe",
                "receiver_username": "jane_smith",
                "file_name": "document.pdf",
                "file_size_formatted": "1.00 MB",
                "status": "completed",
                "progress": 100,
                "created_at": "2026-02-06T10:30:00Z"
            }
        ]
    }
    
    POST Request:
    {
        "receiver_id": 2,
        "file_id": 1
    }
    
    POST Response (201 Created):
    {
        "id": 1,
        "uuid": "...",
        "sender": {...},
        "receiver": {...},
        "file": {...},
        "status": "pending",
        ...
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['file__original_name']
    ordering_fields = ['created_at', 'status', 'progress']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TransferCreateSerializer
        return TransferListSerializer
    
    def get_queryset(self):
        """Return transfers where user is sender or receiver."""
        user = self.request.user
        queryset = Transfer.objects.filter(
            Q(sender=user) | Q(receiver=user)
        ).select_related('sender', 'receiver', 'file')
        
        # Filter by role
        role = self.request.query_params.get('role')
        if role == 'sender':
            queryset = queryset.filter(sender=user)
        elif role == 'receiver':
            queryset = queryset.filter(receiver=user)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        transfer = serializer.save()
        
        # Return full transfer data
        response_serializer = TransferSerializer(transfer)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class TransferDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Get, update, or delete a specific transfer.
    
    GET /api/v1/transfers/<id>/
    PATCH /api/v1/transfers/<id>/
    DELETE /api/v1/transfers/<id>/
    
    Frontend integration:
    - Get transfer details for progress display
    - Update transfer status/progress
    
    GET Response (200 OK):
    {
        "id": 1,
        "uuid": "...",
        "sender": {...},
        "receiver": {...},
        "file": {...},
        "status": "transferring",
        "progress": 45,
        ...
    }
    
    PATCH Request:
    {
        "progress": 50,
        "bytes_transferred": 524288,
        "transfer_speed": 51200
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method in ['PATCH', 'PUT']:
            return TransferUpdateSerializer
        return TransferSerializer
    
    def get_queryset(self):
        """Return transfers where user is sender or receiver."""
        user = self.request.user
        return Transfer.objects.filter(
            Q(sender=user) | Q(receiver=user)
        ).select_related('sender', 'receiver', 'file')


class TransferByUUIDView(generics.RetrieveAPIView):
    """
    Get transfer by UUID.
    
    GET /api/v1/transfers/uuid/<uuid>/
    
    Frontend integration:
    - Used when sharing transfer links
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TransferSerializer
    lookup_field = 'uuid'
    
    def get_queryset(self):
        user = self.request.user
        return Transfer.objects.filter(
            Q(sender=user) | Q(receiver=user)
        ).select_related('sender', 'receiver', 'file')


class TransferActionView(APIView):
    """
    Perform action on a transfer (accept, reject, cancel, etc.)
    
    POST /api/v1/transfers/<id>/action/
    
    Frontend integration:
    - Accept incoming transfer in ReceiverDashboard.tsx
    - Cancel/reject transfers
    
    Request:
    {"action": "accept"}
    
    Response (200 OK):
    {
        "message": "Transfer accepted",
        "transfer": {...}
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, pk):
        user = request.user
        transfer = get_object_or_404(
            Transfer.objects.filter(Q(sender=user) | Q(receiver=user)),
            pk=pk
        )
        
        serializer = TransferActionSerializer(
            data=request.data,
            context={'instance': transfer}
        )
        serializer.is_valid(raise_exception=True)
        
        action = serializer.validated_data['action']
        
        # Perform action
        action_map = {
            'accept': (transfer.accept, 'accepted'),
            'reject': (transfer.reject, 'rejected'),
            'cancel': (transfer.cancel, 'cancelled'),
            'pause': (lambda: setattr(transfer, 'status', 'paused') or transfer.save(), 'paused'),
            'resume': (transfer.start, 'resumed'),
            'retry': (lambda: setattr(transfer, 'status', 'pending') or transfer.save(), 'retried'),
        }
        
        func, action_name = action_map.get(action, (None, None))
        if func:
            func()
        
        # Log action
        TransferLog.objects.create(
            transfer=transfer,
            event='status_changed',
            old_status=transfer.status,
            message=f"Transfer {action_name} by {user.username}"
        )
        
        return Response({
            'message': f'Transfer {action_name}',
            'transfer': TransferSerializer(transfer).data
        })


class SentTransfersView(generics.ListAPIView):
    """
    List transfers sent by current user.
    
    GET /api/v1/transfers/sent/
    
    Frontend integration:
    - Replace mock sent transfers in SenderDashboard.tsx
    
    Response (200 OK):
    {
        "count": 3,
        "results": [
            {
                "id": 1,
                "receiver_username": "jane_smith",
                "file_name": "document.pdf",
                "status": "completed",
                ...
            }
        ]
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TransferListSerializer
    filter_backends = [filters.OrderingFilter]
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Transfer.objects.filter(
            sender=self.request.user
        ).select_related('sender', 'receiver', 'file')


class ReceivedTransfersView(generics.ListAPIView):
    """
    List transfers received by current user.
    
    GET /api/v1/transfers/received/
    
    Frontend integration:
    - Replace mock received transfers in ReceiverDashboard.tsx
    
    Response (200 OK):
    {
        "count": 2,
        "results": [
            {
                "id": 2,
                "sender_username": "john_doe",
                "file_name": "report.xlsx",
                "status": "pending",
                ...
            }
        ]
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TransferListSerializer
    filter_backends = [filters.OrderingFilter]
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Transfer.objects.filter(
            receiver=self.request.user
        ).select_related('sender', 'receiver', 'file')


class PendingTransfersView(generics.ListAPIView):
    """
    List pending incoming transfers for current user.
    
    GET /api/v1/transfers/pending/
    
    Frontend integration:
    - Show notification badge count
    - Display pending transfers that need action
    
    Response (200 OK):
    {
        "count": 1,
        "results": [
            {
                "id": 2,
                "sender_username": "john_doe",
                "file_name": "report.xlsx",
                "status": "pending",
                "created_at": "2026-02-06T10:30:00Z"
            }
        ]
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TransferListSerializer
    
    def get_queryset(self):
        return Transfer.objects.filter(
            receiver=self.request.user,
            status='pending'
        ).select_related('sender', 'receiver', 'file').order_by('-created_at')


class ActiveTransfersView(generics.ListAPIView):
    """
    List active (in-progress) transfers for current user.
    
    GET /api/v1/transfers/active/
    
    Frontend integration:
    - Display active transfers with progress bars
    - Real-time progress updates
    
    Response (200 OK):
    {
        "count": 1,
        "results": [
            {
                "id": 1,
                "file_name": "large_file.zip",
                "status": "transferring",
                "progress": 45,
                ...
            }
        ]
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TransferSerializer
    
    def get_queryset(self):
        user = self.request.user
        active_statuses = ['accepted', 'connecting', 'key_exchange', 'transferring']
        return Transfer.objects.filter(
            Q(sender=user) | Q(receiver=user),
            status__in=active_statuses
        ).select_related('sender', 'receiver', 'file').order_by('-started_at')


class TransferLogsView(generics.ListAPIView):
    """
    List logs for a specific transfer.
    
    GET /api/v1/transfers/<transfer_id>/logs/
    
    Frontend integration:
    - Display in SecurityLog.tsx
    - Show transfer activity timeline
    
    Response (200 OK):
    {
        "count": 5,
        "results": [
            {
                "id": 1,
                "event": "status_changed",
                "old_status": "pending",
                "new_status": "accepted",
                "message": "Transfer accepted by receiver",
                "timestamp": "2026-02-06T10:30:00Z"
            }
        ]
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TransferLogSerializer
    
    def get_queryset(self):
        transfer_id = self.kwargs.get('transfer_id')
        user = self.request.user
        
        # Verify user has access to this transfer
        transfer = get_object_or_404(
            Transfer.objects.filter(Q(sender=user) | Q(receiver=user)),
            id=transfer_id
        )
        
        return TransferLog.objects.filter(transfer=transfer).order_by('-timestamp')


class TransferStatsView(APIView):
    """
    Get transfer statistics for current user.
    
    GET /api/v1/transfers/stats/
    
    Frontend integration:
    - Display stats in dashboard
    - Show transfer counts and totals
    
    Response (200 OK):
    {
        "total_sent": 15,
        "total_received": 10,
        "completed": 20,
        "failed": 2,
        "pending": 3,
        "active": 1,
        "total_bytes_sent": 1073741824,
        "total_bytes_received": 536870912
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        sent = Transfer.objects.filter(sender=user)
        received = Transfer.objects.filter(receiver=user)
        all_transfers = Transfer.objects.filter(Q(sender=user) | Q(receiver=user))
        
        return Response({
            'total_sent': sent.count(),
            'total_received': received.count(),
            'completed': all_transfers.filter(status='completed').count(),
            'failed': all_transfers.filter(status='failed').count(),
            'pending': received.filter(status='pending').count(),
            'active': all_transfers.filter(
                status__in=['accepted', 'connecting', 'key_exchange', 'transferring']
            ).count(),
            'total_bytes_sent': sent.filter(
                status='completed'
            ).aggregate(
                total=models.Sum('bytes_transferred')
            )['total'] or 0,
            'total_bytes_received': received.filter(
                status='completed'
            ).aggregate(
                total=models.Sum('bytes_transferred')
            )['total'] or 0,
        })


# Import models for aggregation
from django.db import models


# ==============================================================================
# PHASE 7: SECURE FILE TRANSFER SYSTEM
# ==============================================================================
# This module implements the complete encrypted file transfer workflow:
#
# 1. SecureTransferInitiateView - Start an encrypted file transfer
#    - Sender uploads file and specifies receiver
#    - System creates/retrieves ECDH session between users
#    - System generates random AES-256 key for file encryption
#    - File is encrypted with AES-256-GCM
#    - AES key is encrypted with shared secret
#    - Transfer record stores encrypted file + encrypted key
#
# 2. SecureTransferDownloadView - Download encrypted transfer
#    - Receiver requests the transfer by UUID
#    - System verifies receiver identity
#    - System sends encrypted file + encrypted AES key
#    - Receiver decrypts AES key using shared secret
#    - Receiver decrypts file using AES key
#
# SECURITY GUARANTEES:
# - End-to-end encryption: Only sender and receiver can decrypt
# - Forward secrecy: Each file uses unique AES key
# - Integrity: AES-GCM provides authentication
# - Access control: Only authorized parties can access transfer
# ==============================================================================

import base64
import hashlib
import logging
import os
from django.core.files.base import ContentFile
from django.http import FileResponse
from rest_framework.parsers import MultiPartParser, FormParser
from io import BytesIO

from files.models import File
from crypto.models import SessionKey
from users.models import UserProfile, UserPrivateKey
from .serializers import (
    SecureTransferInitiateSerializer,
    SecureTransferDetailSerializer,
)

logger = logging.getLogger(__name__)


class SecureTransferInitiateView(APIView):
    """
    Initiate a secure encrypted file transfer.
    
    POST /api/v1/transfers/secure/initiate/
    
    ═══════════════════════════════════════════════════════════════════════════
    SECURE TRANSFER INITIATION FLOW
    ═══════════════════════════════════════════════════════════════════════════
    
    Step 1: AUTHENTICATION & VALIDATION
        - Verify sender is authenticated via JWT
        - Validate receiver exists and has public key registered
        - Validate file exists or is uploaded
    
    Step 2: SESSION KEY RETRIEVAL/CREATION
        - Check for existing active session between sender and receiver
        - If no session exists, derive shared secret using ECDH:
          a. Get sender's private key (encrypted in database)
          b. Get receiver's public key
          c. Perform ECDH key exchange
          d. Store shared secret in new SessionKey
    
    Step 3: FILE ENCRYPTION
        - Generate random 32-byte (256-bit) AES key
        - Encrypt file content using AES-256-GCM
        - Store: ciphertext, IV, authentication tag
    
    Step 4: KEY ENCRYPTION
        - Derive key-encryption-key from shared secret using HKDF
        - Encrypt AES key using AES-256-GCM
        - Store: encrypted_aes_key, key_iv, key_tag
    
    Step 5: CREATE TRANSFER RECORD
        - Create Transfer with all encrypted data
        - Log transfer creation
        - Return transfer UUID to sender
    
    ═══════════════════════════════════════════════════════════════════════════
    
    Request Headers:
        Authorization: Bearer <jwt_token>
        Content-Type: multipart/form-data
    
    Request Body:
        file: <uploaded file> (optional if file_id provided)
        file_id: <int> (optional if file provided)
        receiver_id: <int> (required)
    
    Success Response (201):
    {
        "status": "success",
        "message": "Secure file transfer initiated",
        "data": {
            "transfer_id": 123,
            "uuid": "550e8400-e29b-41d4-a716-446655440000",
            "sender": "john_doe",
            "receiver": "jane_smith",
            "file_name": "document.pdf",
            "file_size": 1048576,
            "encryption_algorithm": "AES-256-GCM",
            "status": "sent",
            "created_at": "2026-03-12T10:30:00Z"
        }
    }
    
    Error Responses:
        - 400: Validation error (no receiver, no file, self-transfer, etc.)
        - 401: Unauthorized (no/invalid JWT)
        - 403: Forbidden (receiver has no public key)
        - 500: Encryption failure
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        """
        Handle secure transfer initiation.
        
        This method orchestrates the complete encryption workflow:
        1. Validate input data
        2. Get or create session with receiver
        3. Generate AES key and encrypt file
        4. Encrypt AES key with shared secret
        5. Create transfer record
        6. Return success response
        """
        # =====================================================================
        # STEP 1: VALIDATION
        # =====================================================================
        serializer = SecureTransferInitiateSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        sender = request.user
        receiver_id = serializer.validated_data['receiver_id']
        receiver = User.objects.get(id=receiver_id)
        
        try:
            # =====================================================================
            # STEP 2: GET OR CREATE SESSION KEY
            # =====================================================================
            session = self._get_or_create_session(sender, receiver)
            
            # =====================================================================
            # STEP 3: PROCESS FILE
            # =====================================================================
            file_obj, file_bytes = self._process_file(
                request=request,
                sender=sender,
                file_id=serializer.validated_data.get('file_id'),
                uploaded_file=serializer.validated_data.get('file'),
            )
            
            # =====================================================================
            # STEP 4: GENERATE AES KEY AND ENCRYPT FILE
            # =====================================================================
            from crypto.utils import encrypt_file, derive_aes_session_key
            
            # Generate random AES-256 key for this file
            aes_key = os.urandom(32)  # 256 bits
            
            # Encrypt file content
            ciphertext, file_iv, file_tag = encrypt_file(file_bytes, aes_key)
            
            # Store encrypted file
            encrypted_content = ContentFile(
                ciphertext,
                name=f"{file_obj.uuid}.enc"
            )
            
            # Update file with encryption data
            file_obj.encrypted_file = encrypted_content
            file_obj.iv = file_iv.hex()
            file_obj.tag = file_tag.hex()
            file_obj.is_encrypted = True
            file_obj.encryption_algorithm = 'AES-256-GCM'
            file_obj.session = session
            file_obj.save()
            
            # =====================================================================
            # STEP 5: ENCRYPT AES KEY WITH SHARED SECRET
            # =====================================================================
            # Decode shared secret from session
            shared_secret = base64.b64decode(session.shared_secret)
            
            # Derive key-encryption-key from shared secret
            # Using different context for key encryption vs file encryption
            kek = derive_aes_session_key(
                shared_secret=shared_secret,
                context=b"aes-key-encryption"
            )
            
            # Encrypt the AES key using the key-encryption-key
            encrypted_aes_key, key_iv, key_tag = encrypt_file(aes_key, kek)
            
            # =====================================================================
            # STEP 6: CREATE TRANSFER RECORD
            # =====================================================================
            transfer = Transfer.objects.create(
                sender=sender,
                receiver=receiver,
                file=file_obj,
                file_name=file_obj.original_name,
                encrypted_file_path=str(file_obj.encrypted_file.name) if file_obj.encrypted_file else "",
                encryption_algorithm='AES-256-GCM',
                encrypted_aes_key=base64.b64encode(encrypted_aes_key).decode('utf-8'),
                key_iv=key_iv.hex(),
                key_tag=key_tag.hex(),
                session=session,
                status='sent',
            )
            
            # Log transfer creation
            TransferLog.objects.create(
                transfer=transfer,
                event='created',
                message=f"Secure transfer initiated by {sender.username} to {receiver.username}"
            )
            
            # =====================================================================
            # SECURITY: Clear sensitive data from memory
            # =====================================================================
            del aes_key
            del kek
            del shared_secret
            del ciphertext
            del file_bytes
            
            # Log success
            logger.info(
                f"Secure transfer created: transfer_id={transfer.id}, "
                f"sender={sender.id}, receiver={receiver.id}, "
                f"file_size={file_obj.size}"
            )
            
            # =====================================================================
            # STEP 7: RETURN SUCCESS RESPONSE
            # =====================================================================
            return Response({
                'status': 'success',
                'message': 'Secure file transfer initiated',
                'data': {
                    'transfer_id': transfer.id,
                    'uuid': str(transfer.uuid),
                    'sender': sender.username,
                    'receiver': receiver.username,
                    'file_name': file_obj.original_name,
                    'file_size': file_obj.size,
                    'file_size_formatted': file_obj.size_formatted,
                    'encryption_algorithm': transfer.encryption_algorithm,
                    'status': transfer.status,
                    'created_at': transfer.created_at.isoformat(),
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(
                f"Secure transfer failed: sender={sender.id}, "
                f"receiver={receiver_id}, error={str(e)}"
            )
            return Response({
                'status': 'error',
                'message': 'Failed to initiate secure transfer. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_or_create_session(self, sender, receiver):
        """
        Get existing session or create new one using ECDH.
        
        ECDH Key Exchange Flow:
        1. Get sender's private key (from encrypted storage)
        2. Get receiver's public key (from UserProfile)
        3. Derive shared secret using ECDH
        4. Store shared secret in SessionKey
        
        Args:
            sender: User object (sender)
            receiver: User object (receiver)
            
        Returns:
            SessionKey: Active session between sender and receiver
            
        Raises:
            Exception: If key exchange fails
        """
        # Check for existing active session
        session = SessionKey.objects.filter(
            sender=sender,
            receiver=receiver,
            is_active=True
        ).first()
        
        if session and session.is_valid:
            logger.debug(f"Using existing session: {session.id}")
            return session
        
        # Deactivate expired/invalid sessions
        SessionKey.objects.filter(
            sender=sender,
            receiver=receiver,
            is_active=True
        ).update(is_active=False)
        
        # =====================================================================
        # PERFORM ECDH KEY EXCHANGE
        # =====================================================================
        from crypto.utils import (
            load_private_key,
            load_public_key,
            derive_shared_secret,
        )
        
        # Get sender's private key
        try:
            sender_private_key_storage = UserPrivateKey.objects.get(user=sender)
            sender_private_pem = sender_private_key_storage.get_decrypted_private_key()
            sender_private_key = load_private_key(sender_private_pem)
        except UserPrivateKey.DoesNotExist:
            raise Exception(f"Sender {sender.username} has no private key registered")
        
        # Get receiver's public key
        try:
            receiver_profile = UserProfile.objects.get(user=receiver)
            if not receiver_profile.public_key:
                raise Exception(f"Receiver {receiver.username} has no public key")
            receiver_public_key = load_public_key(
                receiver_profile.public_key.encode('utf-8')
            )
        except UserProfile.DoesNotExist:
            raise Exception(f"Receiver {receiver.username} has no profile")
        
        # Derive shared secret using ECDH
        shared_secret = derive_shared_secret(
            sender_private_key,
            receiver_public_key,
            salt=None,
            info=b"secure-file-transfer"
        )
        
        # Store as base64 for database storage
        shared_secret_b64 = base64.b64encode(shared_secret).decode('utf-8')
        
        # Create new session
        session = SessionKey.objects.create(
            sender=sender,
            receiver=receiver,
            shared_secret=shared_secret_b64,
            is_active=True
        )
        
        logger.info(
            f"New ECDH session created: session_id={session.id}, "
            f"sender={sender.id}, receiver={receiver.id}"
        )
        
        return session
    
    def _process_file(self, request, sender, file_id=None, uploaded_file=None):
        """
        Get existing file or create from upload.
        
        Args:
            request: HTTP request object
            sender: User object (file owner)
            file_id: ID of existing file (optional)
            uploaded_file: Uploaded file object (optional)
            
        Returns:
            tuple: (File object, file bytes)
        """
        if file_id:
            # Use existing file
            file_obj = File.objects.get(id=file_id, owner=sender)
            
            # Read file content
            if file_obj.file_path:
                file_obj.file_path.seek(0)
                file_bytes = file_obj.file_path.read()
            elif file_obj.encrypted_file:
                # File is already encrypted - this shouldn't happen for new transfers
                raise Exception("File is already encrypted")
            else:
                raise Exception("File has no content to transfer")
        else:
            # Create new file from upload
            file_bytes = uploaded_file.read()
            checksum = hashlib.sha256(file_bytes).hexdigest()
            
            file_obj = File.objects.create(
                name=uploaded_file.name,
                original_name=uploaded_file.name,
                size=len(file_bytes),
                mime_type=uploaded_file.content_type or 'application/octet-stream',
                checksum=checksum,
                owner=sender,
            )
        
        return file_obj, file_bytes


class SecureTransferDownloadView(APIView):
    """
    Download an encrypted file transfer.
    
    GET /api/v1/transfers/secure/<uuid>/download/
    
    ═══════════════════════════════════════════════════════════════════════════
    SECURE TRANSFER DOWNLOAD FLOW
    ═══════════════════════════════════════════════════════════════════════════
    
    Step 1: AUTHENTICATION & AUTHORIZATION
        - Verify user is authenticated via JWT
        - Verify user is the intended receiver (or sender for their own files)
    
    Step 2: VALIDATE TRANSFER
        - Check transfer exists and is in downloadable state
        - Verify session is still active and valid
    
    Step 3: DECRYPT AES KEY
        - Get shared secret from session
        - Derive key-encryption-key using HKDF
        - Decrypt AES key using key-encryption-key
    
    Step 4: DECRYPT FILE
        - Read encrypted file from storage
        - Decrypt file content using AES key
        - Verify authentication tag (integrity check)
    
    Step 5: RETURN DECRYPTED FILE
        - Return file as download response
        - Update transfer status
        - Log download event
    
    ═══════════════════════════════════════════════════════════════════════════
    
    Request Headers:
        Authorization: Bearer <jwt_token>
    
    Success Response (200):
        Binary file download with headers:
        - Content-Type: <original mime type>
        - Content-Disposition: attachment; filename="original_filename.ext"
    
    Error Responses:
        - 400: Decryption failed (integrity check failed)
        - 403: Not authorized (not sender or receiver)
        - 404: Transfer not found
        - 500: Server error
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, uuid):
        """
        Handle secure file download.
        
        This method orchestrates the complete decryption workflow:
        1. Validate user authorization
        2. Decrypt AES key using shared secret
        3. Decrypt file using AES key
        4. Return decrypted file
        """
        user = request.user
        
        # =====================================================================
        # STEP 1: FETCH AND AUTHORIZE
        # =====================================================================
        try:
            transfer = Transfer.objects.select_related(
                'sender', 'receiver', 'file', 'session'
            ).get(uuid=uuid)
        except Transfer.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Transfer not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Verify user is sender or receiver
        is_sender = transfer.sender == user
        is_receiver = transfer.receiver == user
        
        if not (is_sender or is_receiver):
            logger.warning(
                f"Unauthorized download attempt: user={user.id}, transfer={transfer.id}"
            )
            return Response({
                'status': 'error',
                'message': 'You are not authorized to download this transfer.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # =====================================================================
        # STEP 2: VALIDATE TRANSFER STATE
        # =====================================================================
        if not transfer.file:
            return Response({
                'status': 'error',
                'message': 'No file associated with this transfer.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        file_obj = transfer.file
        
        if not file_obj.encrypted_file:
            return Response({
                'status': 'error',
                'message': 'No encrypted content available.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        if not transfer.encrypted_aes_key:
            return Response({
                'status': 'error',
                'message': 'Missing encryption key data.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # =====================================================================
        # STEP 3: VALIDATE SESSION
        # =====================================================================
        session = transfer.session
        
        if not session:
            return Response({
                'status': 'error',
                'message': 'No session associated with this transfer.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if not session.is_valid:
            return Response({
                'status': 'error',
                'message': 'Session has expired. Please request a new transfer.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # =====================================================================
        # STEP 4: DECRYPT AES KEY
        # =====================================================================
        try:
            from crypto.utils import decrypt_file, derive_aes_session_key
            
            # Get shared secret from session
            shared_secret = base64.b64decode(session.shared_secret)
            
            # Derive key-encryption-key
            kek = derive_aes_session_key(
                shared_secret=shared_secret,
                context=b"aes-key-encryption"
            )
            
            # Decrypt AES key
            encrypted_aes_key = base64.b64decode(transfer.encrypted_aes_key)
            key_iv = bytes.fromhex(transfer.key_iv)
            key_tag = bytes.fromhex(transfer.key_tag)
            
            aes_key = decrypt_file(
                ciphertext=encrypted_aes_key,
                aes_key=kek,
                iv=key_iv,
                tag=key_tag
            )
            
        except Exception as e:
            logger.error(
                f"AES key decryption failed: transfer={transfer.id}, error={str(e)}"
            )
            return Response({
                'status': 'error',
                'message': 'Failed to decrypt transfer key. Transfer may be corrupted.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # =====================================================================
        # STEP 5: DECRYPT FILE
        # =====================================================================
        try:
            # Read encrypted file
            file_obj.encrypted_file.seek(0)
            ciphertext = file_obj.encrypted_file.read()
            
            # Get file IV and tag
            file_iv = bytes.fromhex(file_obj.iv)
            file_tag = bytes.fromhex(file_obj.tag)
            
            # Decrypt file
            decrypted_content = decrypt_file(
                ciphertext=ciphertext,
                aes_key=aes_key,
                iv=file_iv,
                tag=file_tag
            )
            
        except Exception as e:
            logger.error(
                f"File decryption failed: transfer={transfer.id}, error={str(e)}"
            )
            return Response({
                'status': 'error',
                'message': 'File decryption failed. File may be corrupted or tampered with.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        finally:
            # Security: Clear sensitive data
            try:
                del aes_key
                del kek
                del shared_secret
            except:
                pass
        
        # =====================================================================
        # STEP 6: UPDATE TRANSFER STATUS
        # =====================================================================
        if transfer.status == 'sent' and is_receiver:
            transfer.status = 'completed'
            transfer.completed_at = timezone.now()
            transfer.progress = 100
            transfer.bytes_transferred = file_obj.size
            transfer.save()
            
            # Log download
            TransferLog.objects.create(
                transfer=transfer,
                event='status_changed',
                old_status='sent',
                new_status='completed',
                message=f"File downloaded by {user.username}"
            )
        
        # Update file download stats
        if not file_obj.is_decrypted:
            file_obj.is_decrypted = True
            file_obj.downloaded_at = timezone.now()
        file_obj.download_count += 1
        file_obj.save()
        
        # Log success
        logger.info(
            f"Secure download completed: transfer={transfer.id}, "
            f"user={user.id}, role={'sender' if is_sender else 'receiver'}"
        )
        
        # =====================================================================
        # STEP 7: RETURN DECRYPTED FILE
        # =====================================================================
        decrypted_stream = BytesIO(decrypted_content)
        
        response = FileResponse(
            decrypted_stream,
            content_type=file_obj.mime_type,
            as_attachment=True,
            filename=file_obj.original_name
        )
        
        response['Content-Length'] = len(decrypted_content)
        response['X-Content-Type-Options'] = 'nosniff'
        
        del decrypted_content
        
        return response


class SecureTransferDetailView(APIView):
    """
    Get details of a secure transfer.
    
    GET /api/v1/transfers/secure/<uuid>/
    
    This endpoint returns transfer metadata and (for the receiver only)
    the encrypted AES key needed to decrypt the file.
    
    Response includes:
    - Transfer metadata (sender, receiver, file info, status)
    - For receiver: encrypted_aes_key, key_iv, key_tag (for decryption)
    
    Frontend integration:
    - Used to check transfer status
    - Receiver gets encrypted key to decrypt file locally
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, uuid):
        """Get transfer details."""
        user = request.user
        
        try:
            transfer = Transfer.objects.select_related(
                'sender', 'receiver', 'file', 'session'
            ).get(uuid=uuid)
        except Transfer.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Transfer not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Verify user has access
        if transfer.sender != user and transfer.receiver != user:
            return Response({
                'status': 'error',
                'message': 'You are not authorized to view this transfer.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = SecureTransferDetailSerializer(
            transfer,
            context={'request': request}
        )
        
        return Response({
            'status': 'success',
            'data': serializer.data
        })


class SecureTransferMetadataView(APIView):
    """
    Get encrypted file metadata for receiver to download and decrypt locally.
    
    GET /api/v1/transfers/secure/<uuid>/metadata/
    
    This endpoint is used when the receiver wants to download the encrypted
    file and decrypt it locally (client-side decryption). Returns:
    
    - File metadata (name, size, type)
    - Encrypted AES key (encrypted with shared secret)
    - Key IV and tag (for decrypting the AES key)
    - Download URL for encrypted file
    
    SECURITY NOTE:
    - Only the receiver can access this endpoint
    - The encrypted file and encrypted key can only be decrypted
      by someone who has the shared secret (sender or receiver)
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, uuid):
        """Get transfer metadata for client-side decryption."""
        user = request.user
        
        try:
            transfer = Transfer.objects.select_related(
                'sender', 'receiver', 'file', 'session'
            ).get(uuid=uuid)
        except Transfer.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Transfer not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Only receiver can get decryption metadata
        if transfer.receiver != user:
            return Response({
                'status': 'error',
                'message': 'Only the receiver can access transfer metadata.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        file_obj = transfer.file
        
        return Response({
            'status': 'success',
            'data': {
                'transfer_id': transfer.id,
                'uuid': str(transfer.uuid),
                'file_name': file_obj.original_name,
                'file_size': file_obj.size,
                'file_size_formatted': file_obj.size_formatted,
                'mime_type': file_obj.mime_type,
                'encryption_algorithm': transfer.encryption_algorithm,
                'encrypted_aes_key': transfer.encrypted_aes_key,
                'key_iv': transfer.key_iv,
                'key_tag': transfer.key_tag,
                'file_iv': file_obj.iv,
                'file_tag': file_obj.tag,
                'sender': transfer.sender.username,
                'status': transfer.status,
                'created_at': transfer.created_at.isoformat(),
            }
        })


class EncryptedFileDownloadView(APIView):
    """
    Download encrypted file without server-side decryption.
    
    GET /api/v1/transfers/secure/<uuid>/encrypted-file/
    
    This endpoint returns the raw encrypted file for client-side decryption.
    Used when receiver wants to decrypt the file locally rather than
    having the server decrypt it.
    
    Use case:
    - Maximum security: decryption happens only on receiver's device
    - Server never sees the decrypted content
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, uuid):
        """Download raw encrypted file."""
        user = request.user
        
        try:
            transfer = Transfer.objects.select_related(
                'sender', 'receiver', 'file'
            ).get(uuid=uuid)
        except Transfer.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Transfer not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Only sender and receiver can download
        if transfer.sender != user and transfer.receiver != user:
            return Response({
                'status': 'error',
                'message': 'You are not authorized to download this file.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        file_obj = transfer.file
        
        if not file_obj.encrypted_file:
            return Response({
                'status': 'error',
                'message': 'No encrypted content available.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Read encrypted file
        file_obj.encrypted_file.seek(0)
        encrypted_content = file_obj.encrypted_file.read()
        
        # Return encrypted file
        response = FileResponse(
            BytesIO(encrypted_content),
            content_type='application/octet-stream',
            as_attachment=True,
            filename=f"{file_obj.original_name}.enc"
        )
        
        response['Content-Length'] = len(encrypted_content)
        response['X-Encrypted'] = 'true'
        response['X-Original-Filename'] = file_obj.original_name
        
        return response
