from django.contrib import admin
from django.utils.html import format_html
from core.base import BaseAdmin
from .models import (
    Carrier, CarrierCredential, CarrierZone, CarrierRate, 
    ShippingRule, Shipment, ShipmentTracking, NDRRecord,
    CarrierAPILog, PincodeServiceability, ShippingSettings
)


class CarrierCredentialInline(admin.TabularInline):
    model = CarrierCredential
    extra = 0
    fields = ['environment', 'api_key', 'client_id', 'base_url', 'is_active']
    readonly_fields = ['created', 'updated']


class CarrierZoneInline(admin.TabularInline):
    model = CarrierZone
    extra = 0


class CarrierRateInline(admin.TabularInline):
    model = CarrierRate
    extra = 0


@admin.register(Carrier)
class CarrierAdmin(BaseAdmin):
    list_display = ['name', 'code', 'status', 'supports_cod', 'priority', 'avg_delivery_days', 'success_rate', 'credential_status']
    list_filter = ['status', 'supports_cod', 'supports_reverse']
    search_fields = ['name', 'code']
    inlines = [CarrierCredentialInline, CarrierZoneInline, CarrierRateInline]
    
    def credential_status(self, obj):
        creds = obj.carriercredential_set.filter(is_active=True)
        if creds.exists():
            return format_html('<span style="color:green;">✓ Configured</span>')
        return format_html('<span style="color:red;">✗ Not Configured</span>')
    credential_status.short_description = "Credentials"


@admin.register(CarrierCredential)
class CarrierCredentialAdmin(BaseAdmin):
    list_display = ['carrier', 'environment', 'is_active', 'api_key_masked', 'base_url', 'created']
    list_filter = ['carrier', 'environment', 'is_active']
    search_fields = ['carrier__name', 'carrier__code']
    readonly_fields = ['created', 'updated']
    fieldsets = (
        ('Carrier Info', {
            'fields': ('carrier', 'environment', 'is_active')
        }),
        ('API Credentials', {
            'fields': ('api_key', 'api_secret', 'client_id', 'client_secret'),
            'description': 'Store credentials securely. These will be used for API calls.'
        }),
        ('Endpoints', {
            'fields': ('base_url', 'webhook_url', 'webhook_secret')
        }),
        ('Additional Config', {
            'fields': ('additional_config',),
            'description': 'JSON format for carrier-specific settings (pickup_name, login_id, etc.)'
        }),
        ('Timestamps', {
            'fields': ('created', 'updated'),
            'classes': ('collapse',)
        }),
    )
    
    def api_key_masked(self, obj):
        if obj.api_key:
            return f"{obj.api_key[:8]}...{obj.api_key[-4:]}" if len(obj.api_key) > 12 else "***"
        return "-"
    api_key_masked.short_description = "API Key"


@admin.register(ShippingRule)
class ShippingRuleAdmin(BaseAdmin):
    list_display = ['name', 'rule_type', 'priority', 'assigned_carrier', 'fallback_carrier', 'is_enabled', 'is_active']
    list_filter = ['rule_type', 'assigned_carrier', 'is_enabled', 'is_active']
    search_fields = ['name', 'description']
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'description', 'rule_type', 'priority')
        }),
        ('Carrier Assignment', {
            'fields': ('assigned_carrier', 'fallback_carrier')
        }),
        ('Conditions (JSON)', {
            'fields': ('conditions',),
            'description': 'Example: {"states": ["Delhi", "Maharashtra"], "min_amount": 500, "payment_type": "cod"}'
        }),
        ('Status', {
            'fields': ('is_enabled', 'is_active')
        }),
    )


class ShipmentTrackingInline(admin.TabularInline):
    model = ShipmentTracking
    extra = 0
    readonly_fields = ['event_time', 'status', 'location', 'description']


class NDRRecordInline(admin.TabularInline):
    model = NDRRecord
    extra = 0


@admin.register(Shipment)
class ShipmentAdmin(BaseAdmin):
    list_display = ['tracking_number', 'order', 'carrier', 'status', 'is_cod', 'shipping_cost', 'created']
    list_filter = ['status', 'carrier', 'is_cod', 'assignment_method']
    search_fields = ['tracking_number', 'awb_number', 'order__order_no']
    inlines = [ShipmentTrackingInline, NDRRecordInline]
    readonly_fields = ['carrier_response', 'label_url', 'invoice_url']


@admin.register(NDRRecord)
class NDRRecordAdmin(BaseAdmin):
    list_display = ['shipment', 'ndr_date', 'reason', 'attempt_number', 'action', 'is_resolved']
    list_filter = ['reason', 'action', 'is_resolved']
    search_fields = ['shipment__tracking_number']


@admin.register(CarrierAPILog)
class CarrierAPILogAdmin(admin.ModelAdmin):
    list_display = ['carrier', 'log_type', 'is_success', 'response_status', 'response_time_ms', 'created']
    list_filter = ['carrier', 'log_type', 'is_success', 'request_method']
    search_fields = ['reference_id', 'request_url']
    readonly_fields = ['carrier', 'log_type', 'request_url', 'request_method', 'request_headers',
                       'request_body', 'response_status', 'response_body', 'response_time_ms',
                       'is_success', 'error_message', 'reference_id', 'created']


@admin.register(PincodeServiceability)
class PincodeServiceabilityAdmin(admin.ModelAdmin):
    list_display = ['pincode', 'carrier', 'is_prepaid_available', 'is_cod_available', 'is_reverse_available']
    list_filter = ['carrier', 'is_prepaid_available', 'is_cod_available']
    search_fields = ['pincode']


@admin.register(ShippingSettings)
class ShippingSettingsAdmin(admin.ModelAdmin):
    list_display = ['id', 'primary_carrier', 'auto_assign_enabled', 'auto_book_enabled', 'updated']
    
    def has_add_permission(self, request):
        # Only allow one settings object
        if ShippingSettings.objects.exists():
            return False
        return super().has_add_permission(request)
