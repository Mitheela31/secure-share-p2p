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

from .models import Transfer, TransferLog
from .serializers import (
    TransferSerializer,
    TransferCreateSerializer,
    TransferListSerializer,
    TransferUpdateSerializer,
    TransferLogSerializer,
    TransferActionSerializer,
)


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
