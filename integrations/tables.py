from django_tables2 import columns
from core.base import BaseTable
from .models import GoogleWorkspaceConfig, ShopifyStore, ShopifyOrder, IntegrationConfig, WebhookEndpoint


class GoogleConfigTable(BaseTable):
    name = columns.Column(linkify=True)
    sync_enabled = columns.BooleanColumn()
    last_sync_at = columns.DateTimeColumn(format='d/m/Y H:i')
    
    class Meta:
        model = GoogleWorkspaceConfig
        fields = ['name', 'sync_enabled', 'last_sync_at', 'created']
        attrs = {'class': 'table table-striped table-bordered'}


class ShopifyStoreTable(BaseTable):
    name = columns.Column(linkify=True)
    shop_domain = columns.Column()
    sync_enabled = columns.BooleanColumn()
    connection_status = columns.Column()
    last_sync_at = columns.DateTimeColumn(format='d/m/Y H:i')
    
    class Meta:
        model = ShopifyStore
        fields = ['name', 'shop_domain', 'sync_enabled', 'connection_status', 'last_sync_at', 'created']
        attrs = {'class': 'table table-striped table-bordered'}


class ShopifyOrderTable(BaseTable):
    shopify_order_number = columns.Column(verbose_name="Order #")
    store = columns.Column()
    financial_status = columns.Column()
    fulfillment_status = columns.Column()
    sync_status = columns.Column()
    erp_order = columns.Column(verbose_name="ERP Order")
    
    class Meta:
        model = ShopifyOrder
        fields = ['shopify_order_number', 'store', 'financial_status', 'fulfillment_status', 'sync_status', 'erp_order', 'created']
        attrs = {'class': 'table table-striped table-bordered'}


class IntegrationConfigTable(BaseTable):
    name = columns.Column(linkify=True)
    integration_type = columns.Column()
    provider = columns.Column()
    is_enabled = columns.BooleanColumn(verbose_name="Enabled")
    last_test_status = columns.Column(verbose_name="Status")
    
    class Meta:
        model = IntegrationConfig
        fields = ['name', 'integration_type', 'provider', 'is_enabled', 'last_test_status', 'created']
        attrs = {'class': 'table table-striped table-bordered'}


class WebhookEndpointTable(BaseTable):
    name = columns.Column(linkify=True)
    event_type = columns.Column()
    url = columns.Column()
    is_enabled = columns.BooleanColumn(verbose_name="Enabled")
    total_sent = columns.Column(verbose_name="Sent")
    last_sent_at = columns.DateTimeColumn(format='d/m/Y H:i')
    
    class Meta:
        model = WebhookEndpoint
        fields = ['name', 'event_type', 'url', 'is_enabled', 'total_sent', 'last_sent_at']
        attrs = {'class': 'table table-striped table-bordered'}
