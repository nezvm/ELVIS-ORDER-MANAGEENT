from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg, Sum, Q
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
import json
import csv

from core import mixins
from master.models import Order, Channel
from .models import (
    Carrier, CarrierCredential, CarrierAPILog, ShippingRule, Shipment, 
    ShipmentTracking, NDRRecord, PincodeRule, ChannelShippingRule, ShippingSettings
)
from .tables import CarrierTable, ShipmentTable, ShippingRuleTable, NDRTable
from .forms import CarrierForm, ShippingRuleForm, ShipmentForm, NDRActionForm


# Carrier Views
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
        context['credentials'] = self.object.credentials.filter(is_active=True)
        context['zones'] = self.object.zones.all()
        context['rates'] = self.object.rates.all()
        context['recent_logs'] = self.object.api_logs.all()[:20]
        context['is_logistics'] = True
        context['is_carrier'] = True
        
        # Performance stats
        shipments = self.object.shipments.filter(is_active=True)
        context['total_shipments'] = shipments.count()
        context['delivered_shipments'] = shipments.filter(status='delivered').count()
        context['pending_shipments'] = shipments.exclude(status__in=['delivered', 'cancelled', 'rto_delivered']).count()
        context['api_success_rate'] = self.object.api_success_rate
        
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


# Shipping Rules Views
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


# Pincode Rules Views
class PincodeRuleListView(mixins.HybridListView):
    model = PincodeRule
    template_name = 'logistics/pincode_rule_list.html'
    filterset_fields = {'pincode': ['contains'], 'carrier': ['exact'], 'rule_type': ['exact']}
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Pincode Rules'
        context['can_add'] = True
        context['new_link'] = reverse_lazy('logistics:pincode_rule_create')
        context['carriers'] = Carrier.objects.filter(status='active', is_active=True)
        context['is_logistics'] = True
        return context


class PincodeRuleCreateView(mixins.HybridCreateView):
    model = PincodeRule
    fields = ['pincode', 'carrier', 'rule_type', 'priority', 'supports_cod', 'supports_prepaid', 'delivery_days', 'notes']
    template_name = 'logistics/pincode_rule_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'New Pincode Rule'
        context['carriers'] = Carrier.objects.filter(status='active', is_active=True)
        context['is_logistics'] = True
        return context


class PincodeRuleUpdateView(mixins.HybridUpdateView):
    model = PincodeRule
    fields = ['pincode', 'carrier', 'rule_type', 'priority', 'supports_cod', 'supports_prepaid', 'delivery_days', 'notes']
    template_name = 'logistics/pincode_rule_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update Pincode Rule'
        context['carriers'] = Carrier.objects.filter(status='active', is_active=True)
        context['is_logistics'] = True
        return context


class PincodeRuleDeleteView(mixins.HybridDeleteView):
    model = PincodeRule


# Channel Rules Views
class ChannelRuleListView(mixins.HybridListView):
    model = ChannelShippingRule
    template_name = 'logistics/channel_rule_list.html'
    filterset_fields = {'channel': ['exact'], 'payment_type': ['exact'], 'carrier': ['exact']}
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Channel Shipping Rules'
        context['can_add'] = True
        context['new_link'] = reverse_lazy('logistics:channel_rule_create')
        context['channels'] = Channel.objects.filter(is_active=True)
        context['carriers'] = Carrier.objects.filter(status='active', is_active=True)
        context['is_logistics'] = True
        return context


class ChannelRuleCreateView(mixins.HybridCreateView):
    model = ChannelShippingRule
    fields = ['channel', 'payment_type', 'carrier', 'priority', 'is_enabled', 'notes']
    template_name = 'logistics/channel_rule_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'New Channel Rule'
        context['channels'] = Channel.objects.filter(is_active=True)
        context['carriers'] = Carrier.objects.filter(status='active', is_active=True)
        context['is_logistics'] = True
        return context


class ChannelRuleUpdateView(mixins.HybridUpdateView):
    model = ChannelShippingRule
    fields = ['channel', 'payment_type', 'carrier', 'priority', 'is_enabled', 'notes']
    template_name = 'logistics/channel_rule_form.html'


class ChannelRuleDeleteView(mixins.HybridDeleteView):
    model = ChannelShippingRule


# Shipments Views
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
        
        # Unfulfilled orders (orders without active shipments)
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


# Shipping Dashboard - Comprehensive View
class ShippingDashboardView(mixins.HybridTemplateView):
    template_name = 'logistics/shipping_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Shipping Dashboard'
        context['is_logistics'] = True
        
        # Get filter parameters
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        channel_id = self.request.GET.get('channel')
        carrier_id = self.request.GET.get('carrier')
        status_filter = self.request.GET.get('status', 'pending')
        
        # Build query for orders
        orders_qs = Order.objects.filter(is_active=True).select_related('customer', 'channel')
        
        if date_from:
            orders_qs = orders_qs.filter(created__date__gte=date_from)
        if date_to:
            orders_qs = orders_qs.filter(created__date__lte=date_to)
        if channel_id:
            orders_qs = orders_qs.filter(channel_id=channel_id)
        
        # Separate orders with and without shipments
        if status_filter == 'pending':
            # Orders without courier
            context['orders'] = orders_qs.exclude(
                shipments__status__in=['manifested', 'picked_up', 'in_transit', 'out_for_delivery', 'delivered']
            ).order_by('-created')[:100]
        elif status_filter == 'assigned':
            # Orders with assigned courier
            context['shipments'] = Shipment.objects.filter(
                is_active=True,
                order__in=orders_qs
            ).select_related('order', 'order__customer', 'carrier')
            if carrier_id:
                context['shipments'] = context['shipments'].filter(carrier_id=carrier_id)
            context['shipments'] = context['shipments'].order_by('-created')[:100]
        
        # Channels and Carriers for filters
        context['channels'] = Channel.objects.filter(is_active=True)
        context['carriers'] = Carrier.objects.filter(status='active', is_active=True)
        context['status_filter'] = status_filter
        
        # Stats
        today = timezone.now().date()
        context['pending_count'] = Order.objects.filter(is_active=True).exclude(
            shipments__status__in=['manifested', 'picked_up', 'in_transit', 'out_for_delivery', 'delivered']
        ).count()
        context['today_booked'] = Shipment.objects.filter(created__date=today, is_active=True).count()
        context['in_transit_count'] = Shipment.objects.filter(status='in_transit', is_active=True).count()
        
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


# API Log View
class APILogListView(mixins.HybridListView):
    model = CarrierAPILog
    template_name = 'logistics/api_log_list.html'
    filterset_fields = {'carrier': ['exact'], 'log_type': ['exact'], 'is_success': ['exact']}
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'API Logs'
        context['carriers'] = Carrier.objects.filter(is_active=True)
        context['is_logistics'] = True
        return context


# Shipping Settings View
class ShippingSettingsView(mixins.HybridTemplateView):
    template_name = 'logistics/shipping_settings.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Shipping Settings'
        context['settings'] = ShippingSettings.get_settings()
        context['carriers'] = Carrier.objects.filter(status='active', is_active=True)
        context['is_logistics'] = True
        return context
    
    def post(self, request, *args, **kwargs):
        settings = ShippingSettings.get_settings()
        
        primary_carrier_id = request.POST.get('primary_carrier')
        if primary_carrier_id:
            settings.primary_carrier = Carrier.objects.filter(pk=primary_carrier_id).first()
        else:
            settings.primary_carrier = None
        
        settings.enable_channel_rules = request.POST.get('enable_channel_rules') == 'on'
        settings.enable_pincode_rules = request.POST.get('enable_pincode_rules') == 'on'
        settings.enable_auto_allocation = request.POST.get('enable_auto_allocation') == 'on'
        settings.check_serviceability_before_allocation = request.POST.get('check_serviceability') == 'on'
        
        if request.POST.get('default_weight'):
            settings.default_weight_kg = request.POST.get('default_weight')
        if request.POST.get('max_cod_amount'):
            settings.max_cod_amount = request.POST.get('max_cod_amount')
        
        settings.save()
        messages.success(request, 'Settings saved successfully')
        return redirect('logistics:shipping_settings')


# API Endpoints
@login_required
@require_POST
def allocate_orders(request):
    """Allocate carrier to selected orders."""
    from .services import ShipmentAllocationService
    
    try:
        data = json.loads(request.body)
        order_ids = data.get('order_ids', [])
        carrier_id = data.get('carrier_id')  # Optional - for manual override
        
        if not order_ids:
            return JsonResponse({'error': 'No orders specified'}, status=400)
        
        service = ShipmentAllocationService()
        carrier = None
        if carrier_id:
            carrier = Carrier.objects.filter(pk=carrier_id, status='active').first()
        
        results = []
        for order_id in order_ids:
            try:
                order = Order.objects.get(pk=order_id, is_active=True)
                success, result = service.create_shipment(order, carrier=carrier, user=request.user)
                
                if success:
                    results.append({
                        'order_id': str(order_id),
                        'success': True,
                        'awb': result.awb_number,
                        'carrier': result.carrier.name
                    })
                else:
                    results.append({
                        'order_id': str(order_id),
                        'success': False,
                        'error': result
                    })
            except Order.DoesNotExist:
                results.append({
                    'order_id': str(order_id),
                    'success': False,
                    'error': 'Order not found'
                })
            except Exception as e:
                results.append({
                    'order_id': str(order_id),
                    'success': False,
                    'error': str(e)
                })
        
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
def bulk_allocate(request):
    """Bulk allocate carriers to all pending orders."""
    from .services import ShipmentAllocationService
    
    try:
        # Get all orders without active shipments
        orders = Order.objects.filter(is_active=True).exclude(
            shipments__status__in=['manifested', 'picked_up', 'in_transit', 'out_for_delivery', 'delivered']
        )[:50]  # Limit to 50 at a time
        
        service = ShipmentAllocationService()
        results = service.bulk_allocate(orders, user=request.user)
        
        return JsonResponse(results)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def force_book_awb(request, order_pk):
    """Force book AWB for a specific order."""
    from .services import ShipmentAllocationService
    
    try:
        data = json.loads(request.body) if request.body else {}
        carrier_id = data.get('carrier_id')
        
        order = get_object_or_404(Order, pk=order_pk, is_active=True)
        carrier = None
        if carrier_id:
            carrier = Carrier.objects.filter(pk=carrier_id, status='active').first()
        
        service = ShipmentAllocationService()
        success, result = service.create_shipment(order, carrier=carrier, user=request.user, force=True)
        
        if success:
            return JsonResponse({
                'success': True,
                'awb': result.awb_number,
                'carrier': result.carrier.name,
                'tracking_number': result.tracking_number
            })
        else:
            return JsonResponse({'success': False, 'error': result}, status=400)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def test_carrier_connection(request, pk):
    """Test carrier API connectivity."""
    from .courier_apis import CourierAPIRegistry
    
    try:
        carrier = get_object_or_404(Carrier, pk=pk)
        api = CourierAPIRegistry.get_api(carrier)
        result = api.test_connection()
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
@require_GET
def carrier_api_logs(request, pk):
    """Get API logs for a carrier."""
    carrier = get_object_or_404(Carrier, pk=pk)
    logs = carrier.api_logs.all()[:50]
    
    return JsonResponse({
        'logs': [{
            'id': str(log.id),
            'type': log.log_type,
            'url': log.request_url,
            'status': log.response_status,
            'success': log.is_success,
            'time_ms': log.response_time_ms,
            'created': log.created.isoformat(),
            'reference': log.reference_id
        } for log in logs]
    })


@login_required
@require_POST
def track_shipment(request, pk):
    """Update tracking for a shipment."""
    from .services import ShipmentAllocationService
    
    try:
        shipment = get_object_or_404(Shipment, pk=pk)
        service = ShipmentAllocationService()
        success, message = service.update_tracking(shipment)
        
        return JsonResponse({'success': success, 'message': message})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def cancel_shipment(request, pk):
    """Cancel a shipment."""
    from .services import ShipmentAllocationService
    
    try:
        shipment = get_object_or_404(Shipment, pk=pk)
        service = ShipmentAllocationService()
        success, message = service.cancel_shipment(shipment)
        
        return JsonResponse({'success': success, 'message': message})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def download_label(request, pk):
    """Redirect to shipping label URL."""
    shipment = get_object_or_404(Shipment, pk=pk)
    
    if shipment.label_url:
        return redirect(shipment.label_url)
    else:
        messages.error(request, 'No label available for this shipment')
        return redirect('logistics:shipment_detail', pk=pk)


@login_required
@require_POST
def ndr_action(request, pk):
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
@require_POST
def bulk_upload_pincodes(request):
    """Bulk upload pincode rules from CSV."""
    if 'file' not in request.FILES:
        return JsonResponse({'error': 'No file uploaded'}, status=400)
    
    try:
        file = request.FILES['file']
        decoded = file.read().decode('utf-8').splitlines()
        reader = csv.DictReader(decoded)
        
        created = 0
        updated = 0
        errors = []
        
        for row in reader:
            try:
                pincode = row.get('pincode', '').strip()
                carrier_code = row.get('carrier_code', '').strip()
                
                if not pincode or not carrier_code:
                    errors.append(f"Missing pincode or carrier_code in row")
                    continue
                
                carrier = Carrier.objects.filter(code=carrier_code, is_active=True).first()
                if not carrier:
                    errors.append(f"Carrier not found: {carrier_code}")
                    continue
                
                rule, was_created = PincodeRule.objects.update_or_create(
                    pincode=pincode,
                    carrier=carrier,
                    rule_type='manual',
                    defaults={
                        'priority': int(row.get('priority', 0)),
                        'supports_cod': row.get('supports_cod', 'true').lower() == 'true',
                        'supports_prepaid': row.get('supports_prepaid', 'true').lower() == 'true',
                        'delivery_days': int(row.get('delivery_days')) if row.get('delivery_days') else None,
                        'notes': row.get('notes', '')
                    }
                )
                
                if was_created:
                    created += 1
                else:
                    updated += 1
                    
            except Exception as e:
                errors.append(f"Error processing row: {str(e)}")
        
        return JsonResponse({
            'success': True,
            'created': created,
            'updated': updated,
            'errors': errors[:10]  # Return first 10 errors
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


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
