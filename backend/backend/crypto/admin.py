from django.contrib import admin
from .models import SessionKey


@admin.register(SessionKey)
class SessionKeyAdmin(admin.ModelAdmin):
    list_display = ['id', 'sender', 'receiver', 'created_at']
    list_filter = ['created_at']
    search_fields = ['sender__username', 'receiver__username']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
