"""
Transfer URL configuration.
"""

from django.urls import path
from .views import (
    TransferListCreateView,
    TransferDetailView,
    TransferByUUIDView,
    TransferActionView,
    SentTransfersView,
    ReceivedTransfersView,
    PendingTransfersView,
    ActiveTransfersView,
    TransferLogsView,
    TransferStatsView,
    # Phase 7: Secure Transfer endpoints
    SecureTransferInitiateView,
    SecureTransferDownloadView,
    SecureTransferDetailView,
    SecureTransferMetadataView,
    EncryptedFileDownloadView,
)

urlpatterns = [
    # Main CRUD
    path('', TransferListCreateView.as_view(), name='transfer-list-create'),
    path('<int:pk>/', TransferDetailView.as_view(), name='transfer-detail'),
    path('uuid/<uuid:uuid>/', TransferByUUIDView.as_view(), name='transfer-by-uuid'),
    
    # Actions
    path('<int:pk>/action/', TransferActionView.as_view(), name='transfer-action'),
    
    # Filtered views
    path('sent/', SentTransfersView.as_view(), name='sent-transfers'),
    path('received/', ReceivedTransfersView.as_view(), name='received-transfers'),
    path('pending/', PendingTransfersView.as_view(), name='pending-transfers'),
    path('active/', ActiveTransfersView.as_view(), name='active-transfers'),
    
    # Logs and stats
    path('<int:transfer_id>/logs/', TransferLogsView.as_view(), name='transfer-logs'),
    path('stats/', TransferStatsView.as_view(), name='transfer-stats'),
    
    # =========================================================================
    # PHASE 7: SECURE FILE TRANSFER ENDPOINTS
    # =========================================================================
    # These endpoints implement the complete encrypted file transfer workflow
    # using ECDH key exchange and AES-256-GCM encryption.
    # =========================================================================
    
    # POST /api/v1/transfers/secure/initiate/
    # Initiate a secure encrypted file transfer
    # - Upload file and encrypt with AES-256-GCM
    # - Encrypt AES key with ECDH shared secret
    # - Create transfer record with encrypted data
    path('secure/initiate/', SecureTransferInitiateView.as_view(), name='secure-transfer-initiate'),
    
    # GET /api/v1/transfers/secure/<uuid>/
    # Get details of a secure transfer
    # - Returns transfer metadata
    # - For receiver: includes encrypted AES key for local decryption
    path('secure/<uuid:uuid>/', SecureTransferDetailView.as_view(), name='secure-transfer-detail'),
    
    # GET /api/v1/transfers/secure/<uuid>/download/
    # Download decrypted file (server-side decryption)
    # - Server decrypts file using shared secret
    # - Returns plaintext file to authorized user
    path('secure/<uuid:uuid>/download/', SecureTransferDownloadView.as_view(), name='secure-transfer-download'),
    
    # GET /api/v1/transfers/secure/<uuid>/metadata/
    # Get encryption metadata for client-side decryption
    # - Returns encrypted AES key and IV/tag for local decryption
    # - Used when receiver wants to decrypt file locally
    path('secure/<uuid:uuid>/metadata/', SecureTransferMetadataView.as_view(), name='secure-transfer-metadata'),
    
    # GET /api/v1/transfers/secure/<uuid>/encrypted-file/
    # Download encrypted file (for client-side decryption)
    # - Returns raw encrypted file
    # - Server never decrypts - maximum security
    path('secure/<uuid:uuid>/encrypted-file/', EncryptedFileDownloadView.as_view(), name='encrypted-file-download'),
]
