"""
File management URL configuration.
"""

from django.urls import path
from .views import (
    FileListCreateView,
    FileDetailView,
    FileByUUIDView,
    FileDownloadView,
    FileUploadView,
    FileChunkListView,
    FileChunkUpdateView,
    FileProgressView,
    SecureFileUploadView,
    SecureFileDownloadView,
)

urlpatterns = [
    # File CRUD
    path('', FileListCreateView.as_view(), name='file-list-create'),
    path('<int:pk>/', FileDetailView.as_view(), name='file-detail'),
    path('<int:file_id>/download/', FileDownloadView.as_view(), name='file-download'),
    path('uuid/<uuid:uuid>/', FileByUUIDView.as_view(), name='file-by-uuid'),
    
    # Direct upload (non-P2P, non-encrypted)
    path('upload/', FileUploadView.as_view(), name='file-upload'),
    
    # =========================================================================
    # SECURE ENCRYPTED UPLOAD (AES-256-GCM)
    # =========================================================================
    # POST /api/v1/files/secure-upload/
    # Encrypts file using AES-256-GCM with session key derived from ECDH
    # =========================================================================
    path('secure-upload/', SecureFileUploadView.as_view(), name='secure-file-upload'),
    
    # =========================================================================
    # SECURE ENCRYPTED DOWNLOAD (AES-256-GCM DECRYPTION)
    # =========================================================================
    # GET /api/v1/files/<uuid>/secure-download/
    # Decrypts file using AES-256-GCM with session key derived from ECDH
    # Only file owner or intended receiver can access
    # =========================================================================
    path('<uuid:uuid>/secure-download/', SecureFileDownloadView.as_view(), name='secure-file-download'),
    
    # Chunk management
    path('<int:file_id>/chunks/', FileChunkListView.as_view(), name='file-chunks'),
    path('<int:file_id>/chunks/<int:chunk_id>/', FileChunkUpdateView.as_view(), name='chunk-update'),
    path('<int:file_id>/progress/', FileProgressView.as_view(), name='file-progress'),
]
