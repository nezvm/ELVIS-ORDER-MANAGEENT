from rest_framework import serializers
from master.models import Order, OrderItem, Customer, Product, Channel
from channels_config.models import DynamicChannel, UTRRecord
from logistics.models import Carrier, Shipment, ShippingRule
from inventory.models import Warehouse, StockLevel, StockMovement
from segmentation.models import CustomerProfile, CustomerSegment


# Master serializers
class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'phone_no', 'customer_name', 'pincode', 'address', 
                  'city', 'state', 'country', 'alternate_phone_no', 'created']


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'product_name', 'product_code', 'size', 'price', 'image', 'created']


class ChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Channel
        fields = ['id', 'channel_type', 'prefix', 'created']


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), write_only=True, source='product')
    
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_id', 'price', 'quantity', 'amount']


class OrderSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)
    customer_id = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all(), write_only=True, source='customer')
    channel = ChannelSerializer(read_only=True)
    channel_id = serializers.PrimaryKeyRelatedField(queryset=Channel.objects.all(), write_only=True, source='channel', required=False)
    items = OrderItemSerializer(many=True, read_only=True, source='order_item')
    
    class Meta:
        model = Order
        fields = ['id', 'order_no', 'customer', 'customer_id', 'channel', 'channel_id',
                  'utr', 'cod_charge', 'total_amount', 'items', 'created']
        read_only_fields = ['order_no']


# Channel Config serializers
class DynamicChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = DynamicChannel
        fields = ['id', 'name', 'code', 'prefix', 'description', 'icon', 'color',
                  'is_cod_channel', 'requires_utr', 'requires_payment_capture', 
                  'sort_order', 'is_active', 'created']


class UTRRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = UTRRecord
        fields = ['id', 'utr', 'order', 'captured_by', 'captured_at', 'verified', 'notes']
        read_only_fields = ['captured_by', 'captured_at']


# Logistics serializers
class CarrierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Carrier
        fields = ['id', 'name', 'code', 'website', 'tracking_url_template',
                  'supports_cod', 'supports_prepaid', 'supports_reverse',
                  'status', 'priority', 'avg_delivery_days', 'sla_adherence_rate',
                  'success_rate', 'is_active', 'created']


class ShipmentSerializer(serializers.ModelSerializer):
    order = OrderSerializer(read_only=True)
    carrier = CarrierSerializer(read_only=True)
    
    class Meta:
        model = Shipment
        fields = ['id', 'order', 'carrier', 'tracking_number', 'awb_number', 'status',
                  'weight', 'shipping_cost', 'is_cod', 'cod_amount',
                  'expected_delivery_date', 'actual_delivery_date',
                  'label_url', 'assignment_method', 'created']


class ShippingRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingRule
        fields = ['id', 'name', 'description', 'rule_type', 'priority',
                  'condition_field', 'condition_operator', 'condition_value',
                  'assigned_carrier', 'fallback_carrier', 'is_active', 'created']


# Inventory serializers
class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = ['id', 'name', 'code', 'address', 'city', 'state', 'pincode',
                  'country', 'contact_person', 'contact_phone', 'contact_email',
                  'is_primary', 'is_active', 'created']


class StockLevelSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    warehouse = WarehouseSerializer(read_only=True)
    available_quantity = serializers.IntegerField(read_only=True)
    stock_status = serializers.CharField(read_only=True)
    
    class Meta:
        model = StockLevel
        fields = ['id', 'product', 'warehouse', 'quantity', 'reserved_quantity',
                  'available_quantity', 'safety_stock', 'reorder_point',
                  'reorder_quantity', 'bin_location', 'stock_status', 'created']


class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = ['id', 'product', 'warehouse', 'movement_type', 'quantity',
                  'reference_type', 'reference_id', 'unit_cost', 'notes',
                  'stock_before', 'stock_after', 'performed_by', 'created']
        read_only_fields = ['stock_before', 'stock_after', 'performed_by']


# Segmentation serializers
class CustomerProfileSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)
    
    class Meta:
        model = CustomerProfile
        fields = ['id', 'customer', 'lifetime_order_count', 'lifetime_revenue',
                  'average_order_value', 'first_order_date', 'last_order_date',
                  'days_since_last_order', 'primary_channel', 'channels_used',
                  'tier_city', 'logistics_zone', 'order_behavior_segment',
                  'lifecycle_stage', 'channel_loyalty', 'value_tier',
                  'loyalty_tier', 'loyalty_points', 'last_computed_at']


class CustomerSegmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerSegment
        fields = ['id', 'name', 'code', 'segment_type', 'description', 'color',
                  'icon', 'filter_criteria', 'customer_count', 'total_revenue',
                  'avg_order_value', 'last_computed_at', 'is_active', 'created']
