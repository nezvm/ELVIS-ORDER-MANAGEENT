import uuid
from django.db import models
from django.urls import reverse_lazy
from django.db.models import Sum, Count, Avg, F, Q
from core.base import BaseModel
from decimal import Decimal


class CustomerProfile(BaseModel):
    """Extended customer profile with computed metrics."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.OneToOneField('master.Customer', on_delete=models.CASCADE, related_name='profile')
    
    # Order Metrics
    lifetime_order_count = models.IntegerField(default=0)
    lifetime_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    average_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    first_order_date = models.DateField(null=True, blank=True)
    last_order_date = models.DateField(null=True, blank=True)
    days_since_last_order = models.IntegerField(default=0)
    
    # Channel Metrics
    primary_channel = models.CharField(max_length=100, blank=True, null=True)
    channels_used = models.JSONField(default=list, help_text="List of channels customer has ordered from")
    channel_order_counts = models.JSONField(default=dict, help_text="Order count per channel")
    
    # Geographic Data
    tier_city = models.CharField(max_length=20, blank=True, null=True, choices=[
        ('tier_1', 'Tier 1'),
        ('tier_2', 'Tier 2'),
        ('tier_3', 'Tier 3'),
        ('tier_4', 'Tier 4/Rural'),
    ])
    logistics_zone = models.CharField(max_length=50, blank=True, null=True)
    
    # Behavioral Segments
    order_behavior_segment = models.CharField(max_length=50, blank=True, null=True, choices=[
        ('non_ordered', 'Non-Ordered'),
        ('one_time', 'One-Time Buyer'),
        ('new_repeat', 'New Repeat (2 orders)'),
        ('repeat', 'Repeat Buyer (3-5)'),
        ('loyal', 'Loyal (6-10)'),
        ('super_loyal', 'Super Loyal (11+)'),
    ])
    
    lifecycle_stage = models.CharField(max_length=50, blank=True, null=True, choices=[
        ('new', 'New'),
        ('active', 'Active'),
        ('engaged', 'Engaged'),
        ('at_risk', 'At Risk'),
        ('dropped', 'Dropped'),
        ('churned', 'Churned'),
        ('reactivated', 'Reactivated'),
    ])
    
    channel_loyalty = models.CharField(max_length=50, blank=True, null=True, choices=[
        ('whatsapp_loyal', 'WhatsApp Loyal'),
        ('cod_preferred', 'COD Preferred'),
        ('prepaid_preferred', 'Prepaid Preferred'),
        ('multi_channel', 'Multi-Channel'),
        ('web_only', 'Web Only'),
    ])
    
    value_tier = models.CharField(max_length=30, blank=True, null=True, choices=[
        ('high', 'High Value'),
        ('medium', 'Medium Value'),
        ('low', 'Low Value'),
    ])
    
    # Loyalty Program
    loyalty_tier = models.CharField(max_length=30, blank=True, null=True, choices=[
        ('bronze', 'Bronze'),
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
    ])
    loyalty_points = models.IntegerField(default=0)
    
    # Last computed
    last_computed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Customer Profile"
        verbose_name_plural = "Customer Profiles"
        ordering = ['-lifetime_revenue']
    
    def __str__(self):
        return f"Profile: {self.customer.customer_name}"
    
    @staticmethod
    def get_list_url():
        return reverse_lazy("segmentation:profile_list")
    
    def get_absolute_url(self):
        return reverse_lazy("segmentation:profile_detail", kwargs={"pk": str(self.pk)})


class CustomerSegment(BaseModel):
    """Predefined customer segments."""
    SEGMENT_TYPES = [
        ('order_behavior', 'Order Behavior'),
        ('lifecycle', 'Lifecycle Stage'),
        ('channel', 'Channel Loyalty'),
        ('value', 'Value Tier'),
        ('geographic', 'Geographic'),
        ('custom', 'Custom'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    segment_type = models.CharField(max_length=30, choices=SEGMENT_TYPES)
    description = models.TextField(blank=True, null=True)
    color = models.CharField(max_length=20, default='#6c757d')
    icon = models.CharField(max_length=50, default='fa-users')
    
    # Filter criteria (JSON)
    filter_criteria = models.JSONField(default=dict, help_text="Filter criteria for dynamic segmentation")
    
    # Stats (updated periodically)
    customer_count = models.IntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    avg_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    last_computed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Customer Segment"
        verbose_name_plural = "Customer Segments"
        ordering = ['segment_type', 'name']
    
    def __str__(self):
        return self.name
    
    @staticmethod
    def get_list_url():
        return reverse_lazy("segmentation:segment_list")
    
    def get_absolute_url(self):
        return reverse_lazy("segmentation:segment_detail", kwargs={"pk": str(self.pk)})
    
    def get_update_url(self):
        return reverse_lazy("segmentation:segment_update", kwargs={"pk": str(self.pk)})
    
    def get_delete_url(self):
        return reverse_lazy("segmentation:segment_delete", kwargs={"pk": str(self.pk)})


class CustomerSegmentMembership(BaseModel):
    """Many-to-many relationship between customers and segments."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name='segment_memberships')
    segment = models.ForeignKey(CustomerSegment, on_delete=models.CASCADE, related_name='members')
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Segment Membership"
        verbose_name_plural = "Segment Memberships"
        unique_together = ['profile', 'segment']
    
    def __str__(self):
        return f"{self.profile.customer.customer_name} in {self.segment.name}"


class SegmentExport(BaseModel):
    """Track segment exports for marketing campaigns."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    segment = models.ForeignKey(CustomerSegment, on_delete=models.CASCADE, related_name='exports')
    export_type = models.CharField(max_length=30, choices=[
        ('csv', 'CSV'),
        ('excel', 'Excel'),
        ('api', 'API/Webhook'),
    ])
    customer_count = models.IntegerField(default=0)
    exported_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    file_url = models.URLField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Segment Export"
        verbose_name_plural = "Segment Exports"
        ordering = ['-created']
    
    def __str__(self):
        return f"Export: {self.segment.name} ({self.created.date()})"


class CohortAnalysis(BaseModel):
    """Cohort analysis data."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cohort_month = models.DateField(help_text="First day of the cohort month")
    total_customers = models.IntegerField(default=0)
    
    # Retention by month (JSON: {"month_1": count, "month_2": count, ...})
    retention_data = models.JSONField(default=dict)
    
    # Revenue by month
    revenue_data = models.JSONField(default=dict)
    
    # Average order value by month
    aov_data = models.JSONField(default=dict)
    
    class Meta:
        verbose_name = "Cohort Analysis"
        verbose_name_plural = "Cohort Analyses"
        ordering = ['-cohort_month']
        unique_together = ['cohort_month']
    
    def __str__(self):
        return f"Cohort: {self.cohort_month.strftime('%B %Y')}"
