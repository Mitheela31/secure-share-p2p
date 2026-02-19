"""
File views for file metadata management.
"""

from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
import hashlib

from .models import File, FileChunk
from .serializers import (
    FileSerializer,
    FileCreateSerializer,
    FileListSerializer,
    FileChunkSerializer,
    FileChunkCreateSerializer,
    FileUploadSerializer,
)


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
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = FileSerializer
    lookup_field = 'uuid'
    queryset = File.objects.all()


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
        serializer = FileUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        uploaded_file = serializer.validated_data['file']
        is_encrypted = serializer.validated_data['is_encrypted']
        
        # Calculate checksum
        hasher = hashlib.sha256()
        for chunk in uploaded_file.chunks():
            hasher.update(chunk)
        checksum = hasher.hexdigest()
        
        # Create file record
        file_obj = File.objects.create(
            name=uploaded_file.name,
            original_name=uploaded_file.name,
            size=uploaded_file.size,
            mime_type=uploaded_file.content_type or 'application/octet-stream',
            checksum=checksum,
            is_encrypted=is_encrypted,
            owner=request.user,
            file_path=uploaded_file,
        )
        
        response_serializer = FileSerializer(file_obj)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


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
