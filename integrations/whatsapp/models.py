import uuid
from django.db import models
from django.urls import reverse_lazy
from django.utils import timezone
from core.base import BaseModel


class WhatsAppCustomer(BaseModel):
    """
    Global WhatsApp customer - deduplicated by wa_id (customer's phone number).
    If the same customer messages multiple sales numbers, only ONE record exists here.
    """
    
    # Attribution source choices
    ATTRIBUTION_SOURCE_CHOICES = [
        ('organic', 'Organic / Direct'),
        ('ctwa_ad', 'Click-to-WhatsApp Ad'),
        ('fb_ad', 'Facebook Ad'),
        ('ig_ad', 'Instagram Ad'),
        ('meta_ad', 'Meta Ad (Unspecified)'),
        ('google_ad', 'Google Ad'),
        ('referral', 'Referral'),
        ('unknown', 'Unknown'),
    ]
    
    # Source type for lead attribution
    SOURCE_TYPE_CHOICES = [
        ('organic', 'Organic'),
        ('ad', 'Ad'),
        ('unknown', 'Unknown'),
    ]
    
    # Lead conversion status
    LEAD_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('won', 'Won'),
        ('lost', 'Lost'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Unique identifier - customer's WhatsApp number (without +)
    wa_id = models.CharField(
        max_length=32, 
        unique=True, 
        db_index=True,
        help_text="Customer's WhatsApp ID (phone number without +)"
    )
    
    # Profile info from WhatsApp
    profile_name = models.CharField(max_length=255, blank=True, null=True)
    
    # Timestamps
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    
    # Last message preview
    last_message_preview = models.TextField(blank=True, null=True)
    last_message_at = models.DateTimeField(null=True, blank=True)
    
    # =============================================================================
    # ATTRIBUTION & AD TRACKING
    # =============================================================================
    is_from_ad = models.BooleanField(
        default=False, 
        db_index=True,
        help_text="True if first contact was from a Click-to-WhatsApp ad"
    )
    
    # Source type (organic, ad, unknown)
    source_type = models.CharField(
        max_length=20,
        choices=SOURCE_TYPE_CHOICES,
        default='unknown',
        db_index=True,
        help_text="Lead source type"
    )
    
    attribution_source = models.CharField(
        max_length=30, 
        choices=ATTRIBUTION_SOURCE_CHOICES, 
        default='unknown',
        db_index=True,
        help_text="How the customer discovered us"
    )
    
    # Ad platform (facebook, instagram, google, etc.)
    ad_platform = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        db_index=True,
        help_text="Ad platform (facebook, instagram, google)"
    )
    
    # Meta Ads specific fields (from referral data in webhook)
    meta_ad_id = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text="Meta Ad ID (from CTWA referral)"
    )
    meta_ad_source_id = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text="Source ID (Post/Creative ID)"
    )
    meta_ad_source_type = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        help_text="Source type (ad, post, etc.)"
    )
    meta_ad_source_url = models.URLField(
        blank=True, 
        null=True,
        help_text="Source URL (ad link)"
    )
    meta_ad_headline = models.CharField(
        max_length=500, 
        blank=True, 
        null=True,
        help_text="Ad headline text"
    )
    meta_ad_body = models.TextField(
        blank=True, 
        null=True,
        help_text="Ad body text"
    )
    meta_ctwa_clid = models.CharField(
        max_length=200, 
        blank=True, 
        null=True,
        db_index=True,
        help_text="Click-to-WhatsApp Click ID (for conversion tracking)"
    )
    
    # Campaign tracking
    meta_campaign_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
        help_text="Meta Campaign ID"
    )
    meta_adset_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Meta Ad Set ID"
    )
    
    # For Meta Conversions API (CAPI) tracking
    meta_fbclid = models.CharField(
        max_length=200, 
        blank=True, 
        null=True,
        db_index=True,
        help_text="Facebook Click ID"
    )
    google_gclid = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        db_index=True,
        help_text="Google Click ID"
    )
    
    # =============================================================================
    # LEAD STATUS & CONVERSION TRACKING
    # =============================================================================
    lead_status = models.CharField(
        max_length=20,
        choices=LEAD_STATUS_CHOICES,
        default='pending',
        db_index=True,
        help_text="Lead conversion status (Pending/Won/Lost)"
    )
    lead_created_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the lead was created (for matching period calculation)"
    )
    won_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the lead was marked as Won (conversion date)"
    )
    lost_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the lead was marked as Lost (after matching period)"
    )
    
    # Conversion tracking
    converted_order = models.ForeignKey(
        'master.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='converted_whatsapp_leads',
        help_text="Order that converted this lead"
    )
    conversion_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Value of the converted order"
    )
    conversion_sent = models.BooleanField(
        default=False,
        help_text="Whether conversion event was sent to Meta CAPI"
    )
    conversion_sent_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When conversion was sent to Meta"
    )
    conversion_event_id = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Meta CAPI event ID"
    )
    
    # Legacy field for backward compatibility
    conversion_sent_to_meta = models.BooleanField(
        default=False,
        help_text="DEPRECATED: Use conversion_sent instead"
    )
    
    # Custom tags for manual categorization
    tags = models.JSONField(
        default=list, 
        blank=True,
        help_text="Custom tags for categorization"
    )
    
    # =============================================================================
    # ASSIGNMENT & LINKING
    # =============================================================================
    # Assignment - sticky owner
    assigned_sales_user = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='whatsapp_customers',
        help_text="Assigned sales person (sticky - keeps same owner across channels)"
    )
    
    # Link to main Customer model (optional enrichment)
    linked_customer = models.ForeignKey(
        'master.Customer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='whatsapp_profiles',
        help_text="Linked ERP customer record"
    )
    
    # Link to Lead model for unified lead management
    linked_lead = models.ForeignKey(
        'marketing.Lead',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='whatsapp_profiles',
        help_text="Linked Lead record"
    )
    
    # Stats
    total_messages = models.IntegerField(default=0)
    total_channels_contacted = models.IntegerField(default=1)
    
    class Meta:
        verbose_name = "WhatsApp Customer"
        verbose_name_plural = "WhatsApp Customers"
        ordering = ['-last_seen']
        indexes = [
            models.Index(fields=['wa_id']),
            models.Index(fields=['last_seen']),
            models.Index(fields=['-last_message_at']),
            models.Index(fields=['is_from_ad']),
            models.Index(fields=['attribution_source']),
            models.Index(fields=['lead_status']),
            models.Index(fields=['source_type']),
            models.Index(fields=['meta_campaign_id']),
        ]
    
    def __str__(self):
        name = self.profile_name or 'Unknown'
        return f"{name} ({self.wa_id})"
    
    @staticmethod
    def get_list_url():
        return reverse_lazy("integrations:whatsapp_customer_list")
    
    def get_absolute_url(self):
        return reverse_lazy("integrations:whatsapp_customer_detail", kwargs={"pk": str(self.pk)})
    
    def formatted_phone(self):
        """Return phone in readable format."""
        if self.wa_id and len(self.wa_id) >= 10:
            return f"+{self.wa_id}"
        return self.wa_id
    
    def save(self, *args, **kwargs):
        # Set lead_created_at on first save
        if not self.lead_created_at:
            self.lead_created_at = self.first_seen or timezone.now()
        super().save(*args, **kwargs)
    
    def is_within_matching_period(self, days=7):
        """Check if lead is still within the matching period."""
        if not self.lead_created_at:
            return True
        cutoff = timezone.now() - timezone.timedelta(days=days)
        return self.lead_created_at > cutoff
    
    def mark_as_won(self, order, conversion_value=None):
        """Mark lead as Won with conversion details."""
        self.lead_status = 'won'
        self.won_at = timezone.now()
        self.converted_order = order
        self.conversion_value = conversion_value or order.total_amount
        self.conversion_sent = False  # Will be sent by Celery task
        self.save()
    
    def mark_as_lost(self):
        """Mark lead as Lost (no conversion within matching period)."""
        self.lead_status = 'lost'
        self.lost_at = timezone.now()
        self.save()


class WhatsAppConnectedNumber(BaseModel):
    """
    Stores WhatsApp Business numbers connected via Embedded Signup.
    Each record represents a number connected to the ERP for lead capture.
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending Setup'),
        ('active', 'Active'),
        ('disconnected', 'Disconnected'),
        ('error', 'Error'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Meta identifiers from Embedded Signup
    waba_id = models.CharField(
        max_length=64,
        db_index=True,
        help_text="WhatsApp Business Account ID from Meta"
    )
    phone_number_id = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="Phone Number ID from Meta"
    )
    
    # Display info
    display_phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Human-readable phone number"
    )
    display_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Business display name"
    )
    
    # Connection status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    
    # Auth tokens (encrypted in production)
    access_token = models.TextField(
        blank=True,
        null=True,
        help_text="Meta access token for this number"
    )
    token_expires_at = models.DateTimeField(
        null=True,
        blank=True
    )
    
    # Connected by user
    connected_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='connected_whatsapp_numbers'
    )
    
    # Webhook tracking
    webhook_verified = models.BooleanField(default=False)
    last_webhook_at = models.DateTimeField(null=True, blank=True)
    webhook_count = models.IntegerField(default=0)
    
    # Stats
    total_messages_received = models.IntegerField(default=0)
    total_leads_captured = models.IntegerField(default=0)
    
    # Metadata
    meta_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata from Embedded Signup"
    )
    
    class Meta:
        verbose_name = "Connected WhatsApp Number"
        verbose_name_plural = "Connected WhatsApp Numbers"
        ordering = ['-created']
    
    def __str__(self):
        return f"{self.display_name or self.display_phone_number or self.phone_number_id}"


class WhatsAppNumberConfig(BaseModel):
    """
    Configuration for each WhatsApp Business number connected.
    Tracks webhook activity per sales number.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Meta identifiers
    phone_number_id = models.CharField(
        max_length=64, 
        unique=True, 
        db_index=True,
        help_text="Meta's Phone Number ID from webhook metadata"
    )
    display_phone_number = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        help_text="Human-readable phone number"
    )
    
    # Friendly name for the number
    name = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text="Friendly name (e.g., 'Sales Team 1', 'Support')"
    )
    
    # Link to connected number (if connected via Embedded Signup)
    connected_number = models.OneToOneField(
        WhatsAppConnectedNumber,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='config'
    )
    
    # Webhook activity tracking
    last_webhook_at = models.DateTimeField(null=True, blank=True)
    webhook_count = models.IntegerField(default=0)
    
    # Stats
    total_messages_received = models.IntegerField(default=0)
    total_customers = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = "WhatsApp Number"
        verbose_name_plural = "WhatsApp Numbers"
        ordering = ['-last_webhook_at']
    
    def __str__(self):
        if self.name:
            return f"{self.name} ({self.display_phone_number or self.phone_number_id})"
        return self.display_phone_number or self.phone_number_id


class WhatsAppCustomerChannel(BaseModel):
    """
    Touchpoint: tracks which sales numbers a customer has contacted.
    Unique constraint on (customer, phone_number_id).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    customer = models.ForeignKey(
        WhatsAppCustomer,
        on_delete=models.CASCADE,
        related_name='channels'
    )
    
    # The sales number they contacted
    phone_number_id = models.CharField(
        max_length=64, 
        db_index=True,
        help_text="Meta's Phone Number ID (sales number)"
    )
    
    # Optional link to number config
    number_config = models.ForeignKey(
        WhatsAppNumberConfig,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customer_channels'
    )
    
    # Timestamps for this specific channel
    first_contact_at = models.DateTimeField(auto_now_add=True)
    last_contact_at = models.DateTimeField(auto_now=True)
    
    # Stats for this channel
    message_count = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = "Customer Channel"
        verbose_name_plural = "Customer Channels"
        unique_together = ['customer', 'phone_number_id']
        indexes = [
            models.Index(fields=['customer', 'phone_number_id']),
            models.Index(fields=['-last_contact_at']),
        ]
    
    def __str__(self):
        return f"{self.customer.wa_id} via {self.phone_number_id}"


class WhatsAppMessage(BaseModel):
    """
    Store inbound (and optionally outbound) WhatsApp messages.
    """
    DIRECTION_CHOICES = [
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound'),
    ]
    
    MSG_TYPE_CHOICES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('document', 'Document'),
        ('sticker', 'Sticker'),
        ('location', 'Location'),
        ('contacts', 'Contacts'),
        ('interactive', 'Interactive'),
        ('button', 'Button'),
        ('reaction', 'Reaction'),
        ('unknown', 'Unknown'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Link to customer
    customer = models.ForeignKey(
        WhatsAppCustomer,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    
    # The sales number this message was sent to/from
    phone_number_id = models.CharField(
        max_length=64, 
        db_index=True,
        help_text="Meta's Phone Number ID (sales number)"
    )
    
    # Meta's message ID (for deduplication)
    message_id = models.CharField(
        max_length=128, 
        unique=True,
        db_index=True,
        help_text="Meta's unique message ID"
    )
    
    # Direction
    direction = models.CharField(
        max_length=10, 
        choices=DIRECTION_CHOICES, 
        default='inbound'
    )
    
    # Message type and content
    msg_type = models.CharField(
        max_length=32, 
        choices=MSG_TYPE_CHOICES, 
        default='unknown'
    )
    body = models.TextField(blank=True, null=True, help_text="Message text content")
    
    # Media (if applicable)
    media_id = models.CharField(max_length=200, blank=True, null=True)
    media_url = models.URLField(blank=True, null=True)
    media_mime_type = models.CharField(max_length=100, blank=True, null=True)
    
    # Timestamps
    timestamp_utc = models.DateTimeField(help_text="Message timestamp from Meta")
    
    # Raw payload for debugging
    raw_payload = models.JSONField(default=dict, blank=True)
    
    class Meta:
        verbose_name = "WhatsApp Message"
        verbose_name_plural = "WhatsApp Messages"
        ordering = ['-timestamp_utc']
        indexes = [
            models.Index(fields=['customer', 'phone_number_id']),
            models.Index(fields=['-timestamp_utc']),
            models.Index(fields=['message_id']),
        ]
    
    def __str__(self):
        return f"{self.direction}: {self.customer.wa_id} - {self.msg_type}"


class WhatsAppWebhookLog(BaseModel):
    """
    Log all webhook requests for debugging.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    phone_number_id = models.CharField(max_length=64, blank=True, null=True)
    event_type = models.CharField(max_length=50, blank=True, null=True)
    
    # Request details
    payload = models.JSONField(default=dict)
    
    # Processing result
    processed = models.BooleanField(default=False)
    error_message = models.TextField(blank=True, null=True)
    
    # Stats
    messages_processed = models.IntegerField(default=0)
    customers_created = models.IntegerField(default=0)
    customers_updated = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = "Webhook Log"
        verbose_name_plural = "Webhook Logs"
        ordering = ['-created']
    
    def __str__(self):
        return f"Webhook {self.created}: {self.event_type or 'unknown'}"


# =============================================================================
# META INTEGRATION CONFIGURATION
# =============================================================================

class MetaConversionConfig(BaseModel):
    """
    Configuration for Meta Conversions API (CAPI).
    Stores pixel ID and access token for sending conversion events.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(
        max_length=100,
        default='Default',
        help_text="Configuration name"
    )
    
    pixel_id = models.CharField(
        max_length=64,
        help_text="Meta Pixel ID"
    )
    
    access_token = models.TextField(
        blank=True,
        null=True,
        help_text="Meta System User Access Token with ads_management permission"
    )
    
    # Settings
    is_active = models.BooleanField(default=True)
    test_mode = models.BooleanField(
        default=False,
        help_text="If true, events are sent with test_event_code"
    )
    test_event_code = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Test event code for testing (from Events Manager)"
    )
    
    # Stats
    events_sent = models.IntegerField(default=0)
    last_event_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Meta Conversion Config"
        verbose_name_plural = "Meta Conversion Configs"
    
    def __str__(self):
        return f"{self.name} (Pixel: {self.pixel_id})"


class MetaAdsConfig(BaseModel):
    """
    Configuration for Meta Ads Insights API.
    Used to fetch ad spend data for ROAS calculation.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(
        max_length=100,
        default='Default',
        help_text="Configuration name"
    )
    
    ad_account_id = models.CharField(
        max_length=64,
        help_text="Meta Ad Account ID (without act_ prefix)"
    )
    
    access_token = models.TextField(
        blank=True,
        null=True,
        help_text="Meta System User Access Token with ads_read permission"
    )
    
    # Business Portfolio ID for Embedded Signup
    business_id = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="Meta Business Portfolio ID (required for Embedded Signup)"
    )
    
    # Settings
    is_active = models.BooleanField(default=True)
    
    # Stats
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Meta Ads Config"
        verbose_name_plural = "Meta Ads Configs"
    
    def __str__(self):
        return f"{self.name} (Account: {self.ad_account_id})"


# =============================================================================
# DAILY REPORTING
# =============================================================================

class DailyLeadReport(BaseModel):
    """
    Aggregated daily statistics per WhatsApp number.
    Generated by Celery task at 02:00 IST.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Report date
    report_date = models.DateField(db_index=True)
    
    # WhatsApp number (optional - null means aggregate for all numbers)
    phone_number_id = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        db_index=True,
        help_text="Phone Number ID (null for aggregate)"
    )
    number_config = models.ForeignKey(
        WhatsAppNumberConfig,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='daily_reports'
    )
    
    # Campaign (optional)
    campaign_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
        help_text="Meta Campaign ID for campaign-level reporting"
    )
    
    # Lead Metrics
    total_leads = models.IntegerField(default=0)
    ad_leads = models.IntegerField(default=0)
    organic_leads = models.IntegerField(default=0)
    
    # Conversion Metrics
    conversions = models.IntegerField(default=0)
    conversion_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Conversion rate as percentage"
    )
    
    # Revenue
    revenue = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        help_text="Total conversion revenue"
    )
    
    # Ad Spend (from Meta Ads API)
    ad_spend = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        help_text="Ad spend from Meta Ads Insights"
    )
    
    # ROAS
    roas = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Return on Ad Spend (revenue / ad_spend)"
    )
    
    # Status breakdown
    pending_leads = models.IntegerField(default=0)
    won_leads = models.IntegerField(default=0)
    lost_leads = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = "Daily Lead Report"
        verbose_name_plural = "Daily Lead Reports"
        unique_together = ['report_date', 'phone_number_id', 'campaign_id']
        ordering = ['-report_date']
        indexes = [
            models.Index(fields=['report_date', 'phone_number_id']),
            models.Index(fields=['report_date', 'campaign_id']),
        ]
    
    def __str__(self):
        number = self.phone_number_id or 'All Numbers'
        return f"{self.report_date} - {number}"
    
    def calculate_roas(self):
        """Calculate ROAS from revenue and ad spend."""
        if self.ad_spend > 0:
            self.roas = self.revenue / self.ad_spend
        else:
            self.roas = 0
        return self.roas


class LeadConversionEvent(BaseModel):
    """
    Track individual conversion events sent to Meta CAPI.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Link to customer
    customer = models.ForeignKey(
        WhatsAppCustomer,
        on_delete=models.CASCADE,
        related_name='conversion_events'
    )
    
    # Link to order
    order = models.ForeignKey(
        'master.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='whatsapp_conversion_events'
    )
    
    # Event details
    event_name = models.CharField(
        max_length=50,
        default='Purchase',
        help_text="Meta event name (Purchase, Lead, etc.)"
    )
    event_time = models.DateTimeField()
    event_id = models.CharField(
        max_length=200,
        unique=True,
        help_text="Unique event ID for deduplication"
    )
    
    # Conversion value
    value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    currency = models.CharField(max_length=3, default='INR')
    
    # Attribution data
    fbclid = models.CharField(max_length=200, blank=True, null=True)
    ctwa_clid = models.CharField(max_length=200, blank=True, null=True)
    campaign_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Send status
    sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    response_code = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    retry_count = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = "Lead Conversion Event"
        verbose_name_plural = "Lead Conversion Events"
        ordering = ['-event_time']
        indexes = [
            models.Index(fields=['sent', 'event_time']),
            models.Index(fields=['customer', 'event_time']),
        ]
    
    def __str__(self):
        return f"{self.event_name}: {self.customer.wa_id} - {self.value} {self.currency}"
