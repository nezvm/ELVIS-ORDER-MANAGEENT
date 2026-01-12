import uuid
from django.db import models
from django.urls import reverse_lazy
from core.base import BaseModel
from decimal import Decimal


class Carrier(BaseModel):
    """Shipping carriers like Delhivery, BlueDart, etc."""
    CARRIER_STATUS = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('testing', 'Testing'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=50, unique=True, help_text="Internal code (e.g., 'delhivery', 'bluedart')")
    logo = models.ImageField(upload_to='carriers/', null=True, blank=True)
    website = models.URLField(blank=True, null=True)
    tracking_url_template = models.CharField(max_length=500, blank=True, null=True,
                                             help_text="URL template with {tracking_number} placeholder")
    supports_cod = models.BooleanField(default=True)
    supports_prepaid = models.BooleanField(default=True)
    supports_reverse = models.BooleanField(default=False, help_text="Supports reverse logistics")
    status = models.CharField(max_length=20, choices=CARRIER_STATUS, default='active')
    priority = models.IntegerField(default=0, help_text="Higher priority = preferred carrier")
    
    # Performance metrics (updated by background jobs)
    avg_delivery_days = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    sla_adherence_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Percentage")
    success_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Delivery success %")
    
    class Meta:
        verbose_name = "Carrier"
        verbose_name_plural = "Carriers"
        ordering = ['-priority', 'name']
    
    def __str__(self):
        return self.name
    
    @staticmethod
    def get_list_url():
        return reverse_lazy("logistics:carrier_list")
    
    def get_absolute_url(self):
        return reverse_lazy("logistics:carrier_detail", kwargs={"pk": str(self.pk)})
    
    def get_update_url(self):
        return reverse_lazy("logistics:carrier_update", kwargs={"pk": str(self.pk)})
    
    def get_delete_url(self):
        return reverse_lazy("logistics:carrier_delete", kwargs={"pk": str(self.pk)})
    
    def get_tracking_url(self, tracking_number):
        if self.tracking_url_template:
            return self.tracking_url_template.replace('{tracking_number}', tracking_number)
        return None


class CarrierCredential(BaseModel):
    """API credentials for carrier integrations."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    carrier = models.ForeignKey(Carrier, on_delete=models.CASCADE, related_name='credentials')
    environment = models.CharField(max_length=20, choices=[('sandbox', 'Sandbox'), ('production', 'Production')], default='sandbox')
    api_key = models.CharField(max_length=500, blank=True, null=True)
    api_secret = models.CharField(max_length=500, blank=True, null=True)
    client_id = models.CharField(max_length=500, blank=True, null=True)
    client_secret = models.CharField(max_length=500, blank=True, null=True)
    access_token = models.TextField(blank=True, null=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    base_url = models.URLField(blank=True, null=True)
    webhook_secret = models.CharField(max_length=500, blank=True, null=True)
    additional_config = models.JSONField(default=dict, blank=True, help_text="Additional carrier-specific configuration")
    
    class Meta:
        verbose_name = "Carrier Credential"
        verbose_name_plural = "Carrier Credentials"
        unique_together = ['carrier', 'environment']
    
    def __str__(self):
        return f"{self.carrier.name} - {self.environment}"


class CarrierZone(BaseModel):
    """Geographic zones served by carriers."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    carrier = models.ForeignKey(Carrier, on_delete=models.CASCADE, related_name='zones')
    zone_name = models.CharField(max_length=100)
    zone_code = models.CharField(max_length=50)
    states = models.JSONField(default=list, help_text="List of state codes covered")
    pincodes = models.JSONField(default=list, help_text="List of pincodes or pincode ranges")
    
    class Meta:
        verbose_name = "Carrier Zone"
        verbose_name_plural = "Carrier Zones"
        unique_together = ['carrier', 'zone_code']
    
    def __str__(self):
        return f"{self.carrier.name} - {self.zone_name}"


class CarrierRate(BaseModel):
    """Shipping rates per carrier and zone."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    carrier = models.ForeignKey(Carrier, on_delete=models.CASCADE, related_name='rates')
    zone = models.ForeignKey(CarrierZone, on_delete=models.CASCADE, null=True, blank=True, related_name='rates')
    min_weight = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Minimum weight in kg")
    max_weight = models.DecimalField(max_digits=10, decimal_places=2, default=999, help_text="Maximum weight in kg")
    base_rate = models.DecimalField(max_digits=10, decimal_places=2, help_text="Base shipping rate")
    per_kg_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Rate per additional kg")
    cod_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fuel_surcharge_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_cod = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Carrier Rate"
        verbose_name_plural = "Carrier Rates"
    
    def __str__(self):
        zone_name = self.zone.zone_name if self.zone else "All Zones"
        return f"{self.carrier.name} - {zone_name} - {self.min_weight}-{self.max_weight}kg"
    
    def calculate_rate(self, weight, is_cod=False):
        """Calculate shipping rate for given weight."""
        rate = self.base_rate
        if weight > self.min_weight:
            additional_weight = weight - self.min_weight
            rate += additional_weight * self.per_kg_rate
        
        # Add fuel surcharge
        rate += rate * (self.fuel_surcharge_percent / 100)
        
        # Add COD charge if applicable
        if is_cod:
            rate += self.cod_charge
        
        return Decimal(str(round(rate, 2)))


class ShippingRule(BaseModel):
    """Rule-based carrier allocation rules."""
    RULE_TYPES = [
        ('zone', 'By Zone/State'),
        ('weight', 'By Weight'),
        ('price', 'By Order Value'),
        ('cod', 'By COD Availability'),
        ('customer_tier', 'By Customer Tier'),
        ('channel', 'By Sales Channel'),
        ('product', 'By Product Category'),
    ]
    
    CONDITION_OPERATORS = [
        ('equals', 'Equals'),
        ('not_equals', 'Not Equals'),
        ('greater_than', 'Greater Than'),
        ('less_than', 'Less Than'),
        ('in_list', 'In List'),
        ('not_in_list', 'Not In List'),
        ('contains', 'Contains'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    rule_type = models.CharField(max_length=50, choices=RULE_TYPES)
    priority = models.IntegerField(default=0, help_text="Higher priority rules are evaluated first")
    
    # Condition
    condition_field = models.CharField(max_length=100, help_text="Field to evaluate (e.g., 'state', 'weight', 'total_amount')")
    condition_operator = models.CharField(max_length=50, choices=CONDITION_OPERATORS, default='equals')
    condition_value = models.JSONField(help_text="Value(s) to compare against")
    
    # Action
    assigned_carrier = models.ForeignKey(Carrier, on_delete=models.CASCADE, related_name='allocation_rules')
    fallback_carrier = models.ForeignKey(Carrier, on_delete=models.SET_NULL, null=True, blank=True, 
                                          related_name='fallback_rules', help_text="Carrier to use if primary is unavailable")
    
    class Meta:
        verbose_name = "Shipping Rule"
        verbose_name_plural = "Shipping Rules"
        ordering = ['-priority']
    
    def __str__(self):
        return f"{self.name} (Priority: {self.priority})"
    
    @staticmethod
    def get_list_url():
        return reverse_lazy("logistics:rule_list")
    
    def get_absolute_url(self):
        return reverse_lazy("logistics:rule_detail", kwargs={"pk": str(self.pk)})
    
    def get_update_url(self):
        return reverse_lazy("logistics:rule_update", kwargs={"pk": str(self.pk)})
    
    def get_delete_url(self):
        return reverse_lazy("logistics:rule_delete", kwargs={"pk": str(self.pk)})
    
    def evaluate(self, order_data):
        """Evaluate if this rule matches the order data."""
        field_value = order_data.get(self.condition_field)
        
        if field_value is None:
            return False
        
        if self.condition_operator == 'equals':
            return str(field_value) == str(self.condition_value)
        elif self.condition_operator == 'not_equals':
            return str(field_value) != str(self.condition_value)
        elif self.condition_operator == 'greater_than':
            return float(field_value) > float(self.condition_value)
        elif self.condition_operator == 'less_than':
            return float(field_value) < float(self.condition_value)
        elif self.condition_operator == 'in_list':
            values = self.condition_value if isinstance(self.condition_value, list) else [self.condition_value]
            return str(field_value) in [str(v) for v in values]
        elif self.condition_operator == 'not_in_list':
            values = self.condition_value if isinstance(self.condition_value, list) else [self.condition_value]
            return str(field_value) not in [str(v) for v in values]
        elif self.condition_operator == 'contains':
            return str(self.condition_value).lower() in str(field_value).lower()
        
        return False


class Shipment(BaseModel):
    """Shipment records for orders."""
    SHIPMENT_STATUS = [
        ('pending', 'Pending'),
        ('manifested', 'Manifested'),
        ('picked_up', 'Picked Up'),
        ('in_transit', 'In Transit'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('rto_initiated', 'RTO Initiated'),
        ('rto_in_transit', 'RTO In Transit'),
        ('rto_delivered', 'RTO Delivered'),
        ('cancelled', 'Cancelled'),
        ('lost', 'Lost'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey('master.Order', on_delete=models.CASCADE, related_name='shipments')
    carrier = models.ForeignKey(Carrier, on_delete=models.PROTECT, related_name='shipments')
    tracking_number = models.CharField(max_length=100, unique=True, db_index=True)
    awb_number = models.CharField(max_length=100, blank=True, null=True, help_text="Air Waybill Number")
    status = models.CharField(max_length=30, choices=SHIPMENT_STATUS, default='pending')
    
    # Weight and dimensions
    weight = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Weight in kg")
    length = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Length in cm")
    width = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Width in cm")
    height = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Height in cm")
    volumetric_weight = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Shipping details
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cod_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_cod = models.BooleanField(default=False)
    
    # Dates
    manifest_date = models.DateTimeField(null=True, blank=True)
    pickup_date = models.DateTimeField(null=True, blank=True)
    expected_delivery_date = models.DateField(null=True, blank=True)
    actual_delivery_date = models.DateTimeField(null=True, blank=True)
    
    # Addresses
    pickup_address = models.JSONField(default=dict)
    delivery_address = models.JSONField(default=dict)
    
    # Carrier response data
    carrier_response = models.JSONField(default=dict, blank=True)
    label_url = models.URLField(blank=True, null=True)
    invoice_url = models.URLField(blank=True, null=True)
    
    # Assignment info
    assigned_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='assigned_shipments')
    assignment_method = models.CharField(max_length=50, choices=[
        ('manual', 'Manual'),
        ('rule_based', 'Rule Based'),
        ('performance_based', 'Performance Based'),
        ('bulk', 'Bulk Assignment'),
    ], default='manual')
    rule_used = models.ForeignKey(ShippingRule, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = "Shipment"
        verbose_name_plural = "Shipments"
        ordering = ['-created']
    
    def __str__(self):
        return f"{self.tracking_number} - {self.order.order_no}"
    
    @staticmethod
    def get_list_url():
        return reverse_lazy("logistics:shipment_list")
    
    def get_absolute_url(self):
        return reverse_lazy("logistics:shipment_detail", kwargs={"pk": str(self.pk)})
    
    def get_update_url(self):
        return reverse_lazy("logistics:shipment_update", kwargs={"pk": str(self.pk)})
    
    def get_tracking_url(self):
        return self.carrier.get_tracking_url(self.tracking_number)


class ShipmentTracking(BaseModel):
    """Tracking history for shipments."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name='tracking_events')
    status = models.CharField(max_length=100)
    status_code = models.CharField(max_length=50, blank=True, null=True)
    location = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    event_time = models.DateTimeField()
    carrier_scan_time = models.DateTimeField(null=True, blank=True)
    raw_data = models.JSONField(default=dict, blank=True)
    
    class Meta:
        verbose_name = "Shipment Tracking"
        verbose_name_plural = "Shipment Tracking Events"
        ordering = ['-event_time']
    
    def __str__(self):
        return f"{self.shipment.tracking_number} - {self.status}"


class NDRRecord(BaseModel):
    """Non-Delivery Reports for failed deliveries."""
    NDR_REASONS = [
        ('customer_unavailable', 'Customer Unavailable'),
        ('wrong_address', 'Wrong Address'),
        ('address_incomplete', 'Address Incomplete'),
        ('customer_refused', 'Customer Refused'),
        ('cod_not_ready', 'COD Not Ready'),
        ('customer_rescheduled', 'Customer Rescheduled'),
        ('area_not_serviceable', 'Area Not Serviceable'),
        ('other', 'Other'),
    ]
    
    NDR_ACTIONS = [
        ('reattempt', 'Reattempt Delivery'),
        ('rto', 'Return to Origin'),
        ('hold', 'Hold at Warehouse'),
        ('reschedule', 'Reschedule'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name='ndr_records')
    ndr_date = models.DateTimeField()
    reason = models.CharField(max_length=50, choices=NDR_REASONS)
    reason_description = models.TextField(blank=True, null=True)
    attempt_number = models.IntegerField(default=1)
    
    # Action taken
    action = models.CharField(max_length=30, choices=NDR_ACTIONS, null=True, blank=True)
    action_date = models.DateTimeField(null=True, blank=True)
    action_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='ndr_actions')
    action_notes = models.TextField(blank=True, null=True)
    
    # Customer contact
    customer_contacted = models.BooleanField(default=False)
    customer_response = models.TextField(blank=True, null=True)
    new_delivery_date = models.DateField(null=True, blank=True)
    
    # Resolution
    is_resolved = models.BooleanField(default=False)
    resolution_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "NDR Record"
        verbose_name_plural = "NDR Records"
        ordering = ['-ndr_date']
    
    def __str__(self):
        return f"NDR: {self.shipment.tracking_number} - {self.reason}"
    
    @staticmethod
    def get_list_url():
        return reverse_lazy("logistics:ndr_list")
    
    def get_absolute_url(self):
        return reverse_lazy("logistics:ndr_detail", kwargs={"pk": str(self.pk)})
