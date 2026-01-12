from django_tables2 import columns
from core.base import BaseTable
from .models import Carrier, Shipment, ShippingRule, NDRRecord


class CarrierTable(BaseTable):
    name = columns.Column(linkify=True)
    code = columns.Column()
    status = columns.Column()
    supports_cod = columns.BooleanColumn(verbose_name="COD")
    priority = columns.Column()
    success_rate = columns.Column(verbose_name="Success %")
    
    class Meta:
        model = Carrier
        fields = ['name', 'code', 'status', 'supports_cod', 'priority', 'success_rate', 'created']
        attrs = {'class': 'table table-striped table-bordered'}


class ShipmentTable(BaseTable):
    tracking_number = columns.Column(linkify=True)
    order = columns.Column(linkify=lambda record: record.order.get_absolute_url())
    carrier = columns.Column()
    status = columns.Column()
    is_cod = columns.BooleanColumn(verbose_name="COD")
    shipping_cost = columns.Column()
    
    class Meta:
        model = Shipment
        fields = ['tracking_number', 'order', 'carrier', 'status', 'is_cod', 'shipping_cost', 'created']
        attrs = {'class': 'table table-striped table-bordered'}


class ShippingRuleTable(BaseTable):
    name = columns.Column(linkify=True)
    rule_type = columns.Column()
    priority = columns.Column()
    assigned_carrier = columns.Column()
    fallback_carrier = columns.Column()
    
    class Meta:
        model = ShippingRule
        fields = ['name', 'rule_type', 'priority', 'assigned_carrier', 'fallback_carrier', 'created']
        attrs = {'class': 'table table-striped table-bordered'}


class NDRTable(BaseTable):
    shipment = columns.Column(linkify=lambda record: record.get_absolute_url())
    ndr_date = columns.DateTimeColumn(format='d/m/Y H:i')
    reason = columns.Column()
    attempt_number = columns.Column(verbose_name="Attempt")
    action = columns.Column()
    is_resolved = columns.BooleanColumn(verbose_name="Resolved")
    
    class Meta:
        model = NDRRecord
        fields = ['shipment', 'ndr_date', 'reason', 'attempt_number', 'action', 'is_resolved']
        attrs = {'class': 'table table-striped table-bordered'}
