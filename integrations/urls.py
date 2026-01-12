from django.urls import path
from . import views

app_name = 'integrations'

urlpatterns = [
    # Dashboard
    path('', views.IntegrationDashboardView.as_view(), name='dashboard'),
    
    # Google Workspace
    path('google/', views.GoogleConfigListView.as_view(), name='google_config_list'),
    path('google/<uuid:pk>/', views.GoogleConfigDetailView.as_view(), name='google_config_detail'),
    path('google/new/', views.GoogleConfigCreateView.as_view(), name='google_config_create'),
    path('google/<uuid:pk>/update/', views.GoogleConfigUpdateView.as_view(), name='google_config_update'),
    
    # Shopify
    path('shopify/', views.ShopifyStoreListView.as_view(), name='shopify_store_list'),
    path('shopify/<uuid:pk>/', views.ShopifyStoreDetailView.as_view(), name='shopify_store_detail'),
    path('shopify/new/', views.ShopifyStoreCreateView.as_view(), name='shopify_store_create'),
    path('shopify/<uuid:pk>/update/', views.ShopifyStoreUpdateView.as_view(), name='shopify_store_update'),
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
    
    # API Endpoints
    path('api/google/<uuid:pk>/sync/', views.sync_google_contacts, name='sync_google_contacts'),
    path('api/shopify/<uuid:pk>/sync/', views.sync_shopify_orders, name='sync_shopify_orders'),
    path('api/shopify/<uuid:pk>/test/', views.test_shopify_connection, name='test_shopify_connection'),
    path('api/shopify/order/<uuid:order_pk>/fulfill/', views.send_fulfillment, name='send_fulfillment'),
    path('api/integration/<uuid:pk>/test/', views.test_integration, name='test_integration'),
]
