from django.contrib import admin
from core.base import BaseAdmin
from .models import (
    Carrier, CarrierCredential, CarrierZone, CarrierRate, 
    ShippingRule, Shipment, ShipmentTracking, NDRRecord
)


class CarrierCredentialInline(admin.TabularInline):
    model = CarrierCredential
    extra = 0
    fields = ['environment', 'api_key', 'base_url']


class CarrierZoneInline(admin.TabularInline):
    model = CarrierZone
    extra = 0


class CarrierRateInline(admin.TabularInline):
    model = CarrierRate
    extra = 0


@admin.register(Carrier)
class CarrierAdmin(BaseAdmin):
    list_display = ['name', 'code', 'status', 'supports_cod', 'priority', 'avg_delivery_days', 'success_rate']
    list_filter = ['status', 'supports_cod', 'supports_reverse']
    search_fields = ['name', 'code']
    inlines = [CarrierCredentialInline, CarrierZoneInline, CarrierRateInline]


@admin.register(ShippingRule)
class ShippingRuleAdmin(BaseAdmin):
    list_display = ['name', 'rule_type', 'priority', 'assigned_carrier', 'fallback_carrier', 'is_active']
    list_filter = ['rule_type', 'assigned_carrier', 'is_active']
    search_fields = ['name', 'description']


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
