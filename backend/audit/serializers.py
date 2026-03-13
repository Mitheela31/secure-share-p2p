"""
=============================================================================
PHASE 8: Audit Serializers for ActivityLog API
=============================================================================

Serializers for converting ActivityLog model instances to JSON format.
Provides both detailed and list views of activity logs.

=============================================================================
"""

from rest_framework import serializers
from .models import ActivityLog


class ActivityLogUserSerializer(serializers.Serializer):
    """
    Minimal user serializer for embedding in activity logs.
    
    Only includes non-sensitive user information.
    """
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)


class ActivityLogListSerializer(serializers.ModelSerializer):
    """
    List serializer for ActivityLog - optimized for list views.
    
    Provides a compact representation with essential fields only.
    Used in paginated list endpoints.
    
    Response Example:
    {
        "id": 1,
        "action": "file_upload",
        "action_display": "File Upload",
        "description": "Uploaded file: document.pdf",
        "status": "success",
        "timestamp": "2026-03-12T10:30:00Z"
    }
    """
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    
    class Meta:
        model = ActivityLog
        fields = [
            'id',
            'action',
            'action_display',
            'description',
            'status',
            'timestamp',
        ]
        read_only_fields = fields


class ActivityLogSerializer(serializers.ModelSerializer):
    """
    Full serializer for ActivityLog - includes all details.
    
    Used for detailed view of individual log entries.
    Includes user information, IP address, and metadata.
    
    Response Example:
    {
        "id": 1,
        "uuid": "550e8400-e29b-41d4-a716-446655440000",
        "user": {
            "id": 1,
            "username": "john_doe"
        },
        "action": "file_upload",
        "action_display": "File Upload",
        "description": "Uploaded file: document.pdf (1.5 MB)",
        "status": "success",
        "status_display": "Success",
        "ip_address": "192.168.1.100",
        "user_agent": "Mozilla/5.0...",
        "metadata": {
            "file_id": 1,
            "file_name": "document.pdf",
            "file_size": 1572864
        },
        "timestamp": "2026-03-12T10:30:00Z"
    }
    """
    user = ActivityLogUserSerializer(read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ActivityLog
        fields = [
            'id',
            'uuid',
            'user',
            'action',
            'action_display',
            'description',
            'status',
            'status_display',
            'ip_address',
            'user_agent',
            'metadata',
            'related_file',
            'related_transfer',
            'timestamp',
        ]
        read_only_fields = fields


class ActivityLogCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating ActivityLog entries programmatically.
    
    Note: Activity logs should generally be created through the
    ActivityLog.log() class method, not directly via API.
    This serializer is provided for internal use.
    """
    
    class Meta:
        model = ActivityLog
        fields = [
            'user',
            'action',
            'description',
            'status',
            'ip_address',
            'user_agent',
            'metadata',
            'related_file',
            'related_transfer',
        ]
    
    def validate_action(self, value):
        """Ensure action is a valid choice."""
        valid_actions = [choice[0] for choice in ActivityLog.ACTION_CHOICES]
        if value not in valid_actions:
            raise serializers.ValidationError(
                f"Invalid action. Must be one of: {', '.join(valid_actions)}"
            )
        return value
