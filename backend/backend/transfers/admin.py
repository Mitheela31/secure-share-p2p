from django.contrib import admin
from .models import Transfer, TransferLog


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    """Admin for Transfer model."""
    
    list_display = [
        'id',
        'sender',
        'receiver',
        'file',
        'status',
        'progress',
        'created_at',
        'completed_at',
    ]
    list_filter = ['status', 'created_at']
    search_fields = [
        'sender__username', 
        'receiver__username', 
        'file__original_name',
        'uuid'
    ]
    ordering = ['-created_at']
    readonly_fields = ['uuid', 'created_at', 'started_at', 'completed_at', 'updated_at']
    
    fieldsets = (
        ('Transfer Info', {
            'fields': ('uuid', 'sender', 'receiver', 'file')
        }),
        ('Status', {
            'fields': ('status', 'progress', 'bytes_transferred', 'transfer_speed')
        }),
        ('Connection', {
            'fields': ('connection_id', 'error_message', 'retry_count')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'started_at', 'completed_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TransferLog)
class TransferLogAdmin(admin.ModelAdmin):
    """Admin for TransferLog model."""
    
    list_display = [
        'id',
        'transfer',
        'event',
        'old_status',
        'new_status',
        'timestamp',
    ]
    list_filter = ['event', 'timestamp']
    search_fields = ['transfer__uuid', 'message']
    ordering = ['-timestamp']
    readonly_fields = ['timestamp']
