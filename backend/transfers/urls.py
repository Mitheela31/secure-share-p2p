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
]
