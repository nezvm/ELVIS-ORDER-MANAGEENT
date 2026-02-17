"""
Wabis WhatsApp BSP Integration Models

Models for WhatsApp lead intake via Wabis BSP:
- WabisConfig: BSP credentials and settings
- WabisNumber: Registered WhatsApp business numbers
- WabisMessage: Incoming/outgoing messages
- WabisWebhookLog: Raw webhook payload storage
"""

import uuid
from django.db import models
from django.urls import reverse_lazy
from django.utils import timezone
from core.base import BaseModel


class WabisConfig(BaseModel):
    """
    Wabis BSP configuration and credentials.
    Single instance for the organization.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, default='Default Wabis Config')
    
    # API Credentials
    api_key = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Wabis API Key from developer console"
    )
    api_secret = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Wabis API Secret"
    )
    webhook_secret = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Secret for webhook signature verification"
    )
    verify_token = models.CharField(
        max_length=200,
        default='elvis_wabis_verify_2024',
        help_text="Token for webhook verification handshake"
    )
    
    # API Endpoints
    api_base_url = models.URLField(
        default='https://bot.wabis.in/api',
        help_text="Wabis API base URL"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    connection_status = models.CharField(
        max_length=30,
        choices=[
            ('connected', 'Connected'),
            ('disconnected', 'Disconnected'),
            ('error', 'Error'),
        ],
        default='disconnected'
    )
    last_webhook_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True, null=True)
    
    # Stats
    total_messages_received = models.IntegerField(default=0)
    total_messages_sent = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = "Wabis Config"
        verbose_name_plural = "Wabis Configs"
    
    def __str__(self):
        return f"{self.name} ({self.connection_status})"


class WabisNumber(BaseModel):
    """
    WhatsApp Business Number registered with Wabis.
    Tracks each business number separately for per-number metrics.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Wabis/Meta identifiers
    phone_number_id = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="Phone Number ID from Wabis/Meta"
    )
    waba_id = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="WhatsApp Business Account ID"
    )
    
    # Display info
    display_phone_number = models.CharField(
        max_length=20,
        help_text="Human-readable phone number"
    )
    display_name = models.CharField(
        max_length=100,
        help_text="Business display name"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('inactive', 'Inactive'),
            ('pending', 'Pending'),
            ('error', 'Error'),
        ],
        default='active'
    )
    webhook_verified = models.BooleanField(default=False)
    
    # Activity tracking
    last_message_at = models.DateTimeField(null=True, blank=True)
    total_messages_received = models.IntegerField(default=0)
    total_customers = models.IntegerField(default=0)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        verbose_name = "Wabis Number"
        verbose_name_plural = "Wabis Numbers"
        ordering = ['-last_message_at']
    
    def __str__(self):
        return f"{self.display_name} ({self.display_phone_number})"


class WabisCustomer(BaseModel):
    """
    Global WhatsApp customer - deduplicated by wa_id (customer's phone).
    One record per customer regardless of which business number they contacted.
    """
    
    # Source type for attribution
    SOURCE_TYPE_CHOICES = [
        ('organic', 'Organic'),
        ('ads', 'Ads'),
        ('unknown', 'Unknown'),
    ]
    
    # Conversion status
    CONVERSION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('won', 'Won'),
        ('lost', 'Lost'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Unique identifier - customer's WhatsApp number
    wa_id = models.CharField(
        max_length=32,
        unique=True,
        db_index=True,
        help_text="Customer's WhatsApp ID (phone number without +)"
    )
    
    # Profile info
    profile_name = models.CharField(max_length=255, blank=True, null=True)
    
    # Timestamps
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    last_message_at = models.DateTimeField(null=True, blank=True)
    last_message_preview = models.TextField(blank=True, null=True)
    
    # =============================================================================
    # ATTRIBUTION & AD TRACKING
    # =============================================================================
    source_type = models.CharField(
        max_length=20,
        choices=SOURCE_TYPE_CHOICES,
        default='unknown',
        db_index=True
    )
    is_from_ad = models.BooleanField(default=False, db_index=True)
    
    # Meta Ads Attribution (placeholders for ROAS)
    meta_fbclid = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        db_index=True,
        help_text="Facebook Click ID"
    )
    meta_campaign_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True
    )
    meta_adset_id = models.CharField(max_length=100, blank=True, null=True)
    meta_ad_id = models.CharField(max_length=100, blank=True, null=True)
    meta_ctwa_clid = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Click-to-WhatsApp Click ID"
    )
    
    # Ad content captured
    ad_headline = models.CharField(max_length=500, blank=True, null=True)
    ad_body = models.TextField(blank=True, null=True)
    ad_source_url = models.URLField(blank=True, null=True)
    
    # =============================================================================
    # CONVERSION TRACKING
    # =============================================================================
    conversion_status = models.CharField(
        max_length=20,
        choices=CONVERSION_STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    lead_created_at = models.DateTimeField(null=True, blank=True)
    won_at = models.DateTimeField(null=True, blank=True)
    lost_at = models.DateTimeField(null=True, blank=True)
    
    # Linked order for conversion
    converted_order = models.ForeignKey(
        'master.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='wabis_converted_leads'
    )
    conversion_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    
    # Meta CAPI tracking
    conversion_sent_to_meta = models.BooleanField(default=False)
    conversion_sent_at = models.DateTimeField(null=True, blank=True)
    conversion_event_id = models.CharField(max_length=200, blank=True, null=True)
    
    # =============================================================================
    # LINKS
    # =============================================================================
    linked_lead = models.ForeignKey(
        'marketing.Lead',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='wabis_profiles'
    )
    linked_customer = models.ForeignKey(
        'master.Customer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='wabis_profiles'
    )
    assigned_to = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='wabis_customers'
    )
    
    # Stats
    total_messages = models.IntegerField(default=0)
    total_channels = models.IntegerField(default=1)
    tags = models.JSONField(default=list, blank=True)
    
    class Meta:
        verbose_name = "Wabis Customer"
        verbose_name_plural = "Wabis Customers"
        ordering = ['-last_message_at']
        indexes = [
            models.Index(fields=['wa_id']),
            models.Index(fields=['source_type']),
            models.Index(fields=['conversion_status']),
            models.Index(fields=['meta_campaign_id']),
        ]
    
    def __str__(self):
        return f"{self.profile_name or 'Unknown'} ({self.wa_id})"
    
    def formatted_phone(self):
        if self.wa_id and len(self.wa_id) >= 10:
            return f"+{self.wa_id}"
        return self.wa_id
    
    def mark_as_won(self, order, value=None):
        self.conversion_status = 'won'
        self.won_at = timezone.now()
        self.converted_order = order
        self.conversion_value = value or order.total_amount
        self.save()
    
    def mark_as_lost(self):
        self.conversion_status = 'lost'
        self.lost_at = timezone.now()
        self.save()


class WabisCustomerChannel(BaseModel):
    """
    Touchpoint: tracks which business numbers a customer has contacted.
    Enables per-number metrics.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    customer = models.ForeignKey(
        WabisCustomer,
        on_delete=models.CASCADE,
        related_name='channels'
    )
    number = models.ForeignKey(
        WabisNumber,
        on_delete=models.CASCADE,
        related_name='customer_channels'
    )
    
    # Timestamps
    first_contact_at = models.DateTimeField(auto_now_add=True)
    last_contact_at = models.DateTimeField(auto_now=True)
    
    # Stats
    message_count = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = "Customer Channel"
        verbose_name_plural = "Customer Channels"
        unique_together = ['customer', 'number']
    
    def __str__(self):
        return f"{self.customer.wa_id} via {self.number.display_name}"


class WabisMessage(BaseModel):
    """
    Store incoming/outgoing WhatsApp messages.
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
    
    customer = models.ForeignKey(
        WabisCustomer,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    number = models.ForeignKey(
        WabisNumber,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    
    # Message identifiers
    message_id = models.CharField(
        max_length=128,
        unique=True,
        db_index=True,
        help_text="Wabis/Meta message ID"
    )
    
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES, default='inbound')
    msg_type = models.CharField(max_length=32, choices=MSG_TYPE_CHOICES, default='unknown')
    
    # Content
    body = models.TextField(blank=True, null=True)
    media_id = models.CharField(max_length=200, blank=True, null=True)
    media_url = models.URLField(blank=True, null=True)
    media_mime_type = models.CharField(max_length=100, blank=True, null=True)
    
    # Timestamps
    timestamp_utc = models.DateTimeField()
    
    # Raw payload for debugging
    raw_payload = models.JSONField(default=dict, blank=True)
    
    class Meta:
        verbose_name = "Wabis Message"
        verbose_name_plural = "Wabis Messages"
        ordering = ['-timestamp_utc']
    
    def __str__(self):
        return f"{self.direction}: {self.customer.wa_id} - {self.msg_type}"


class WabisWebhookLog(BaseModel):
    """
    Log all webhook payloads for debugging and mapping.
    Retention: Keep for 30 days, then archive/delete.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Request info
    phone_number_id = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    event_type = models.CharField(max_length=50, blank=True, null=True)
    
    # Raw payload - CRITICAL for mapping unknown fields
    payload = models.JSONField(default=dict)
    headers = models.JSONField(default=dict, blank=True)
    
    # Processing status
    processed = models.BooleanField(default=False)
    processing_time_ms = models.IntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    
    # Results
    messages_processed = models.IntegerField(default=0)
    customers_created = models.IntegerField(default=0)
    customers_updated = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = "Webhook Log"
        verbose_name_plural = "Webhook Logs"
        ordering = ['-created']
        indexes = [
            models.Index(fields=['phone_number_id', '-created']),
            models.Index(fields=['processed', '-created']),
        ]
    
    def __str__(self):
        return f"Webhook {self.created}: {self.event_type or 'unknown'}"


# =============================================================================
# METRICS & REPORTING
# =============================================================================

class DailyLeadMetrics(BaseModel):
    """
    Aggregated daily metrics per WhatsApp number and source.
    Generated by Celery task at 2:00 AM IST.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Date
    date = models.DateField(db_index=True)
    
    # Number (null = aggregate for all numbers)
    number = models.ForeignKey(
        WabisNumber,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='daily_metrics'
    )
    
    # Source breakdown
    source_type = models.CharField(
        max_length=20,
        choices=WabisCustomer.SOURCE_TYPE_CHOICES,
        default='unknown'
    )
    
    # Lead counts
    total_leads = models.IntegerField(default=0)
    new_leads = models.IntegerField(default=0)
    
    # Conversion counts
    conversions = models.IntegerField(default=0)
    conversion_value = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    conversion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Status breakdown
    pending_leads = models.IntegerField(default=0)
    won_leads = models.IntegerField(default=0)
    lost_leads = models.IntegerField(default=0)
    
    # Messages
    total_messages = models.IntegerField(default=0)
    
    # ROAS placeholders (to be populated when ad spend is integrated)
    ad_spend = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    roas = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    class Meta:
        verbose_name = "Daily Lead Metrics"
        verbose_name_plural = "Daily Lead Metrics"
        unique_together = ['date', 'number', 'source_type']
        ordering = ['-date']
    
    def __str__(self):
        number_name = self.number.display_name if self.number else 'All Numbers'
        return f"{self.date} - {number_name} - {self.source_type}"
    
    def calculate_roas(self):
        if self.ad_spend > 0:
            self.roas = self.conversion_value / self.ad_spend
        return self.roas


class CampaignMetrics(BaseModel):
    """
    Campaign-level metrics for ROAS tracking.
    Placeholder for future Meta Ads integration.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    date = models.DateField(db_index=True)
    campaign_id = models.CharField(max_length=100, db_index=True)
    campaign_name = models.CharField(max_length=500, blank=True, null=True)
    
    # Spend (to be populated from Meta Ads API)
    spend = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='INR')
    
    # Performance metrics
    impressions = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)
    reach = models.IntegerField(default=0)
    
    # Lead tracking
    leads_generated = models.IntegerField(default=0)
    conversions = models.IntegerField(default=0)
    conversion_value = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    
    # ROAS
    roas = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    class Meta:
        verbose_name = "Campaign Metrics"
        verbose_name_plural = "Campaign Metrics"
        unique_together = ['date', 'campaign_id']
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.date} - {self.campaign_name or self.campaign_id}"
