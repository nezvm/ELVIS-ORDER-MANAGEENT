import uuid
from django.db import models
from django.urls import reverse_lazy
from django.db.models import Sum, Count, Avg, F, Q
from core.base import BaseModel
from decimal import Decimal


class Lead(BaseModel):
    """Leads from Google Contacts sync, Shopify Abandoned, or manual entry."""
    MATCH_STATUS = [
        ('win', 'WIN - Matched'),
        ('loss', 'LOSS - Not Matched'),
        ('pending', 'Pending Review'),
        ('converted', 'CONVERTED - Order Placed'),
    ]
    
    LEAD_STATUS = [
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('interested', 'Interested'),
        ('not_interested', 'Not Interested'),
        ('follow_up', 'Follow Up'),
        ('converted', 'Converted'),
        ('dormant', 'Dormant'),
    ]
    
    LEAD_SOURCES = [
        ('manual', 'Manual Entry'),
        ('whatsapp_vcf_import', 'WhatsApp VCF Import'),
        ('google_contacts_sync', 'Google Contacts Sync'),
        ('shopify_abandoned_checkout', 'Shopify Abandoned Checkout'),
        ('shopify_abandoned_cart', 'Shopify Abandoned Cart'),
        ('website_form', 'Website Form'),
        ('referral', 'Referral'),
    ]
    
    LOCATION_STATUS = [
        ('unknown', 'Unknown'),
        ('enriched', 'Enriched'),
        ('verified', 'Verified'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Identity
    phone_no = models.CharField(max_length=20, db_index=True, blank=True, null=True)
    phone_normalized = models.CharField(max_length=20, db_index=True, blank=True, null=True, help_text="E.164 format")
    name = models.CharField(max_length=200, blank=True, null=True)
    original_google_name = models.CharField(max_length=200, blank=True, null=True, help_text="Original name from Google before correction")
    email = models.EmailField(blank=True, null=True, db_index=True)
    email_normalized = models.EmailField(blank=True, null=True, db_index=True, help_text="Lowercase trimmed email")
    
    # Lead Source
    lead_source = models.CharField(max_length=50, choices=LEAD_SOURCES, default='manual')
    source_ref_id = models.CharField(max_length=200, blank=True, null=True, help_text="External reference ID (Shopify checkout/cart ID)")
    source_payload = models.JSONField(default=dict, blank=True, help_text="Raw snapshot from source")
    captured_at = models.DateTimeField(auto_now_add=True, help_text="When lead was captured in ERP")
    needs_phone = models.BooleanField(default=False, help_text="True if lead created from email only")
    
    # Shopify Abandoned Checkout/Cart Fields
    recover_url = models.URLField(blank=True, null=True, help_text="Checkout recovery link")
    cart_value = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Abandoned cart value")
    cart_items_summary = models.JSONField(default=list, help_text="List of product titles + qty")
    abandoned_at = models.DateTimeField(blank=True, null=True, help_text="Shopify abandoned timestamp")
    shopify_store = models.ForeignKey('integrations.ShopifyStore', on_delete=models.SET_NULL, null=True, blank=True, related_name='abandoned_leads')
    
    # Google Sync
    google_resource_name = models.CharField(max_length=200, blank=True, null=True, unique=True)
    google_sync_config = models.ForeignKey('integrations.GoogleWorkspaceConfig', on_delete=models.SET_NULL, null=True, blank=True, related_name='leads')
    source_device = models.CharField(max_length=200, blank=True, null=True)
    source_user = models.CharField(max_length=200, blank=True, null=True)
    first_synced_at = models.DateTimeField(auto_now_add=True)
    last_synced_at = models.DateTimeField(auto_now=True)
    
    # Location
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    district = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    pincode = models.CharField(max_length=10, blank=True, null=True, db_index=True)
    country = models.CharField(max_length=100, default='India')
    location_status = models.CharField(max_length=20, choices=LOCATION_STATUS, default='unknown')
    
    # Match Status
    match_status = models.CharField(max_length=20, choices=MATCH_STATUS, default='pending')
    matched_customer = models.ForeignKey('master.Customer', on_delete=models.SET_NULL, null=True, blank=True, related_name='matched_leads')
    matched_order = models.ForeignKey('master.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='matched_leads')
    
    # Conversion Tracking
    converted_order = models.ForeignKey('master.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='converted_leads', help_text="Order that converted this lead")
    conversion_days = models.IntegerField(null=True, blank=True, help_text="Days from abandoned to conversion")
    
    # Lead Management
    lead_status = models.CharField(max_length=20, choices=LEAD_STATUS, default='new')
    assigned_to = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_leads')
    follow_up_date = models.DateField(null=True, blank=True)
    last_contacted_at = models.DateTimeField(null=True, blank=True)
    conversion_date = models.DateField(null=True, blank=True)
    
    # Segmentation
    order_behavior_segment = models.CharField(max_length=50, blank=True, null=True)
    lifecycle_stage = models.CharField(max_length=50, blank=True, null=True)
    channel_loyalty = models.CharField(max_length=50, blank=True, null=True)
    value_tier = models.CharField(max_length=30, blank=True, null=True)
    risk_status = models.CharField(max_length=30, blank=True, null=True)
    
    # Computed Metrics
    lifetime_order_count = models.IntegerField(default=0)
    lifetime_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    first_order_date = models.DateField(null=True, blank=True)
    last_order_date = models.DateField(null=True, blank=True)
    primary_channel = models.CharField(max_length=100, blank=True, null=True)
    channels_used = models.JSONField(default=list)
    
    # Communication
    whatsapp_opt_in = models.BooleanField(default=True)
    sms_opt_in = models.BooleanField(default=True)
    last_broadcast_at = models.DateTimeField(null=True, blank=True)
    broadcast_count = models.IntegerField(default=0)
    
    # Notes
    notes = models.TextField(blank=True, null=True)
    tags = models.JSONField(default=list)
    
    class Meta:
        verbose_name = "Lead"
        verbose_name_plural = "Leads"
        ordering = ['-created']
    
    def __str__(self):
        return f"{self.name or 'Unknown'} ({self.phone_no})"
    
    @staticmethod
    def get_list_url():
        return reverse_lazy("marketing:lead_list")
    
    def get_absolute_url(self):
        return reverse_lazy("marketing:lead_detail", kwargs={"pk": str(self.pk)})
    
    def get_update_url(self):
        return reverse_lazy("marketing:lead_update", kwargs={"pk": str(self.pk)})


class LeadActivity(BaseModel):
    """Activity timeline for leads."""
    ACTIVITY_TYPES = [
        ('synced', 'Synced from Google'),
        ('name_updated', 'Name Updated'),
        ('broadcast_sent', 'Broadcast Sent'),
        ('broadcast_delivered', 'Broadcast Delivered'),
        ('reply_received', 'Reply Received'),
        ('contacted', 'Contacted'),
        ('status_changed', 'Status Changed'),
        ('assigned', 'Assigned to Agent'),
        ('converted', 'Converted to Customer'),
        ('note_added', 'Note Added'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=30, choices=ACTIVITY_TYPES)
    description = models.TextField(blank=True, null=True)
    metadata = models.JSONField(default=dict)
    performed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = "Lead Activity"
        verbose_name_plural = "Lead Activities"
        ordering = ['-created']
    
    def __str__(self):
        return f"{self.lead} - {self.activity_type}"


# WhatsApp Provider Management
class WhatsAppProvider(BaseModel):
    """Plug-and-play WhatsApp provider configuration."""
    PROVIDER_TYPES = [
        ('meta_cloud', 'Meta Cloud API'),
        ('gupshup', 'Gupshup'),
        ('wati', 'WATI'),
        ('twilio', 'Twilio'),
        ('custom', 'Custom API'),
    ]
    
    STATUS_CHOICES = [
        ('connected', 'Connected'),
        ('error', 'Error'),
        ('disabled', 'Disabled'),
        ('pending', 'Pending Setup'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    provider_type = models.CharField(max_length=30, choices=PROVIDER_TYPES)
    is_default = models.BooleanField(default=False)
    
    # Credentials (should be encrypted in production)
    api_key = models.CharField(max_length=500, blank=True, null=True)
    api_secret = models.CharField(max_length=500, blank=True, null=True)
    access_token = models.TextField(blank=True, null=True)
    phone_number_id = models.CharField(max_length=100, blank=True, null=True, help_text="WABA Phone Number ID")
    waba_id = models.CharField(max_length=100, blank=True, null=True, help_text="WhatsApp Business Account ID")
    
    # Webhook
    webhook_url = models.URLField(blank=True, null=True)
    webhook_secret = models.CharField(max_length=200, blank=True, null=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    last_test_at = models.DateTimeField(null=True, blank=True)
    last_test_result = models.TextField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    
    # Rate Limits
    rate_limit_per_second = models.IntegerField(default=80)
    daily_limit = models.IntegerField(default=100000)
    messages_sent_today = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = "WhatsApp Provider"
        verbose_name_plural = "WhatsApp Providers"
    
    def __str__(self):
        return f"{self.name} ({self.get_provider_type_display()})"
    
    @staticmethod
    def get_list_url():
        return reverse_lazy("marketing:provider_list")
    
    def get_absolute_url(self):
        return reverse_lazy("marketing:provider_detail", kwargs={"pk": str(self.pk)})


class WhatsAppTemplate(BaseModel):
    """WhatsApp message templates."""
    CATEGORIES = [
        ('marketing', 'Marketing'),
        ('utility', 'Utility'),
        ('authentication', 'Authentication'),
    ]
    
    LANGUAGES = [
        ('en', 'English'),
        ('hi', 'Hindi'),
        ('ta', 'Tamil'),
        ('te', 'Telugu'),
        ('mr', 'Marathi'),
        ('bn', 'Bengali'),
        ('gu', 'Gujarati'),
        ('kn', 'Kannada'),
        ('ml', 'Malayalam'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(WhatsAppProvider, on_delete=models.CASCADE, related_name='templates')
    name = models.CharField(max_length=100)
    template_id = models.CharField(max_length=100, blank=True, null=True, help_text="Provider's template ID")
    category = models.CharField(max_length=30, choices=CATEGORIES, default='utility')
    language = models.CharField(max_length=10, choices=LANGUAGES, default='en')
    
    # Content
    header_type = models.CharField(max_length=20, blank=True, null=True, choices=[('text', 'Text'), ('image', 'Image'), ('video', 'Video'), ('document', 'Document')])
    header_content = models.TextField(blank=True, null=True)
    body = models.TextField(help_text="Use {{1}}, {{2}} etc for variables")
    footer = models.CharField(max_length=60, blank=True, null=True)
    
    # Variables
    variables = models.JSONField(default=list, help_text="List of variable mappings")
    sample_values = models.JSONField(default=list)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='approved')
    
    class Meta:
        verbose_name = "WhatsApp Template"
        verbose_name_plural = "WhatsApp Templates"
        unique_together = ['provider', 'name', 'language']
    
    def __str__(self):
        return f"{self.name} ({self.language})"
    
    @staticmethod
    def get_list_url():
        return reverse_lazy("marketing:template_list")


class NotificationEvent(BaseModel):
    """Event-driven notification configuration."""
    EVENT_TYPES = [
        ('order_created', 'Order Created'),
        ('payment_received', 'Payment Received'),
        ('utr_captured', 'UTR Captured'),
        ('shipment_assigned', 'Shipment Assigned'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('ndr_raised', 'NDR Raised'),
        ('rto_initiated', 'RTO Initiated'),
        ('low_stock', 'Low Stock Alert'),
    ]
    
    AUDIENCE_TYPES = [
        ('customer', 'Customer'),
        ('internal', 'Internal Staff'),
        ('both', 'Both'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES, unique=True)
    is_enabled = models.BooleanField(default=False)
    
    # Template
    template = models.ForeignKey(WhatsAppTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    provider = models.ForeignKey(WhatsAppProvider, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Audience
    audience = models.CharField(max_length=20, choices=AUDIENCE_TYPES, default='customer')
    internal_recipients = models.JSONField(default=list, help_text="Phone numbers for internal notifications")
    
    # Settings
    retry_count = models.IntegerField(default=3)
    retry_delay_seconds = models.IntegerField(default=300)
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Notification Event"
        verbose_name_plural = "Notification Events"
    
    def __str__(self):
        return f"{self.get_event_type_display()} - {'Enabled' if self.is_enabled else 'Disabled'}"


class Campaign(BaseModel):
    """WhatsApp broadcast campaigns."""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('running', 'Running'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    
    # Provider & Template
    provider = models.ForeignKey(WhatsAppProvider, on_delete=models.PROTECT, related_name='campaigns')
    template = models.ForeignKey(WhatsAppTemplate, on_delete=models.PROTECT, related_name='campaigns')
    
    # Audience
    audience_filters = models.JSONField(default=dict, help_text="Filters for audience selection")
    audience_count = models.IntegerField(default=0)
    
    # Scheduling
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    scheduled_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Throttling
    throttle_rate = models.IntegerField(default=50, help_text="Messages per second")
    
    # Stats
    total_recipients = models.IntegerField(default=0)
    sent_count = models.IntegerField(default=0)
    delivered_count = models.IntegerField(default=0)
    read_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)
    opted_out_count = models.IntegerField(default=0)
    
    # Attribution
    attribution_window_days = models.IntegerField(default=7, help_text="Days to track conversions after campaign")
    conversions = models.IntegerField(default=0)
    conversion_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='created_campaigns')
    
    class Meta:
        verbose_name = "Campaign"
        verbose_name_plural = "Campaigns"
        ordering = ['-created']
    
    def __str__(self):
        return self.name
    
    @staticmethod
    def get_list_url():
        return reverse_lazy("marketing:campaign_list")
    
    def get_absolute_url(self):
        return reverse_lazy("marketing:campaign_detail", kwargs={"pk": str(self.pk)})


class CampaignRecipient(BaseModel):
    """Individual recipient in a campaign."""
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
        ('failed', 'Failed'),
        ('opted_out', 'Opted Out'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='recipients')
    lead = models.ForeignKey(Lead, on_delete=models.SET_NULL, null=True, blank=True, related_name='campaign_messages')
    phone_no = models.CharField(max_length=20)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    message_id = models.CharField(max_length=200, blank=True, null=True)
    
    # Timestamps
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Error
    error_code = models.CharField(max_length=50, blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    
    # Conversion
    converted = models.BooleanField(default=False)
    conversion_order = models.ForeignKey('master.Order', on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = "Campaign Recipient"
        verbose_name_plural = "Campaign Recipients"
        unique_together = ['campaign', 'phone_no']
    
    def __str__(self):
        return f"{self.campaign.name} - {self.phone_no}"


class MessageLog(BaseModel):
    """Log of all WhatsApp messages sent."""
    MESSAGE_TYPES = [
        ('notification', 'Notification'),
        ('broadcast', 'Broadcast'),
        ('manual', 'Manual'),
    ]
    
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(WhatsAppProvider, on_delete=models.SET_NULL, null=True)
    template = models.ForeignKey(WhatsAppTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES)
    phone_no = models.CharField(max_length=20, db_index=True)
    
    # Content
    message_content = models.TextField(blank=True, null=True)
    variables_used = models.JSONField(default=dict)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    message_id = models.CharField(max_length=200, blank=True, null=True)
    
    # Timestamps
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Error
    error_code = models.CharField(max_length=50, blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    
    # Reference
    event_type = models.CharField(max_length=50, blank=True, null=True)
    reference_type = models.CharField(max_length=50, blank=True, null=True)
    reference_id = models.CharField(max_length=100, blank=True, null=True)
    campaign = models.ForeignKey(Campaign, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = "Message Log"
        verbose_name_plural = "Message Logs"
        ordering = ['-created']
    
    def __str__(self):
        return f"{self.phone_no} - {self.status}"


class DoNotMessage(BaseModel):
    """Opt-out / Do-not-message list."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_no = models.CharField(max_length=20, unique=True, db_index=True)
    reason = models.CharField(max_length=100, blank=True, null=True)
    opted_out_at = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=50, blank=True, null=True)  # 'keyword', 'manual', 'complaint'
    
    class Meta:
        verbose_name = "Do Not Message"
        verbose_name_plural = "Do Not Message List"
    
    def __str__(self):
        return self.phone_no


# Market Insights Models
class GeoMarketStats(BaseModel):
    """Aggregated statistics by geographic region."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Location
    state = models.CharField(max_length=100, db_index=True)
    district = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    pincode = models.CharField(max_length=10, blank=True, null=True, db_index=True)
    
    # Period
    period_type = models.CharField(max_length=20, choices=[('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly'), ('all_time', 'All Time')])
    period_date = models.DateField(db_index=True)
    
    # Lead Metrics
    leads_count = models.IntegerField(default=0)
    win_count = models.IntegerField(default=0)
    loss_count = models.IntegerField(default=0)
    conversion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Order Metrics
    orders_count = models.IntegerField(default=0)
    revenue = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cod_orders = models.IntegerField(default=0)
    prepaid_orders = models.IntegerField(default=0)
    cod_share = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Delivery Metrics
    delivered_count = models.IntegerField(default=0)
    rto_count = models.IntegerField(default=0)
    rto_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Customer Metrics
    unique_customers = models.IntegerField(default=0)
    repeat_customers = models.IntegerField(default=0)
    repeat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    new_customers = models.IntegerField(default=0)
    
    # First Order Date
    first_order_date = models.DateField(null=True, blank=True)
    
    # Market Tags
    market_category = models.CharField(max_length=50, blank=True, null=True, choices=[
        ('hot', 'Hot Market'),
        ('cold', 'Cold/Loss Market'),
        ('new', 'New Market'),
        ('growing', 'Growing Market'),
        ('high_rto', 'High RTO Market'),
    ])
    
    class Meta:
        verbose_name = "Geo Market Stats"
        verbose_name_plural = "Geo Market Stats"
        unique_together = ['state', 'district', 'pincode', 'period_type', 'period_date']
        ordering = ['-revenue']
    
    def __str__(self):
        location = f"{self.state}"
        if self.district:
            location += f" > {self.district}"
        if self.pincode:
            location += f" > {self.pincode}"
        return location
