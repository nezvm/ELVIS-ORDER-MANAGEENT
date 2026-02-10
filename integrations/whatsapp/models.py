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
    attribution_source = models.CharField(
        max_length=30, 
        choices=ATTRIBUTION_SOURCE_CHOICES, 
        default='unknown',
        db_index=True,
        help_text="How the customer discovered us"
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
        help_text="Click-to-WhatsApp Click ID (for conversion tracking)"
    )
    
    # For Meta Conversions API (CAPI) tracking
    meta_fbclid = models.CharField(
        max_length=200, 
        blank=True, 
        null=True,
        help_text="Facebook Click ID"
    )
    conversion_sent_to_meta = models.BooleanField(
        default=False,
        help_text="Whether conversion event was sent to Meta CAPI"
    )
    conversion_sent_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When conversion was sent to Meta"
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
