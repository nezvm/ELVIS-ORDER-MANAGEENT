import uuid
from django.db import models
from django.urls import reverse_lazy
from core.base import BaseModel


class DynamicChannel(BaseModel):
    """Dynamic channel configuration that replaces hardcoded channel choices."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, help_text="Display name for the channel")
    code = models.CharField(max_length=50, unique=True, help_text="Internal code (e.g., 'whatsapp', 'shopify')")
    prefix = models.CharField(max_length=20, unique=True, help_text="Order number prefix")
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=50, default="fa-shopping-cart", help_text="Font Awesome icon class")
    color = models.CharField(max_length=20, default="#6c757d", help_text="Hex color code")
    is_cod_channel = models.BooleanField(default=False, help_text="Is this a COD channel?")
    requires_utr = models.BooleanField(default=False, help_text="Does this channel require UTR?")
    requires_payment_capture = models.BooleanField(default=False, help_text="Does this channel auto-capture payments?")
    sort_order = models.IntegerField(default=0, help_text="Display order in menus")
    
    class Meta:
        verbose_name = "Dynamic Channel"
        verbose_name_plural = "Dynamic Channels"
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return self.name
    
    @staticmethod
    def get_list_url():
        return reverse_lazy("channels_config:channel_list")
    
    def get_absolute_url(self):
        return reverse_lazy("channels_config:channel_detail", kwargs={"pk": str(self.pk)})
    
    def get_update_url(self):
        return reverse_lazy("channels_config:channel_update", kwargs={"pk": str(self.pk)})
    
    def get_delete_url(self):
        return reverse_lazy("channels_config:channel_delete", kwargs={"pk": str(self.pk)})


class ChannelFormField(BaseModel):
    """Configurable form fields for each channel."""
    FIELD_TYPES = [
        ('text', 'Text Input'),
        ('number', 'Number Input'),
        ('textarea', 'Text Area'),
        ('select', 'Dropdown Select'),
        ('checkbox', 'Checkbox'),
        ('date', 'Date Picker'),
        ('datetime', 'DateTime Picker'),
        ('file', 'File Upload'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    channel = models.ForeignKey(DynamicChannel, on_delete=models.CASCADE, related_name='form_fields')
    field_name = models.CharField(max_length=100, help_text="Internal field name (snake_case)")
    label = models.CharField(max_length=100, help_text="Display label")
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES, default='text')
    is_required = models.BooleanField(default=False)
    is_visible = models.BooleanField(default=True)
    placeholder = models.CharField(max_length=200, blank=True, null=True)
    help_text = models.CharField(max_length=500, blank=True, null=True)
    default_value = models.CharField(max_length=500, blank=True, null=True)
    validation_regex = models.CharField(max_length=500, blank=True, null=True, help_text="Regex pattern for validation")
    choices = models.JSONField(default=list, blank=True, help_text="Options for select fields: [{\"value\": \"a\", \"label\": \"A\"}]")
    sort_order = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = "Channel Form Field"
        verbose_name_plural = "Channel Form Fields"
        ordering = ['channel', 'sort_order']
        unique_together = ['channel', 'field_name']
    
    def __str__(self):
        return f"{self.channel.name} - {self.label}"


class UTRRecord(BaseModel):
    """Track UTR submissions with audit trail."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utr = models.CharField(max_length=50, unique=True, db_index=True)
    order = models.OneToOneField('master.Order', on_delete=models.CASCADE, related_name='utr_record')
    captured_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='captured_utrs')
    captured_at = models.DateTimeField(auto_now_add=True)
    verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_utrs')
    verified_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = "UTR Record"
        verbose_name_plural = "UTR Records"
        ordering = ['-captured_at']
    
    def __str__(self):
        return f"UTR: {self.utr}"
