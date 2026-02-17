from django.apps import AppConfig


class MarketingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'marketing'
    verbose_name = 'Marketing'
    
    def ready(self):
        """Import signals when app is ready."""
        try:
            from . import signals  # noqa
        except ImportError:
            pass
