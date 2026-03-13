"""Audit app configuration."""

from django.apps import AppConfig


class AuditConfig(AppConfig):
    """Configuration for the Audit (Activity Logging) app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'audit'
    verbose_name = 'Activity Logging & Audit'
    
    def ready(self):
        """
        Import signals when app is ready.
        This ensures signal handlers are connected on app startup.
        """
        # Import signals to connect signal handlers
        import audit.signals  # noqa: F401
