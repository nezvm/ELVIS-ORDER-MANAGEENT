from django.urls import reverse_lazy
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg, Sum, Q
from django.utils import timezone
from django.shortcuts import get_object_or_404
import json

from core import mixins
from master.models import Order
from .models import (
    Carrier, CarrierCredential, ShippingRule, Shipment, 
    ShipmentTracking, NDRRecord
)
from .tables import CarrierTable, ShipmentTable, ShippingRuleTable, NDRTable
from .forms import CarrierForm, ShippingRuleForm, ShipmentForm, NDRActionForm
from .services import CarrierAllocationService, MockCarrierService


class CarrierListView(mixins.HybridListView):
    model = Carrier
    table_class = CarrierTable
    template_name = 'logistics/carrier_list.html'
    filterset_fields = {'name': ['contains'], 'status': ['exact'], 'supports_cod': ['exact']}
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Carriers'
        context['can_add'] = True
        context['new_link'] = reverse_lazy('logistics:carrier_create')
        context['is_logistics'] = True
        context['is_carrier'] = True
        return context


class CarrierDetailView(mixins.HybridDetailView):
    model = Carrier
    template_name = 'logistics/carrier_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Carrier: {self.object.name}'
        context['credentials'] = self.object.credentials.all()
        context['zones'] = self.object.zones.all()
        context['rates'] = self.object.rates.all()
        context['is_logistics'] = True
        context['is_carrier'] = True
        
        # Performance stats
        shipments = self.object.shipments.filter(is_active=True)
        context['total_shipments'] = shipments.count()
        context['delivered_shipments'] = shipments.filter(status='delivered').count()
        context['pending_shipments'] = shipments.exclude(status__in=['delivered', 'cancelled', 'rto_delivered']).count()
        
        return context


class CarrierCreateView(mixins.HybridCreateView):
    model = Carrier
    form_class = CarrierForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'New Carrier'
        context['is_logistics'] = True
        context['is_carrier'] = True
        return context


class CarrierUpdateView(mixins.HybridUpdateView):
    model = Carrier
    form_class = CarrierForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Update Carrier: {self.object.name}'
        context['is_logistics'] = True
        context['is_carrier'] = True
        return context


class CarrierDeleteView(mixins.HybridDeleteView):
    model = Carrier


# Shipping Rules
class ShippingRuleListView(mixins.HybridListView):
    model = ShippingRule
    table_class = ShippingRuleTable
    template_name = 'logistics/rule_list.html'
    filterset_fields = {'rule_type': ['exact'], 'assigned_carrier': ['exact']}
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Shipping Rules'
        context['can_add'] = True
        context['new_link'] = reverse_lazy('logistics:rule_create')
        context['is_logistics'] = True
        context['is_rule'] = True
        return context


class ShippingRuleDetailView(mixins.HybridDetailView):
    model = ShippingRule
    template_name = 'logistics/rule_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Rule: {self.object.name}'
        context['is_logistics'] = True
        context['is_rule'] = True
        return context


class ShippingRuleCreateView(mixins.HybridCreateView):
    model = ShippingRule
    form_class = ShippingRuleForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'New Shipping Rule'
        context['is_logistics'] = True
        context['is_rule'] = True
        return context


class ShippingRuleUpdateView(mixins.HybridUpdateView):
    model = ShippingRule
    form_class = ShippingRuleForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Update Rule: {self.object.name}'
        context['is_logistics'] = True
        context['is_rule'] = True
        return context


class ShippingRuleDeleteView(mixins.HybridDeleteView):
    model = ShippingRule


# Shipments
class ShipmentListView(mixins.HybridListView):
    model = Shipment
    table_class = ShipmentTable
    template_name = 'logistics/shipment_list.html'
    filterset_fields = {'status': ['exact'], 'carrier': ['exact'], 'is_cod': ['exact']}
    search_fields = ['tracking_number', 'order__order_no', 'order__customer__customer_name']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Shipments'
        context['is_logistics'] = True
        context['is_shipment'] = True
        
        # Status counts
        qs = Shipment.objects.filter(is_active=True)
        context['pending_count'] = qs.filter(status='pending').count()
        context['in_transit_count'] = qs.filter(status='in_transit').count()
        context['delivered_count'] = qs.filter(status='delivered').count()
        context['ndr_count'] = NDRRecord.objects.filter(is_active=True, is_resolved=False).count()
        
        return context


class ShipmentDetailView(mixins.HybridDetailView):
    model = Shipment
    template_name = 'logistics/shipment_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Shipment: {self.object.tracking_number}'
        context['tracking_events'] = self.object.tracking_events.all()[:20]
        context['ndr_records'] = self.object.ndr_records.all()
        context['is_logistics'] = True
        context['is_shipment'] = True
        return context


class ShipmentUpdateView(mixins.HybridUpdateView):
    model = Shipment
    form_class = ShipmentForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Update Shipment: {self.object.tracking_number}'
        context['is_logistics'] = True
        context['is_shipment'] = True
        return context


# Logistics Panel - Main Dashboard
class LogisticsPanelView(mixins.HybridTemplateView):
    template_name = 'logistics/panel.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Logistics Panel'
        context['is_logistics'] = True
        context['is_panel'] = True
        
        # Unfulfilled orders (orders without shipments)
        unfulfilled_orders = Order.objects.filter(
            is_active=True
        ).exclude(
            shipments__status__in=['manifested', 'picked_up', 'in_transit', 'out_for_delivery', 'delivered']
        ).order_by('-created')[:100]
        context['unfulfilled_orders'] = unfulfilled_orders
        context['unfulfilled_count'] = unfulfilled_orders.count()
        
        # Available carriers
        context['carriers'] = Carrier.objects.filter(is_active=True, status='active')
        
        # Today's stats
        today = timezone.now().date()
        today_shipments = Shipment.objects.filter(created__date=today, is_active=True)
        context['today_shipped'] = today_shipments.count()
        context['today_delivered'] = today_shipments.filter(status='delivered').count()
        
        # Pending NDRs
        context['pending_ndrs'] = NDRRecord.objects.filter(is_active=True, is_resolved=False).count()
        
        return context


# NDR Management
class NDRListView(mixins.HybridListView):
    model = NDRRecord
    table_class = NDRTable
    template_name = 'logistics/ndr_list.html'
    filterset_fields = {'reason': ['exact'], 'action': ['exact'], 'is_resolved': ['exact']}
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'NDR Management'
        context['is_logistics'] = True
        context['is_ndr'] = True
        
        # Counts by reason
        ndr_counts = NDRRecord.objects.filter(is_active=True, is_resolved=False).values('reason').annotate(count=Count('id'))
        context['ndr_counts'] = {item['reason']: item['count'] for item in ndr_counts}
        
        return context


class NDRDetailView(mixins.HybridDetailView):
    model = NDRRecord
    template_name = 'logistics/ndr_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'NDR: {self.object.shipment.tracking_number}'
        context['action_form'] = NDRActionForm(instance=self.object)
        context['is_logistics'] = True
        context['is_ndr'] = True
        return context


# API Endpoints
@login_required
@require_POST
def assign_carrier(request):
    """Assign carrier to orders (single or bulk)."""
    try:
        data = json.loads(request.body)
        order_ids = data.get('order_ids', [])
        carrier_id = data.get('carrier_id')
        method = data.get('method', 'manual')  # 'manual', 'rule_based', 'performance_based'
        
        if not order_ids:
            return JsonResponse({'error': 'No orders specified'}, status=400)
        
        results = []
        allocation_service = CarrierAllocationService()
        carrier_service = MockCarrierService()
        
        for order_id in order_ids:
            try:
                order = Order.objects.get(pk=order_id, is_active=True)
                
                # Determine carrier
                if method == 'manual' and carrier_id:
                    carrier = Carrier.objects.get(pk=carrier_id, is_active=True, status='active')
                    rule_used = None
                elif method == 'rule_based':
                    carrier, rule_used = allocation_service.allocate_by_rules(order)
                elif method == 'performance_based':
                    carrier = allocation_service.allocate_by_performance(order)
                    rule_used = None
                else:
                    return JsonResponse({'error': 'Invalid assignment method'}, status=400)
                
                if not carrier:
                    results.append({'order_id': order_id, 'success': False, 'error': 'No suitable carrier found'})
                    continue
                
                # Create shipment using mock carrier service
                shipment_data = carrier_service.create_shipment(order, carrier)
                
                shipment = Shipment.objects.create(
                    order=order,
                    carrier=carrier,
                    tracking_number=shipment_data['tracking_number'],
                    awb_number=shipment_data.get('awb_number'),
                    status='manifested',
                    weight=shipment_data.get('weight', 0.5),
                    shipping_cost=shipment_data.get('shipping_cost', 0),
                    is_cod=order.cod_charge > 0,
                    cod_amount=order.cod_charge,
                    assigned_by=request.user,
                    assignment_method=method,
                    rule_used=rule_used,
                    carrier_response=shipment_data,
                    label_url=shipment_data.get('label_url'),
                )
                
                results.append({
                    'order_id': order_id,
                    'success': True,
                    'shipment_id': str(shipment.id),
                    'tracking_number': shipment.tracking_number,
                    'carrier': carrier.name
                })
                
            except Order.DoesNotExist:
                results.append({'order_id': order_id, 'success': False, 'error': 'Order not found'})
            except Carrier.DoesNotExist:
                results.append({'order_id': order_id, 'success': False, 'error': 'Carrier not found'})
            except Exception as e:
                results.append({'order_id': order_id, 'success': False, 'error': str(e)})
        
        success_count = sum(1 for r in results if r['success'])
        return JsonResponse({
            'success': True,
            'total': len(order_ids),
            'success_count': success_count,
            'results': results
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def update_ndr_action(request, pk):
    """Update NDR action."""
    try:
        ndr = get_object_or_404(NDRRecord, pk=pk)
        data = json.loads(request.body)
        
        ndr.action = data.get('action')
        ndr.action_notes = data.get('action_notes', '')
        ndr.action_by = request.user
        ndr.action_date = timezone.now()
        
        if data.get('customer_contacted'):
            ndr.customer_contacted = True
            ndr.customer_response = data.get('customer_response', '')
        
        if data.get('new_delivery_date'):
            ndr.new_delivery_date = data.get('new_delivery_date')
        
        if data.get('is_resolved'):
            ndr.is_resolved = True
            ndr.resolution_date = timezone.now()
        
        ndr.save()
        
        return JsonResponse({'success': True, 'message': 'NDR action updated'})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def get_carrier_recommendation(request):
    """Get carrier recommendation for an order."""
    order_id = request.GET.get('order_id')
    
    if not order_id:
        return JsonResponse({'error': 'Order ID required'}, status=400)
    
    try:
        order = Order.objects.get(pk=order_id, is_active=True)
        allocation_service = CarrierAllocationService()
        
        # Get rule-based recommendation
        rule_carrier, rule = allocation_service.allocate_by_rules(order)
        
        # Get performance-based recommendation
        perf_carrier = allocation_service.allocate_by_performance(order)
        
        return JsonResponse({
            'rule_based': {
                'carrier_id': str(rule_carrier.id) if rule_carrier else None,
                'carrier_name': rule_carrier.name if rule_carrier else None,
                'rule_name': rule.name if rule else None,
            },
            'performance_based': {
                'carrier_id': str(perf_carrier.id) if perf_carrier else None,
                'carrier_name': perf_carrier.name if perf_carrier else None,
            }
        })
        
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Order not found'}, status=404)


@login_required
def logistics_dashboard_data(request):
    """API endpoint for logistics dashboard charts."""
    from datetime import timedelta
    
    today = timezone.now().date()
    last_7_days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    
    # Shipments per day
    shipments_per_day = []
    deliveries_per_day = []
    
    for day in last_7_days:
        shipments = Shipment.objects.filter(created__date=day, is_active=True).count()
        deliveries = Shipment.objects.filter(actual_delivery_date__date=day, is_active=True).count()
        shipments_per_day.append(shipments)
        deliveries_per_day.append(deliveries)
    
    # Carrier distribution
    carrier_stats = Shipment.objects.filter(
        is_active=True,
        created__date__gte=today - timedelta(days=30)
    ).values('carrier__name').annotate(count=Count('id')).order_by('-count')[:5]
    
    return JsonResponse({
        'dates': [d.strftime('%d %b') for d in last_7_days],
        'shipments_per_day': shipments_per_day,
        'deliveries_per_day': deliveries_per_day,
        'carrier_distribution': {
            'labels': [s['carrier__name'] for s in carrier_stats],
            'data': [s['count'] for s in carrier_stats]
        }
    })
