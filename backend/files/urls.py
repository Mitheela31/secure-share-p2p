"""
File management URL configuration.
"""

from django.urls import path
from .views import (
    FileListCreateView,
    FileDetailView,
    FileByUUIDView,
    FileUploadView,
    FileChunkListView,
    FileChunkUpdateView,
    FileProgressView,
)

urlpatterns = [
    # File CRUD
    path('', FileListCreateView.as_view(), name='file-list-create'),
    path('<int:pk>/', FileDetailView.as_view(), name='file-detail'),
    path('uuid/<uuid:uuid>/', FileByUUIDView.as_view(), name='file-by-uuid'),
    
    # Direct upload (non-P2P)
    path('upload/', FileUploadView.as_view(), name='file-upload'),
    
    # Chunk management
    path('<int:file_id>/chunks/', FileChunkListView.as_view(), name='file-chunks'),
    path('<int:file_id>/chunks/<int:chunk_id>/', FileChunkUpdateView.as_view(), name='chunk-update'),
    path('<int:file_id>/progress/', FileProgressView.as_view(), name='file-progress'),
]
