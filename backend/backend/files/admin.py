from django.contrib import admin
from .models import File, FileChunk


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    """Admin for File model."""
    
    list_display = [
        'id',
        'original_name',
        'size_formatted',
        'mime_type',
        'owner',
        'is_encrypted',
        'uploaded_at',
    ]
    list_filter = ['is_encrypted', 'mime_type', 'uploaded_at']
    search_fields = ['original_name', 'owner__username', 'checksum']
    ordering = ['-uploaded_at']
    readonly_fields = ['uuid', 'size_formatted', 'uploaded_at', 'updated_at']
    
    fieldsets = (
        ('File Info', {
            'fields': ('uuid', 'name', 'original_name', 'size', 'size_formatted', 'mime_type')
        }),
        ('Security', {
            'fields': ('checksum', 'is_encrypted', 'encryption_algorithm')
        }),
        ('Ownership', {
            'fields': ('owner',)
        }),
        ('Timestamps', {
            'fields': ('uploaded_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(FileChunk)
class FileChunkAdmin(admin.ModelAdmin):
    """Admin for FileChunk model."""
    
    list_display = [
        'id',
        'file',
        'chunk_number',
        'total_chunks',
        'size',
        'status',
        'created_at',
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['file__original_name']
    ordering = ['file', 'chunk_number']
