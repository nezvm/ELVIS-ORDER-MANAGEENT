from django.apps import AppConfig


class ShopifyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'integrations.shopify'
    label = 'shopify'
    verbose_name = 'Shopify Integration'
