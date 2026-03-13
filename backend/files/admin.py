from django.contrib import admin
from .models import File, FileChunk


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    """
    Admin for File model.
    
    SECURITY: IV and tag are shown (they're not secret), but the
    encrypted_file content is NOT decryptable without the session key.
    """
    
    list_display = [
        'id',
        'original_name',
        'size_formatted',
        'mime_type',
        'owner',
        'is_encrypted',
        'is_decrypted',
        'session',
        'uploaded_at',
    ]
    list_filter = ['is_encrypted', 'is_decrypted', 'encryption_algorithm', 'mime_type', 'uploaded_at']
    search_fields = ['original_name', 'owner__username', 'checksum']
    ordering = ['-uploaded_at']
    readonly_fields = ['uuid', 'size_formatted', 'uploaded_at', 'updated_at', 'iv', 'tag']
    
    fieldsets = (
        ('File Info', {
            'fields': ('uuid', 'name', 'original_name', 'size', 'size_formatted', 'mime_type')
        }),
        ('Encryption', {
            'fields': ('is_encrypted', 'encryption_algorithm', 'encrypted_file', 'iv', 'tag', 'is_decrypted', 'session'),
            'description': 'AES-256-GCM encryption parameters. IV and tag are public, but decryption requires the session key.'
        }),
        ('Integrity', {
            'fields': ('checksum',),
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
