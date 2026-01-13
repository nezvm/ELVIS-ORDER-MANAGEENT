"""
Feature Flag System for Elvis-Manager ERP

This module provides centralized feature toggle functionality.
Features can be enabled/disabled via settings.py or database.
"""
from django.conf import settings
from functools import wraps
from django.http import Http404


# Default feature flags (can be overridden in settings.py)
DEFAULT_FEATURE_FLAGS = {
    'ENABLE_LOGISTICS_MODULE': True,
    'ENABLE_INVENTORY_MODULE': True,
    'ENABLE_SEGMENTATION_MODULE': True,
    'ENABLE_MARKETING_MODULE': True,
    'ENABLE_INTEGRATIONS_MODULE': True,
    'ENABLE_DYNAMIC_CHANNELS': True,
    'USE_LEGACY_SHIPPING': False,
    'ENABLE_COHORT_ANALYSIS': True,
    'ENABLE_WHATSAPP_INTEGRATION': False,
    'ENABLE_SHOPIFY_INTEGRATION': False,
    'ENABLE_GOOGLE_CONTACTS_SYNC': False,
}


def get_feature_flags():
    """Get merged feature flags from settings and defaults."""
    return {
        **DEFAULT_FEATURE_FLAGS,
        **getattr(settings, 'FEATURE_FLAGS', {})
    }


def is_feature_enabled(feature_name):
    """
    Check if a feature is enabled.
    
    Args:
        feature_name: Name of the feature flag (e.g., 'ENABLE_LOGISTICS_MODULE')
    
    Returns:
        bool: True if feature is enabled, False otherwise
    """
    flags = get_feature_flags()
    return flags.get(feature_name, False)


def feature_required(feature_name):
    """
    Decorator to require a feature to be enabled for a view.
    
    Usage:
        @feature_required('ENABLE_LOGISTICS_MODULE')
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if not is_feature_enabled(feature_name):
                raise Http404(f"Feature '{feature_name}' is not enabled.")
            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator


class FeatureFlagMixin:
    """
    Mixin for class-based views to require a feature flag.
    
    Usage:
        class MyView(FeatureFlagMixin, TemplateView):
            required_feature = 'ENABLE_LOGISTICS_MODULE'
    """
    required_feature = None
    
    def dispatch(self, request, *args, **kwargs):
        if self.required_feature and not is_feature_enabled(self.required_feature):
            raise Http404(f"Feature '{self.required_feature}' is not enabled.")
        return super().dispatch(request, *args, **kwargs)


# Convenience functions for common checks
def is_logistics_enabled():
    return is_feature_enabled('ENABLE_LOGISTICS_MODULE')

def is_inventory_enabled():
    return is_feature_enabled('ENABLE_INVENTORY_MODULE')

def is_segmentation_enabled():
    return is_feature_enabled('ENABLE_SEGMENTATION_MODULE')

def is_marketing_enabled():
    return is_feature_enabled('ENABLE_MARKETING_MODULE')

def is_integrations_enabled():
    return is_feature_enabled('ENABLE_INTEGRATIONS_MODULE')

def use_legacy_shipping():
    return is_feature_enabled('USE_LEGACY_SHIPPING')

def is_dynamic_channels_enabled():
    return is_feature_enabled('ENABLE_DYNAMIC_CHANNELS')
