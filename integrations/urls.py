from django.urls import path, include
from . import views
from .shopify import portal_views

app_name = 'integrations'

urlpatterns = [
    # Dashboard
    path('', views.IntegrationDashboardView.as_view(), name='dashboard'),
    
    # WhatsApp Integration (includes webhook)
    path('whatsapp/', include('integrations.whatsapp.urls')),
    
    # Wabis WhatsApp BSP Integration
    path('wabis/', include('integrations.wabis.urls')),
    
    # Google Workspace
    path('google/', views.GoogleConfigListView.as_view(), name='google_config_list'),
    path('google/<uuid:pk>/', views.GoogleConfigDetailView.as_view(), name='google_config_detail'),
    path('google/new/', views.GoogleConfigCreateView.as_view(), name='google_config_create'),
    path('google/<uuid:pk>/update/', views.GoogleConfigUpdateView.as_view(), name='google_config_update'),
    
    # Shopify Portal (main comprehensive portal)
    path('shopify/', portal_views.ShopifyPortalSelectView.as_view(), name='shopify_portal_select'),
    path('shopify/portal/', portal_views.ShopifyPortalSelectView.as_view(), name='shopify_portal_select_root'),
    path('shopify/portal/<uuid:pk>/', portal_views.ShopifyPortalView.as_view(), name='shopify_portal'),
    
    # Shopify Portal API Endpoints
    path('shopify/api/<uuid:pk>/connect/', portal_views.api_connect_store, name='shopify_api_connect'),
    path('shopify/api/<uuid:pk>/disconnect/', portal_views.api_disconnect_store, name='shopify_api_disconnect'),
    path('shopify/api/<uuid:pk>/verify-permissions/', portal_views.api_verify_permissions, name='shopify_api_verify'),
    path('shopify/api/<uuid:pk>/register-webhooks/', portal_views.api_register_webhooks, name='shopify_api_webhooks'),
    path('shopify/api/<uuid:pk>/save-sync-rules/', portal_views.api_save_sync_rules, name='shopify_api_sync_rules'),
    path('shopify/api/<uuid:pk>/get-shop-info/', portal_views.api_get_shop_info, name='shopify_api_shop_info'),
    path('shopify/api/<uuid:pk>/test-order/', portal_views.api_test_read_order, name='shopify_api_test_order'),
    path('shopify/api/<uuid:pk>/test-customer/', portal_views.api_test_read_customer, name='shopify_api_test_customer'),
    path('shopify/api/<uuid:pk>/simulate-webhook/', portal_views.api_simulate_webhook, name='shopify_api_simulate_webhook'),
    path('shopify/api/<uuid:pk>/test-fulfillment/', portal_views.api_test_fulfillment_push, name='shopify_api_test_fulfillment'),
    path('shopify/api/<uuid:pk>/run-abandoned-sync/', portal_views.api_run_abandoned_sync, name='shopify_api_abandoned_sync'),
    path('shopify/api/<uuid:pk>/logs/', portal_views.api_get_logs, name='shopify_api_logs'),
    path('shopify/api/<uuid:pk>/replay-event/', portal_views.api_replay_event, name='shopify_api_replay'),
    path('shopify/api/<uuid:pk>/toggle-connector/', portal_views.api_toggle_connector, name='shopify_api_toggle_connector'),
    
    # Shopify CRUD (legacy/basic)
    path('shopify/stores/', views.ShopifyStoreListView.as_view(), name='shopify_store_list'),
    path('shopify/stores/<uuid:pk>/', views.ShopifyStoreDetailView.as_view(), name='shopify_store_detail'),
    path('shopify/stores/new/', views.ShopifyStoreCreateView.as_view(), name='shopify_store_create'),
    path('shopify/stores/<uuid:pk>/update/', views.ShopifyStoreUpdateView.as_view(), name='shopify_store_update'),
    path('shopify/orders/', views.ShopifyOrderListView.as_view(), name='shopify_order_list'),
    
    # Generic Integrations
    path('configs/', views.IntegrationConfigListView.as_view(), name='config_list'),
    path('config/<uuid:pk>/', views.IntegrationConfigDetailView.as_view(), name='config_detail'),
    path('config/new/', views.IntegrationConfigCreateView.as_view(), name='config_create'),
    path('config/<uuid:pk>/update/', views.IntegrationConfigUpdateView.as_view(), name='config_update'),
    
    # Webhooks
    path('webhooks/', views.WebhookEndpointListView.as_view(), name='webhook_list'),
    path('webhook/new/', views.WebhookEndpointCreateView.as_view(), name='webhook_create'),
    path('webhook/<uuid:pk>/update/', views.WebhookEndpointUpdateView.as_view(), name='webhook_update'),
    
    # API Endpoints (legacy)
    path('api/google/<uuid:pk>/sync/', views.sync_google_contacts, name='sync_google_contacts'),
    path('api/shopify/<uuid:pk>/sync/', views.sync_shopify_orders, name='sync_shopify_orders'),
    path('api/shopify/<uuid:pk>/test/', views.test_shopify_connection, name='test_shopify_connection'),
    path('api/shopify/order/<uuid:order_pk>/fulfill/', views.send_fulfillment, name='send_fulfillment'),
    path('api/integration/<uuid:pk>/test/', views.test_integration, name='test_integration'),
]
