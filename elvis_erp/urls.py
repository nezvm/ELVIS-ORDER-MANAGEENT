from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from registration.backends.default import urls as registration_urls

# Import WhatsApp webhook for root-level access
from integrations.whatsapp.views import whatsapp_webhook
from integrations.wabis.views import wabis_webhook
from integrations.shopify.views import (
    shopify_webhook, 
    shopify_orders_webhook,
    shopify_checkouts_webhook,
    shopify_fulfillments_webhook
)

# Core URL patterns
core_patterns = [
    path("", include("core.urls")),
    path("master/", include("master.urls")),
    path("accounts/", include("accounts.urls")),
    path("admin/", admin.site.urls),
    path("accounts/", include(registration_urls)),
    path("tinymce/", include("tinymce.urls")),
    
    # New module URLs
    path("channels/", include("channels_config.urls")),
    path("logistics/", include("logistics.urls")),
    path("inventory/", include("inventory.urls")),
    path("segmentation/", include("segmentation.urls")),
    path("integrations/", include("integrations.urls")),
    path("marketing/", include("marketing.urls")),
    
    # WhatsApp Webhook at root level for easy Meta configuration
    path("webhooks/whatsapp/", whatsapp_webhook, name='whatsapp_webhook_root'),
    
    # Wabis Webhook at root level for easy BSP configuration
    path("webhooks/wabis/", wabis_webhook, name='wabis_webhook_root'),
    
    # Shopify Webhooks at root level
    path("webhooks/shopify/", shopify_webhook, name='shopify_webhook_root'),
    path("webhooks/shopify/orders/", shopify_orders_webhook, name='shopify_orders_webhook_root'),
    path("webhooks/shopify/checkouts/", shopify_checkouts_webhook, name='shopify_checkouts_webhook_root'),
    path("webhooks/shopify/fulfillments/", shopify_fulfillments_webhook, name='shopify_fulfillments_webhook_root'),
    
    # REST API
    path("api/v1/", include("api.urls")),
]

# Main URL patterns - serve routes both with and without /api prefix
# Emergent platform routes /api/* to backend on port 8001
urlpatterns = [
    # Routes without /api prefix (for local development)
    *core_patterns,
    
    # Routes with /api prefix (for Emergent platform external access)
    path("api/", include((core_patterns, 'api_prefixed'))),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_FILE_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
