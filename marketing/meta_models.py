"""
Meta CAPI Integration Models

Models for Meta Conversions API integration, ad insights sync,
and probabilistic attribution engine.
"""

import uuid
import hashlib
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from master.models import BaseModel


class MetaIntegrationConfig(BaseModel):
    """
    Singleton configuration for Meta API integration.
    Stores Ad Account, Pixel/Dataset, and access credentials.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Meta Business Assets
    business_id = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        help_text="Meta Business ID (optional)"
    )
    ad_account_id = models.CharField(
        max_length=50,
        help_text="Meta Ad Account ID (format: act_XXXXX)"
    )
    pixel_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Meta Pixel ID for CAPI (use this OR dataset_id)"
    )
    dataset_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Meta Dataset ID for CAPI (use this OR pixel_id)"
    )
    
    # Authentication
    access_token = models.TextField(
        help_text="Meta Marketing API Access Token (stored encrypted)"
    )
    app_secret = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="App Secret for CAPI signature verification (optional)"
    )
    
    # Configuration
    is_active = models.BooleanField(default=True)
    send_lead_events = models.BooleanField(
        default=True,
        help_text="Send Lead events to CAPI on lead creation"
    )
    send_purchase_events = models.BooleanField(
        default=True,
        help_text="Send Purchase events to CAPI when lead becomes Won"
    )
    
    # Attribution Settings
    attribution_threshold = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.20,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text="Threshold for probabilistic ads attribution (0.0-1.0, default 0.20)"
    )
    attribution_window_hours = models.IntegerField(
        default=24,
        help_text="Attribution window in hours for bucketing"
    )
    
    # Sync Status
    last_insights_sync_at = models.DateTimeField(null=True, blank=True)
    last_insights_sync_status = models.CharField(max_length=20, default='never')
    last_insights_sync_message = models.TextField(blank=True, null=True)
    
    last_capi_send_at = models.DateTimeField(null=True, blank=True)
    capi_success_count = models.IntegerField(default=0)
    capi_failure_count = models.IntegerField(default=0)
    
    last_attribution_run_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Meta Integration Config"
        verbose_name_plural = "Meta Integration Config"
    
    def __str__(self):
        return f"Meta Config: {self.ad_account_id}"
    
    @property
    def capi_endpoint_id(self):
        """Returns the CAPI endpoint ID (pixel_id or dataset_id)."""
        return self.pixel_id or self.dataset_id
    
    @property
    def capi_success_rate(self):
        """Returns CAPI success rate percentage."""
        total = self.capi_success_count + self.capi_failure_count
        if total == 0:
            return 100.0
        return round(self.capi_success_count / total * 100, 1)
    
    @classmethod
    def get_config(cls):
        """Get the active Meta integration config (singleton pattern)."""
        return cls.objects.filter(is_active=True).first()
    
    def save(self, *args, **kwargs):
        # Ensure only one active config
        if self.is_active:
            MetaIntegrationConfig.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)


class MetaDailyInsights(BaseModel):
    """
    Daily ad insights pulled from Meta Marketing API.
    Stores spend, impressions, clicks, and messaging metrics.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Date bucket
    insight_date = models.DateField(db_index=True)
    
    # Campaign hierarchy
    campaign_id = models.CharField(max_length=50, db_index=True)
    campaign_name = models.CharField(max_length=255)
    campaign_objective = models.CharField(max_length=100, blank=True, null=True)
    
    adset_id = models.CharField(max_length=50, blank=True, null=True)
    adset_name = models.CharField(max_length=255, blank=True, null=True)
    
    ad_id = models.CharField(max_length=50, blank=True, null=True)
    ad_name = models.CharField(max_length=255, blank=True, null=True)
    
    # Core Metrics
    spend = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    impressions = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)
    reach = models.IntegerField(default=0)
    
    # Messaging/CTWA Metrics (store what Meta provides)
    messaging_conversations_started = models.IntegerField(
        default=0,
        help_text="Messaging conversations started (CTWA metric)"
    )
    messaging_first_reply = models.IntegerField(
        default=0,
        help_text="First replies to messaging"
    )
    onsite_conversion_messaging_first_reply = models.IntegerField(
        default=0,
        help_text="On-site conversion: messaging first reply"
    )
    
    # Meta-reported conversions (for comparison)
    meta_leads = models.IntegerField(default=0, help_text="Meta-reported lead events")
    meta_purchases = models.IntegerField(default=0, help_text="Meta-reported purchase events")
    meta_purchase_value = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    
    # ERP-side attribution (computed)
    erp_attributed_leads = models.IntegerField(default=0)
    erp_attributed_revenue = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    
    # Raw data
    raw_json = models.JSONField(default=dict, blank=True)
    
    class Meta:
        verbose_name = "Meta Daily Insights"
        verbose_name_plural = "Meta Daily Insights"
        unique_together = ['insight_date', 'campaign_id', 'adset_id', 'ad_id']
        ordering = ['-insight_date', 'campaign_name']
        indexes = [
            models.Index(fields=['insight_date']),
            models.Index(fields=['campaign_id']),
            models.Index(fields=['insight_date', 'campaign_id']),
        ]
    
    def __str__(self):
        return f"{self.insight_date} - {self.campaign_name}: ${self.spend}"


class CapiEventLog(BaseModel):
    """
    Log of CAPI events sent to Meta.
    Tracks Lead and Purchase events with retry status.
    """
    EVENT_TYPES = [
        ('Lead', 'Lead'),
        ('Purchase', 'Purchase'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped'),
    ]
    
    SOURCE_CHOICES = [
        ('whatsapp', 'WhatsApp'),
        ('shopify', 'Shopify'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Event identification
    event_name = models.CharField(max_length=20, choices=EVENT_TYPES, db_index=True)
    event_id = models.CharField(
        max_length=100, 
        unique=True,
        help_text="Idempotent event ID: sha256('event_type:' + entity_id)"
    )
    event_time = models.DateTimeField()
    
    # Linked entities
    lead = models.ForeignKey(
        'marketing.Lead',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='capi_events'
    )
    order = models.ForeignKey(
        'integrations.ShopifyOrder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='capi_events'
    )
    
    # Event data
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, db_index=True)
    value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='INR')
    
    # User data hashes (for audit, not the actual data)
    phone_hash_used = models.BooleanField(default=False)
    email_hash_used = models.BooleanField(default=False)
    
    # Custom data sent
    custom_data_json = models.JSONField(default=dict, blank=True)
    
    # Status and retries
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    retries = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    last_error = models.TextField(blank=True, null=True)
    
    # Response (masked sensitive data)
    response_json = models.JSONField(default=dict, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "CAPI Event Log"
        verbose_name_plural = "CAPI Event Logs"
        ordering = ['-created']
        indexes = [
            models.Index(fields=['event_name', 'status']),
            models.Index(fields=['created']),
            models.Index(fields=['source', 'created']),
        ]
    
    def __str__(self):
        return f"{self.event_name} - {self.event_id[:20]}... ({self.status})"
    
    @classmethod
    def generate_event_id(cls, event_type, entity_id):
        """Generate idempotent event ID."""
        raw = f"{event_type}:{entity_id}"
        return hashlib.sha256(raw.encode()).hexdigest()
    
    def mark_sent(self, response=None):
        """Mark event as successfully sent."""
        self.status = 'sent'
        self.sent_at = timezone.now()
        if response:
            self.response_json = response
        self.save()
    
    def mark_failed(self, error):
        """Mark event as failed with error."""
        self.retries += 1
        self.last_error = str(error)
        if self.retries >= self.max_retries:
            self.status = 'failed'
        self.save()


class MarketingDailyRollup(BaseModel):
    """
    Daily aggregated marketing metrics for ROAS dashboard.
    Pre-computed for performance.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    rollup_date = models.DateField(unique=True, db_index=True)
    
    # Spend (from Meta)
    spend_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    
    # Lead counts
    leads_total = models.IntegerField(default=0)
    wa_leads = models.IntegerField(default=0)
    shopify_leads = models.IntegerField(default=0)
    other_leads = models.IntegerField(default=0)
    
    # Attribution breakdown
    estimated_ads_leads = models.IntegerField(default=0)
    organic_leads = models.IntegerField(default=0)
    unknown_leads = models.IntegerField(default=0)
    
    # Conversion metrics
    won_count = models.IntegerField(default=0)
    lost_count = models.IntegerField(default=0)
    pending_count = models.IntegerField(default=0)
    
    # Revenue
    revenue_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    revenue_estimated_ads = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    revenue_organic = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    
    # ROAS calculations
    estimated_roas = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        help_text="Revenue from estimated ads / Spend"
    )
    cost_per_lead = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Spend / Estimated Ads Leads"
    )
    cost_per_purchase = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Spend / Won leads from ads"
    )
    
    # Meta-side metrics (for comparison)
    meta_conversations_started = models.IntegerField(default=0)
    meta_reported_leads = models.IntegerField(default=0)
    meta_reported_purchases = models.IntegerField(default=0)
    meta_reported_revenue = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    
    # Attribution stats
    avg_attribution_confidence = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    ads_share_ratio = models.DecimalField(
        max_digits=5, 
        decimal_places=4, 
        default=0,
        help_text="Estimated ads share of WA leads (0-1)"
    )
    
    computed_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Marketing Daily Rollup"
        verbose_name_plural = "Marketing Daily Rollups"
        ordering = ['-rollup_date']
        indexes = [
            models.Index(fields=['rollup_date']),
        ]
    
    def __str__(self):
        return f"Marketing Rollup - {self.rollup_date}"


# Attribution choices for Lead model
ATTRIBUTION_MODEL_CHOICES = [
    ('unknown', 'Unknown'),
    ('organic', 'Organic'),
    ('probabilistic_ads', 'Probabilistic Ads'),
    ('manual_ads', 'Manual - Ads'),
    ('manual_organic', 'Manual - Organic'),
]
