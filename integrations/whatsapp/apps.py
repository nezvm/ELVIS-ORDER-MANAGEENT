from django.apps import AppConfig


class WhatsappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'integrations.whatsapp'
    verbose_name = 'WhatsApp Integration'
    
    def ready(self):
        """Import signals when app is ready."""
        try:
            from . import signals  # noqa
        except ImportError:
            pass
