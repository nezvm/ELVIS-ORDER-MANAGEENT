from django.contrib import admin
from core.base import BaseAdmin
from .models import (
    GoogleWorkspaceConfig, ContactSyncLog, SyncedContact,
    ShopifyStore, ShopifyOrder, ShopifySyncLog,
    IntegrationConfig, WebhookEndpoint, WebhookLog
)


# Google Workspace
@admin.register(GoogleWorkspaceConfig)
class GoogleWorkspaceConfigAdmin(BaseAdmin):
    list_display = ['name', 'sync_enabled', 'last_sync_at', 'is_active']
    readonly_fields = ['last_sync_at', 'last_sync_token']


@admin.register(ContactSyncLog)
class ContactSyncLogAdmin(BaseAdmin):
    list_display = ['config', 'sync_type', 'status', 'contacts_fetched', 'contacts_created', 'created']
    list_filter = ['status', 'sync_type']


@admin.register(SyncedContact)
class SyncedContactAdmin(BaseAdmin):
    list_display = ['google_resource_name', 'customer', 'sync_status', 'last_synced_at']
    list_filter = ['sync_status', 'config']


# Shopify
@admin.register(ShopifyStore)
class ShopifyStoreAdmin(BaseAdmin):
    list_display = ['name', 'shop_domain', 'sync_enabled', 'connection_status', 'last_sync_at']
    list_filter = ['sync_enabled', 'connection_status']


@admin.register(ShopifyOrder)
class ShopifyOrderAdmin(BaseAdmin):
    list_display = ['shopify_order_number', 'store', 'erp_order', 'financial_status', 'fulfillment_status', 'sync_status']
    list_filter = ['sync_status', 'financial_status', 'fulfillment_status', 'store']
    search_fields = ['shopify_order_number', 'shopify_order_id']


@admin.register(ShopifySyncLog)
class ShopifySyncLogAdmin(BaseAdmin):
    list_display = ['store', 'sync_type', 'status', 'items_processed', 'created']
    list_filter = ['status', 'sync_type', 'store']


# Generic Integrations
@admin.register(IntegrationConfig)
class IntegrationConfigAdmin(BaseAdmin):
    list_display = ['name', 'integration_type', 'provider', 'is_enabled', 'last_test_status']
    list_filter = ['integration_type', 'is_enabled']


@admin.register(WebhookEndpoint)
class WebhookEndpointAdmin(BaseAdmin):
    list_display = ['name', 'event_type', 'url', 'is_enabled', 'total_sent', 'last_sent_at']
    list_filter = ['is_enabled', 'event_type']


@admin.register(WebhookLog)
class WebhookLogAdmin(BaseAdmin):
    list_display = ['endpoint', 'event_type', 'status_code', 'success', 'created']
    list_filter = ['success', 'endpoint']
