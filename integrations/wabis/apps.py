from django.apps import AppConfig


class WabisConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'integrations.wabis'
    verbose_name = 'Wabis WhatsApp BSP'
    
    def ready(self):
        try:
            from . import signals  # noqa
        except ImportError:
            pass
