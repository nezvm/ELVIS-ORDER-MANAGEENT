import uuid
from django.db import models
from django.urls import reverse_lazy
from core.base import BaseModel


# Google Workspace Integration
class GoogleWorkspaceConfig(BaseModel):
    """Google Workspace configuration for contact sync."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, default="Default Google Workspace")
    client_id = models.CharField(max_length=500, blank=True, null=True)
    client_secret = models.CharField(max_length=500, blank=True, null=True)
    refresh_token = models.TextField(blank=True, null=True)
    access_token = models.TextField(blank=True, null=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    
    # Service account JSON (alternative to OAuth)
    service_account_json = models.TextField(blank=True, null=True, help_text="Service account JSON credentials")
    
    # Sync settings
    sync_enabled = models.BooleanField(default=False)
    sync_interval_minutes = models.IntegerField(default=30)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_sync_token = models.CharField(max_length=500, blank=True, null=True, help_text="Incremental sync token")
    
    # Scope
    scopes = models.JSONField(default=list, help_text="OAuth scopes")
    
    class Meta:
        verbose_name = "Google Workspace Config"
        verbose_name_plural = "Google Workspace Configs"
    
    def __str__(self):
        return self.name
    
    @staticmethod
    def get_list_url():
        return reverse_lazy("integrations:google_config_list")
    
    def get_absolute_url(self):
        return reverse_lazy("integrations:google_config_detail", kwargs={"pk": str(self.pk)})


class ContactSyncLog(BaseModel):
    """Log of contact sync operations."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    config = models.ForeignKey(GoogleWorkspaceConfig, on_delete=models.CASCADE, related_name='sync_logs')
    sync_type = models.CharField(max_length=30, choices=[
        ('full', 'Full Sync'),
        ('incremental', 'Incremental Sync'),
        ('manual', 'Manual Sync'),
    ])
    status = models.CharField(max_length=30, choices=[
        ('started', 'Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ], default='started')
    
    contacts_fetched = models.IntegerField(default=0)
    contacts_created = models.IntegerField(default=0)
    contacts_updated = models.IntegerField(default=0)
    contacts_skipped = models.IntegerField(default=0)
    
    error_message = models.TextField(blank=True, null=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Contact Sync Log"
        verbose_name_plural = "Contact Sync Logs"
        ordering = ['-created']
    
    def __str__(self):
        return f"Sync: {self.created.strftime('%Y-%m-%d %H:%M')} - {self.status}"


class SyncedContact(BaseModel):
    """Track synced contacts with Google resource ID mapping."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    config = models.ForeignKey(GoogleWorkspaceConfig, on_delete=models.CASCADE, related_name='synced_contacts')
    google_resource_name = models.CharField(max_length=200, help_text="Google People API resource name")
    customer = models.ForeignKey('master.Customer', on_delete=models.SET_NULL, null=True, blank=True, related_name='synced_contacts')
    
    # Contact data from Google
    google_data = models.JSONField(default=dict)
    
    # Sync metadata
    first_synced_at = models.DateTimeField(auto_now_add=True)
    last_synced_at = models.DateTimeField(auto_now=True)
    sync_status = models.CharField(max_length=30, choices=[
        ('synced', 'Synced'),
        ('pending_review', 'Pending Review'),
        ('conflict', 'Conflict'),
        ('error', 'Error'),
    ], default='synced')
    
    class Meta:
        verbose_name = "Synced Contact"
        verbose_name_plural = "Synced Contacts"
        unique_together = ['config', 'google_resource_name']
    
    def __str__(self):
        name = self.google_data.get('name', 'Unknown')
        return f"Contact: {name}"


# Shopify Integration
class ShopifyStore(BaseModel):
    """Shopify store configuration."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    shop_domain = models.CharField(max_length=200, unique=True, help_text="e.g., mystore.myshopify.com")
    api_key = models.CharField(max_length=200, blank=True, null=True)
    api_secret = models.CharField(max_length=200, blank=True, null=True)
    access_token = models.TextField(blank=True, null=True)
    
    # Channel mapping
    web_paid_channel = models.ForeignKey('channels_config.DynamicChannel', on_delete=models.SET_NULL, 
                                         null=True, blank=True, related_name='shopify_paid_stores',
                                         help_text="Channel for prepaid Shopify orders")
    web_cod_channel = models.ForeignKey('channels_config.DynamicChannel', on_delete=models.SET_NULL,
                                        null=True, blank=True, related_name='shopify_cod_stores',
                                        help_text="Channel for COD Shopify orders")
    
    # Sync settings
    sync_enabled = models.BooleanField(default=False)
    sync_orders = models.BooleanField(default=True)
    sync_products = models.BooleanField(default=False)
    sync_inventory = models.BooleanField(default=False)
    auto_fulfill = models.BooleanField(default=False, help_text="Auto-mark orders as fulfilled when shipped")
    
    # Abandoned Checkout Sync Settings
    sync_abandoned_checkouts = models.BooleanField(default=False, help_text="Sync abandoned checkouts to Leads")
    sync_abandoned_carts = models.BooleanField(default=False, help_text="Sync abandoned carts to Leads (if supported)")
    abandoned_sync_interval_minutes = models.IntegerField(default=30, help_text="How often to fetch abandoned checkouts")
    last_abandoned_sync_at = models.DateTimeField(null=True, blank=True)
    
    # Webhook settings
    webhook_secret = models.CharField(max_length=200, blank=True, null=True)
    orders_webhook_id = models.CharField(max_length=100, blank=True, null=True)
    checkouts_webhook_id = models.CharField(max_length=100, blank=True, null=True, help_text="Webhook for abandoned checkouts")
    
    # Status
    last_sync_at = models.DateTimeField(null=True, blank=True)
    connection_status = models.CharField(max_length=30, choices=[
        ('connected', 'Connected'),
        ('disconnected', 'Disconnected'),
        ('error', 'Error'),
    ], default='disconnected')
    
    class Meta:
        verbose_name = "Shopify Store"
        verbose_name_plural = "Shopify Stores"
    
    def __str__(self):
        return self.name
    
    @staticmethod
    def get_list_url():
        return reverse_lazy("integrations:shopify_store_list")
    
    def get_absolute_url(self):
        return reverse_lazy("integrations:shopify_store_detail", kwargs={"pk": str(self.pk)})
    
    def get_update_url(self):
        return reverse_lazy("integrations:shopify_store_update", kwargs={"pk": str(self.pk)})


class ShopifyOrder(BaseModel):
    """Track Shopify orders synced to ERP."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(ShopifyStore, on_delete=models.CASCADE, related_name='shopify_orders')
    shopify_order_id = models.CharField(max_length=100)
    shopify_order_number = models.CharField(max_length=100)
    
    # ERP order link
    erp_order = models.OneToOneField('master.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='shopify_order')
    
    # Order data from Shopify
    shopify_data = models.JSONField(default=dict)
    
    # Status
    financial_status = models.CharField(max_length=50, blank=True, null=True)  # paid, pending, refunded
    fulfillment_status = models.CharField(max_length=50, blank=True, null=True)  # fulfilled, unfulfilled
    sync_status = models.CharField(max_length=30, choices=[
        ('pending', 'Pending'),
        ('synced', 'Synced'),
        ('fulfilled', 'Fulfilled'),
        ('cancelled', 'Cancelled'),
        ('error', 'Error'),
    ], default='pending')
    
    # Fulfillment
    fulfillment_sent = models.BooleanField(default=False)
    fulfillment_id = models.CharField(max_length=100, blank=True, null=True)
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    tracking_url = models.URLField(blank=True, null=True)
    
    error_message = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Shopify Order"
        verbose_name_plural = "Shopify Orders"
        unique_together = ['store', 'shopify_order_id']
        ordering = ['-created']
    
    def __str__(self):
        return f"Shopify #{self.shopify_order_number}"


class ShopifySyncLog(BaseModel):
    """Log of Shopify sync operations."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(ShopifyStore, on_delete=models.CASCADE, related_name='sync_logs')
    sync_type = models.CharField(max_length=30, choices=[
        ('orders', 'Orders'),
        ('products', 'Products'),
        ('inventory', 'Inventory'),
        ('fulfillment', 'Fulfillment'),
    ])
    status = models.CharField(max_length=30, choices=[
        ('started', 'Started'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ], default='started')
    
    items_processed = models.IntegerField(default=0)
    items_created = models.IntegerField(default=0)
    items_updated = models.IntegerField(default=0)
    items_failed = models.IntegerField(default=0)
    
    error_message = models.TextField(blank=True, null=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Shopify Sync Log"
        verbose_name_plural = "Shopify Sync Logs"
        ordering = ['-created']
    
    def __str__(self):
        return f"{self.store.name} - {self.sync_type} - {self.status}"


# Generic Integration Config
class IntegrationConfig(BaseModel):
    """Generic configuration for plug-and-play integrations."""
    INTEGRATION_TYPES = [
        ('carrier', 'Carrier'),
        ('payment', 'Payment Gateway'),
        ('marketing', 'Marketing Tool'),
        ('notification', 'Notification Service'),
        ('analytics', 'Analytics'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    integration_type = models.CharField(max_length=50, choices=INTEGRATION_TYPES)
    provider = models.CharField(max_length=100, help_text="Provider name (e.g., Twilio, SendGrid)")
    
    # Credentials (encrypted in production)
    api_key = models.CharField(max_length=500, blank=True, null=True)
    api_secret = models.CharField(max_length=500, blank=True, null=True)
    access_token = models.TextField(blank=True, null=True)
    
    # Configuration
    base_url = models.URLField(blank=True, null=True)
    config = models.JSONField(default=dict, help_text="Additional configuration")
    
    # Status
    is_enabled = models.BooleanField(default=False)
    last_test_at = models.DateTimeField(null=True, blank=True)
    last_test_status = models.CharField(max_length=30, blank=True, null=True)
    
    class Meta:
        verbose_name = "Integration Config"
        verbose_name_plural = "Integration Configs"
    
    def __str__(self):
        return f"{self.name} ({self.provider})"
    
    @staticmethod
    def get_list_url():
        return reverse_lazy("integrations:config_list")
    
    def get_absolute_url(self):
        return reverse_lazy("integrations:config_detail", kwargs={"pk": str(self.pk)})


# Webhook configuration
class WebhookEndpoint(BaseModel):
    """Webhook endpoints for external systems."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    event_type = models.CharField(max_length=100, help_text="Event that triggers this webhook")
    url = models.URLField(help_text="Target URL to receive webhook")
    secret = models.CharField(max_length=200, blank=True, null=True, help_text="Secret for signature verification")
    
    # Configuration
    headers = models.JSONField(default=dict, help_text="Custom headers to send")
    is_enabled = models.BooleanField(default=True)
    
    # Stats
    total_sent = models.IntegerField(default=0)
    total_failed = models.IntegerField(default=0)
    last_sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Webhook Endpoint"
        verbose_name_plural = "Webhook Endpoints"
    
    def __str__(self):
        return f"{self.name} - {self.event_type}"


class WebhookLog(BaseModel):
    """Log of webhook deliveries."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    endpoint = models.ForeignKey(WebhookEndpoint, on_delete=models.CASCADE, related_name='logs')
    event_type = models.CharField(max_length=100)
    payload = models.JSONField(default=dict)
    
    # Response
    status_code = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True, null=True)
    success = models.BooleanField(default=False)
    error_message = models.TextField(blank=True, null=True)
    
    # Timing
    response_time_ms = models.IntegerField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Webhook Log"
        verbose_name_plural = "Webhook Logs"
        ordering = ['-created']
    
    def __str__(self):
        status = "Success" if self.success else "Failed"
        return f"{self.endpoint.name} - {status}"
