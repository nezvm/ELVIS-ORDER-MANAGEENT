from django_tables2 import columns
from core.base import BaseTable
from .models import CustomerProfile, CustomerSegment


class CustomerProfileTable(BaseTable):
    customer = columns.Column(linkify=lambda record: record.get_absolute_url(), accessor='customer__customer_name')
    phone = columns.Column(accessor='customer__phone_no')
    lifetime_orders = columns.Column(accessor='lifetime_order_count')
    lifetime_revenue = columns.Column()
    average_order_value = columns.Column(verbose_name="AOV")
    order_behavior_segment = columns.Column(verbose_name="Behavior")
    lifecycle_stage = columns.Column(verbose_name="Lifecycle")
    value_tier = columns.Column(verbose_name="Value")
    loyalty_tier = columns.Column(verbose_name="Loyalty")
    
    class Meta:
        model = CustomerProfile
        fields = ['customer', 'phone', 'lifetime_orders', 'lifetime_revenue', 'average_order_value']
        attrs = {'class': 'table table-striped table-bordered'}


class CustomerSegmentTable(BaseTable):
    name = columns.Column(linkify=True)
    code = columns.Column()
    segment_type = columns.Column()
    customer_count = columns.Column(verbose_name="Customers")
    total_revenue = columns.Column(verbose_name="Revenue")
    avg_order_value = columns.Column(verbose_name="AOV")
    
    class Meta:
        model = CustomerSegment
        fields = ['name', 'code', 'segment_type', 'customer_count', 'total_revenue', 'avg_order_value', 'created']
        attrs = {'class': 'table table-striped table-bordered'}
