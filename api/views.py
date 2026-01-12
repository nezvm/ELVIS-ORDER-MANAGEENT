from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Count

from master.models import Order, OrderItem, Customer, Product, Channel
from channels_config.models import DynamicChannel, UTRRecord
from logistics.models import Carrier, Shipment, ShippingRule
from inventory.models import Warehouse, StockLevel, StockMovement
from segmentation.models import CustomerProfile, CustomerSegment

from .serializers import (
    CustomerSerializer, ProductSerializer, ChannelSerializer,
    OrderSerializer, OrderItemSerializer,
    DynamicChannelSerializer, UTRRecordSerializer,
    CarrierSerializer, ShipmentSerializer, ShippingRuleSerializer,
    WarehouseSerializer, StockLevelSerializer, StockMovementSerializer,
    CustomerProfileSerializer, CustomerSegmentSerializer
)


# Master ViewSets
class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.filter(is_active=True)
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['city', 'state', 'pincode']
    search_fields = ['customer_name', 'phone_no']
    ordering_fields = ['created', 'customer_name']
    
    @action(detail=True, methods=['get'])
    def orders(self, request, pk=None):
        customer = self.get_object()
        orders = Order.objects.filter(customer=customer, is_active=True)
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def profile(self, request, pk=None):
        customer = self.get_object()
        try:
            profile = customer.profile
            serializer = CustomerProfileSerializer(profile)
            return Response(serializer.data)
        except CustomerProfile.DoesNotExist:
            return Response({'error': 'Profile not found'}, status=404)


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['product_name', 'product_code']
    ordering_fields = ['created', 'product_name', 'price']
    
    @action(detail=True, methods=['get'])
    def stock(self, request, pk=None):
        product = self.get_object()
        stock_levels = StockLevel.objects.filter(product=product, is_active=True)
        serializer = StockLevelSerializer(stock_levels, many=True)
        return Response(serializer.data)


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.filter(is_active=True).select_related('customer', 'channel')
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['channel', 'customer']
    search_fields = ['order_no', 'customer__customer_name', 'customer__phone_no']
    ordering_fields = ['created', 'total_amount']
    
    @action(detail=True, methods=['get'])
    def shipments(self, request, pk=None):
        order = self.get_object()
        shipments = order.shipments.filter(is_active=True)
        serializer = ShipmentSerializer(shipments, many=True)
        return Response(serializer.data)


# Channel Config ViewSets
class DynamicChannelViewSet(viewsets.ModelViewSet):
    queryset = DynamicChannel.objects.filter(is_active=True)
    serializer_class = DynamicChannelSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'code']
    ordering_fields = ['sort_order', 'name']


# Logistics ViewSets
class CarrierViewSet(viewsets.ModelViewSet):
    queryset = Carrier.objects.filter(is_active=True)
    serializer_class = CarrierSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'supports_cod']
    search_fields = ['name', 'code']
    ordering_fields = ['priority', 'name', 'success_rate']
    
    @action(detail=True, methods=['get'])
    def shipments(self, request, pk=None):
        carrier = self.get_object()
        shipments = carrier.shipments.filter(is_active=True)[:100]
        serializer = ShipmentSerializer(shipments, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        carrier = self.get_object()
        shipments = carrier.shipments.filter(is_active=True)
        
        stats = {
            'total_shipments': shipments.count(),
            'delivered': shipments.filter(status='delivered').count(),
            'in_transit': shipments.filter(status='in_transit').count(),
            'pending': shipments.filter(status='pending').count(),
            'avg_delivery_days': carrier.avg_delivery_days,
            'success_rate': carrier.success_rate,
            'sla_adherence': carrier.sla_adherence_rate,
        }
        return Response(stats)


class ShipmentViewSet(viewsets.ModelViewSet):
    queryset = Shipment.objects.filter(is_active=True).select_related('order', 'carrier')
    serializer_class = ShipmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'carrier', 'is_cod']
    search_fields = ['tracking_number', 'awb_number', 'order__order_no']
    ordering_fields = ['created', 'status']


class ShippingRuleViewSet(viewsets.ModelViewSet):
    queryset = ShippingRule.objects.filter(is_active=True)
    serializer_class = ShippingRuleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['rule_type', 'assigned_carrier']
    ordering_fields = ['priority', 'name']


# Inventory ViewSets
class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.filter(is_active=True)
    serializer_class = WarehouseSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['state', 'city', 'is_primary']
    search_fields = ['name', 'code']
    
    @action(detail=True, methods=['get'])
    def stock(self, request, pk=None):
        warehouse = self.get_object()
        stock_levels = warehouse.stock_levels.filter(is_active=True)
        serializer = StockLevelSerializer(stock_levels, many=True)
        return Response(serializer.data)


class StockLevelViewSet(viewsets.ModelViewSet):
    queryset = StockLevel.objects.filter(is_active=True).select_related('product', 'warehouse')
    serializer_class = StockLevelSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['warehouse', 'product']
    search_fields = ['product__product_name', 'product__product_code']
    
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        from django.db.models import F
        low_stock = StockLevel.objects.filter(
            is_active=True,
            quantity__lte=F('reorder_point')
        ).select_related('product', 'warehouse')
        serializer = self.get_serializer(low_stock, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def out_of_stock(self, request):
        out_of_stock = StockLevel.objects.filter(
            is_active=True,
            quantity__lte=0
        ).select_related('product', 'warehouse')
        serializer = self.get_serializer(out_of_stock, many=True)
        return Response(serializer.data)


# Segmentation ViewSets
class CustomerProfileViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CustomerProfile.objects.filter(is_active=True).select_related('customer')
    serializer_class = CustomerProfileSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['value_tier', 'lifecycle_stage', 'order_behavior_segment', 'loyalty_tier']
    search_fields = ['customer__customer_name', 'customer__phone_no']
    ordering_fields = ['lifetime_revenue', 'lifetime_order_count', 'last_order_date']


class CustomerSegmentViewSet(viewsets.ModelViewSet):
    queryset = CustomerSegment.objects.filter(is_active=True)
    serializer_class = CustomerSegmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['segment_type']
    search_fields = ['name', 'code']
    
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        segment = self.get_object()
        memberships = segment.members.filter(is_active=True).select_related('profile', 'profile__customer')[:100]
        profiles = [m.profile for m in memberships]
        serializer = CustomerProfileSerializer(profiles, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def refresh(self, request, pk=None):
        from segmentation.services import SegmentationService
        segment = self.get_object()
        count = SegmentationService.assign_profiles_to_segment(segment)
        return Response({'success': True, 'count': count})
