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
    """Shopify store configuration - single store controls all connectors."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store_name = models.CharField(max_length=200)
    name = models.CharField(max_length=200)  # kept for backward compat
    shop_domain = models.CharField(max_length=200, unique=True, help_text="e.g., mystore.myshopify.com")
    api_key = models.CharField(max_length=200, blank=True, null=True)
    api_secret = models.CharField(max_length=200, blank=True, null=True)
    access_token = models.TextField(blank=True, null=True)
    api_version = models.CharField(max_length=20, default='2024-01', help_text="Shopify API version")
    
    # Status
    status = models.CharField(max_length=30, choices=[
        ('CONNECTED', 'Connected'),
        ('DISCONNECTED', 'Disconnected'),
        ('ERROR', 'Error'),
    ], default='DISCONNECTED')
    connection_status = models.CharField(max_length=30, choices=[
        ('connected', 'Connected'),
        ('disconnected', 'Disconnected'),
        ('error', 'Error'),
    ], default='disconnected')
    installed_at = models.DateTimeField(null=True, blank=True)
    
    # Sync timestamps
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_orders_sync_at = models.DateTimeField(null=True, blank=True)
    last_customers_sync_at = models.DateTimeField(null=True, blank=True)
    last_abandoned_sync_at = models.DateTimeField(null=True, blank=True)
    webhook_last_received_at = models.DateTimeField(null=True, blank=True)
    
    # Channel mapping
    web_paid_channel = models.ForeignKey('channels_config.DynamicChannel', on_delete=models.SET_NULL, 
                                         null=True, blank=True, related_name='shopify_paid_stores',
                                         help_text="Channel for prepaid Shopify orders")
    web_cod_channel = models.ForeignKey('channels_config.DynamicChannel', on_delete=models.SET_NULL,
                                        null=True, blank=True, related_name='shopify_cod_stores',
                                        help_text="Channel for COD Shopify orders")
    
    # Channel split rules
    cod_keywords = models.JSONField(default=list, help_text='COD gateway keywords e.g. ["COD", "Cash on Delivery"]')
    treat_pending_cod_as_confirmed = models.BooleanField(default=True, help_text="Treat pending COD as confirmed orders")
    
    # Lead/Customer rules
    create_lead_for_every_customer = models.BooleanField(default=True, help_text="Create lead for every new Shopify customer")
    auto_promote_lead_to_customer = models.BooleanField(default=True, help_text="Auto-promote lead to customer on first order")
    
    # Sync settings
    sync_enabled = models.BooleanField(default=False)
    sync_orders = models.BooleanField(default=True)
    sync_customers = models.BooleanField(default=True)
    sync_products = models.BooleanField(default=False)
    sync_inventory = models.BooleanField(default=False)
    auto_fulfill = models.BooleanField(default=False, help_text="Push fulfillment on SHIPPED status")
    push_partial_fulfillments = models.BooleanField(default=True)
    
    # Abandoned Checkout Sync Settings
    sync_abandoned_checkouts = models.BooleanField(default=True, help_text="Sync abandoned checkouts to Leads")
    sync_abandoned_carts = models.BooleanField(default=False)
    abandoned_sync_interval_minutes = models.IntegerField(default=15, help_text="How often to fetch abandoned checkouts")
    
    # Webhook settings
    webhook_secret = models.CharField(max_length=200, blank=True, null=True)
    orders_webhook_id = models.CharField(max_length=100, blank=True, null=True)
    checkouts_webhook_id = models.CharField(max_length=100, blank=True, null=True)
    customers_webhook_id = models.CharField(max_length=100, blank=True, null=True)
    fulfillments_webhook_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Scopes
    granted_scopes = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Shopify Store"
        verbose_name_plural = "Shopify Stores"
    
    def __str__(self):
        return self.store_name or self.name or self.shop_domain
    
    @staticmethod
    def get_list_url():
        return reverse_lazy("integrations:shopify_store_list")
    
    def get_absolute_url(self):
        return reverse_lazy("integrations:shopify_store_detail", kwargs={"pk": str(self.pk)})
    
    def get_update_url(self):
        return reverse_lazy("integrations:shopify_store_update", kwargs={"pk": str(self.pk)})
    
    def get_portal_url(self):
        return reverse_lazy("integrations:shopify_portal", kwargs={"pk": str(self.pk)})
    
    def get_cod_keywords_list(self):
        if not self.cod_keywords:
            return ['COD', 'Cash on Delivery', 'cash_on_delivery']
        return self.cod_keywords


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
        ('abandoned_checkouts', 'Abandoned Checkouts'),
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


class ShopifyAbandonedCheckout(BaseModel):
    """Track abandoned checkouts from Shopify for lead recovery."""
    RECOVERY_STATUS = [
        ('pending', 'Pending'),
        ('contacted', 'Contacted'),
        ('recovered', 'Recovered'),
        ('lost', 'Lost'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(ShopifyStore, on_delete=models.CASCADE, related_name='abandoned_checkouts')
    
    # Shopify IDs
    shopify_checkout_id = models.CharField(max_length=100, db_index=True)
    shopify_checkout_token = models.CharField(max_length=200, blank=True, null=True)
    
    # Customer info
    customer_email = models.EmailField(blank=True, null=True, db_index=True)
    customer_phone = models.CharField(max_length=20, blank=True, null=True, db_index=True)
    customer_phone_normalized = models.CharField(max_length=20, blank=True, null=True, db_index=True)
    customer_name = models.CharField(max_length=200, blank=True, null=True)
    
    # Cart details
    cart_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cart_items = models.JSONField(default=list, help_text="List of {product_title, quantity, price}")
    cart_item_count = models.IntegerField(default=0)
    currency = models.CharField(max_length=3, default='INR')
    
    # Recovery URL
    recovery_url = models.URLField(blank=True, null=True)
    
    # Timestamps from Shopify
    abandoned_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Status
    recovery_status = models.CharField(max_length=20, choices=RECOVERY_STATUS, default='pending', db_index=True)
    is_recovered = models.BooleanField(default=False)
    recovered_order = models.ForeignKey(
        ShopifyOrder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recovered_from_checkouts'
    )
    
    # Raw data
    shopify_data = models.JSONField(default=dict)
    
    # Link to ERP lead
    lead = models.ForeignKey(
        'marketing.Lead',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='shopify_checkouts'
    )
    
    class Meta:
        verbose_name = "Shopify Abandoned Checkout"
        verbose_name_plural = "Shopify Abandoned Checkouts"
        unique_together = ['store', 'shopify_checkout_id']
        ordering = ['-abandoned_at']
        indexes = [
            models.Index(fields=['customer_phone', 'recovery_status']),
            models.Index(fields=['customer_email', 'recovery_status']),
        ]
    
    def __str__(self):
        return f"Checkout {self.shopify_checkout_id} - ₹{self.cart_value}"


class ShopifyWebhookLog(BaseModel):
    """Log Shopify webhook deliveries for debugging."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    store = models.ForeignKey(ShopifyStore, on_delete=models.SET_NULL, null=True, blank=True)
    webhook_topic = models.CharField(max_length=100, db_index=True)  # orders/create, checkouts/update, etc.
    
    # Request info
    shopify_domain = models.CharField(max_length=200, blank=True, null=True)
    shopify_hmac = models.CharField(max_length=200, blank=True, null=True)
    
    # Payload
    payload = models.JSONField(default=dict)
    
    # Processing
    processed = models.BooleanField(default=False)
    processing_time_ms = models.IntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    
    # Results
    action_taken = models.CharField(max_length=100, blank=True, null=True)
    
    class Meta:
        verbose_name = "Shopify Webhook Log"
        verbose_name_plural = "Shopify Webhook Logs"
        ordering = ['-created']
    
    def __str__(self):
        return f"{self.webhook_topic} - {self.created}"


class ShopifyExternalMap(BaseModel):
    """Maps ERP internal IDs to Shopify external IDs."""
    ENTITY_TYPES = [
        ('ORDER', 'Order'),
        ('CUSTOMER', 'Customer'),
        ('ABANDONED_CHECKOUT', 'Abandoned Checkout'),
        ('FULFILLMENT', 'Fulfillment'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(ShopifyStore, on_delete=models.CASCADE, related_name='external_maps')
    entity_type = models.CharField(max_length=30, choices=ENTITY_TYPES, db_index=True)
    external_id = models.CharField(max_length=200, db_index=True, help_text="Shopify ID")
    internal_id = models.CharField(max_length=200, db_index=True, help_text="ERP internal UUID/ID")
    
    class Meta:
        verbose_name = "Shopify External Map"
        verbose_name_plural = "Shopify External Maps"
        unique_together = ['store', 'entity_type', 'external_id']
        ordering = ['-created']
    
    def __str__(self):
        return f"{self.entity_type}: {self.external_id} → {self.internal_id}"


class ShopifyEventInbox(BaseModel):
    """Idempotent inbox for incoming Shopify webhook events."""
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('DONE', 'Done'),
        ('FAILED', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(ShopifyStore, on_delete=models.CASCADE, related_name='event_inbox')
    topic = models.CharField(max_length=100, db_index=True)
    webhook_id = models.CharField(max_length=200, blank=True, null=True, help_text="Shopify webhook ID or idempotency key")
    idempotency_key = models.CharField(max_length=200, blank=True, null=True, db_index=True)
    payload_json = models.JSONField(default=dict)
    received_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    retries = models.IntegerField(default=0)
    last_error = models.TextField(blank=True, null=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Shopify Event Inbox"
        verbose_name_plural = "Shopify Event Inbox"
        unique_together = ['store', 'idempotency_key']
        ordering = ['-received_at']
        indexes = [
            models.Index(fields=['topic', 'status']),
            models.Index(fields=['status', 'received_at']),
        ]
    
    def __str__(self):
        return f"{self.topic} [{self.status}] @ {self.received_at}"


class ShopifyOutbox(BaseModel):
    """Outbound queue for ERP→Shopify pushes (fulfillments, tracking, tags)."""
    TYPE_CHOICES = [
        ('PUSH_FULFILLMENT', 'Push Fulfillment'),
        ('UPDATE_TRACKING', 'Update Tracking'),
        ('TAG_ORDER', 'Tag Order'),
        ('NOTE_ORDER', 'Note Order'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('DONE', 'Done'),
        ('FAILED', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(ShopifyStore, on_delete=models.CASCADE, related_name='outbox')
    type = models.CharField(max_length=30, choices=TYPE_CHOICES, db_index=True)
    ref_internal_id = models.CharField(max_length=200, blank=True, null=True, help_text="ERP order/shipment ID")
    ref_shopify_id = models.CharField(max_length=200, blank=True, null=True, help_text="Shopify order ID")
    request_json = models.JSONField(default=dict, help_text="Request payload to send")
    response_json = models.JSONField(default=dict, help_text="Response from Shopify")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    retries = models.IntegerField(default=0)
    last_error = models.TextField(blank=True, null=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Shopify Outbox"
        verbose_name_plural = "Shopify Outbox"
        ordering = ['-created']
        indexes = [
            models.Index(fields=['type', 'status']),
            models.Index(fields=['ref_internal_id', 'status']),
        ]
    
    def __str__(self):
        return f"{self.type} [{self.status}] {self.ref_internal_id}"


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
