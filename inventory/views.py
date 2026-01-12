from django.urls import reverse_lazy
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F, Q, Count
from django.utils import timezone
import json

from core import mixins
from master.models import Product
from .models import (
    Warehouse, StockLevel, LotBatch, StockMovement,
    StockTransfer, ReorderRule, InventoryAlert
)
from .tables import (
    WarehouseTable, StockLevelTable, StockMovementTable,
    StockTransferTable, InventoryAlertTable
)
from .forms import (
    WarehouseForm, StockLevelForm, StockMovementForm,
    StockTransferForm, StockAdjustmentForm
)
from .services import InventoryService


# Dashboard
class InventoryDashboardView(mixins.HybridTemplateView):
    template_name = 'inventory/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Inventory Dashboard'
        context['is_inventory'] = True
        context['is_dashboard'] = True
        
        # Summary stats
        context['total_products'] = Product.objects.filter(is_active=True).count()
        context['total_warehouses'] = Warehouse.objects.filter(is_active=True).count()
        
        # Stock status
        stock_levels = StockLevel.objects.filter(is_active=True)
        context['total_stock_value'] = stock_levels.aggregate(
            total=Sum(F('quantity') * F('product__price'))
        )['total'] or 0
        
        # Out of stock products
        context['out_of_stock'] = stock_levels.filter(quantity__lte=0).count()
        
        # Low stock products
        context['low_stock'] = stock_levels.filter(
            quantity__gt=0,
            quantity__lte=F('reorder_point')
        ).count()
        
        # Pending alerts
        context['pending_alerts'] = InventoryAlert.objects.filter(
            is_active=True, is_acknowledged=False
        ).count()
        
        # Recent movements
        context['recent_movements'] = StockMovement.objects.filter(
            is_active=True
        ).select_related('product', 'warehouse')[:10]
        
        # Warehouses with stock values
        context['warehouses'] = Warehouse.objects.filter(is_active=True).annotate(
            stock_value=Sum(F('stock_levels__quantity') * F('stock_levels__product__price'))
        )
        
        return context


# Warehouses
class WarehouseListView(mixins.HybridListView):
    model = Warehouse
    table_class = WarehouseTable
    filterset_fields = {'name': ['contains'], 'city': ['exact'], 'state': ['exact']}
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Warehouses'
        context['can_add'] = True
        context['new_link'] = reverse_lazy('inventory:warehouse_create')
        context['is_inventory'] = True
        context['is_warehouse'] = True
        return context


class WarehouseDetailView(mixins.HybridDetailView):
    model = Warehouse
    template_name = 'inventory/warehouse_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Warehouse: {self.object.name}'
        context['stock_levels'] = self.object.stock_levels.filter(is_active=True).select_related('product')[:50]
        context['total_value'] = self.object.get_total_stock_value()
        context['is_inventory'] = True
        context['is_warehouse'] = True
        return context


class WarehouseCreateView(mixins.HybridCreateView):
    model = Warehouse
    form_class = WarehouseForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'New Warehouse'
        context['is_inventory'] = True
        context['is_warehouse'] = True
        return context


class WarehouseUpdateView(mixins.HybridUpdateView):
    model = Warehouse
    form_class = WarehouseForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Update Warehouse: {self.object.name}'
        context['is_inventory'] = True
        context['is_warehouse'] = True
        return context


class WarehouseDeleteView(mixins.HybridDeleteView):
    model = Warehouse


# Stock Levels
class StockLevelListView(mixins.HybridListView):
    model = StockLevel
    table_class = StockLevelTable
    template_name = 'inventory/stock_list.html'
    filterset_fields = {'warehouse': ['exact'], 'product': ['exact']}
    search_fields = ['product__product_name', 'product__product_code']
    
    def get_queryset(self):
        qs = super().get_queryset().select_related('product', 'warehouse')
        
        status = self.request.GET.get('status')
        if status == 'low_stock':
            qs = qs.filter(quantity__gt=0, quantity__lte=F('reorder_point'))
        elif status == 'out_of_stock':
            qs = qs.filter(quantity__lte=0)
        elif status == 'in_stock':
            qs = qs.filter(quantity__gt=F('reorder_point'))
        
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Stock Levels'
        context['is_inventory'] = True
        context['is_stock'] = True
        
        # Counts
        all_stock = StockLevel.objects.filter(is_active=True)
        context['total_count'] = all_stock.count()
        context['low_stock_count'] = all_stock.filter(quantity__gt=0, quantity__lte=F('reorder_point')).count()
        context['out_of_stock_count'] = all_stock.filter(quantity__lte=0).count()
        context['in_stock_count'] = all_stock.filter(quantity__gt=F('reorder_point')).count()
        
        context['warehouses'] = Warehouse.objects.filter(is_active=True)
        
        return context


class StockLevelDetailView(mixins.HybridDetailView):
    model = StockLevel
    template_name = 'inventory/stock_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Stock: {self.object.product}'
        context['movements'] = StockMovement.objects.filter(
            product=self.object.product,
            warehouse=self.object.warehouse,
            is_active=True
        )[:20]
        context['lots'] = LotBatch.objects.filter(
            product=self.object.product,
            warehouse=self.object.warehouse,
            is_active=True
        )
        context['recommendation'] = InventoryService.calculate_reorder_recommendation(
            self.object.product, self.object.warehouse
        )
        context['is_inventory'] = True
        context['is_stock'] = True
        return context


# Stock Movements
class StockMovementListView(mixins.HybridListView):
    model = StockMovement
    table_class = StockMovementTable
    filterset_fields = {'movement_type': ['exact'], 'warehouse': ['exact']}
    search_fields = ['product__product_name', 'reference_id']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Stock Movements'
        context['can_add'] = True
        context['new_link'] = reverse_lazy('inventory:movement_create')
        context['is_inventory'] = True
        context['is_movement'] = True
        return context


class StockMovementCreateView(mixins.HybridCreateView):
    model = StockMovement
    form_class = StockMovementForm
    template_name = 'inventory/movement_form.html'
    
    def form_valid(self, form):
        form.instance.performed_by = self.request.user
        
        product = form.cleaned_data['product']
        warehouse = form.cleaned_data['warehouse']
        quantity = form.cleaned_data['quantity']
        movement_type = form.cleaned_data['movement_type']
        
        # Get or create stock level
        stock_level, _ = StockLevel.objects.get_or_create(
            product=product, warehouse=warehouse,
            defaults={'quantity': 0, 'is_active': True}
        )
        
        form.instance.stock_before = stock_level.quantity
        
        # Update stock based on movement type
        if movement_type in ['purchase', 'return_in', 'transfer_in', 'adjustment_in', 'initial']:
            stock_level.quantity += abs(quantity)
        else:
            stock_level.quantity -= abs(quantity)
            form.instance.quantity = -abs(quantity)
        
        form.instance.stock_after = stock_level.quantity
        stock_level.save()
        
        # Check for alerts
        InventoryService.check_and_create_alerts(stock_level)
        
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'New Stock Movement'
        context['is_inventory'] = True
        context['is_movement'] = True
        return context


# Stock Transfers
class StockTransferListView(mixins.HybridListView):
    model = StockTransfer
    table_class = StockTransferTable
    filterset_fields = {'status': ['exact'], 'source_warehouse': ['exact'], 'destination_warehouse': ['exact']}
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Stock Transfers'
        context['can_add'] = True
        context['new_link'] = reverse_lazy('inventory:transfer_create')
        context['is_inventory'] = True
        context['is_transfer'] = True
        return context


class StockTransferDetailView(mixins.HybridDetailView):
    model = StockTransfer
    template_name = 'inventory/transfer_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Transfer: {self.object.transfer_number}'
        context['items'] = self.object.items.all().select_related('product')
        context['is_inventory'] = True
        context['is_transfer'] = True
        return context


class StockTransferCreateView(mixins.HybridCreateView):
    model = StockTransfer
    form_class = StockTransferForm
    
    def form_valid(self, form):
        form.instance.requested_by = self.request.user
        # Generate transfer number
        import uuid
        form.instance.transfer_number = f"TRF-{uuid.uuid4().hex[:8].upper()}"
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'New Stock Transfer'
        context['is_inventory'] = True
        context['is_transfer'] = True
        return context


# Alerts
class InventoryAlertListView(mixins.HybridListView):
    model = InventoryAlert
    table_class = InventoryAlertTable
    filterset_fields = {'alert_type': ['exact'], 'priority': ['exact'], 'is_acknowledged': ['exact']}
    
    def get_queryset(self):
        return super().get_queryset().filter(is_acknowledged=False)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Inventory Alerts'
        context['is_inventory'] = True
        context['is_alert'] = True
        return context


# API Endpoints
@login_required
@require_POST
def adjust_stock(request):
    """API endpoint to adjust stock."""
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        warehouse_id = data.get('warehouse_id')
        new_quantity = data.get('new_quantity')
        reason = data.get('reason', '')
        
        product = Product.objects.get(pk=product_id)
        warehouse = Warehouse.objects.get(pk=warehouse_id)
        
        success, message = InventoryService.adjust_stock(
            product, warehouse, int(new_quantity), reason, request.user
        )
        
        return JsonResponse({'success': success, 'message': message})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def acknowledge_alert(request, pk):
    """Acknowledge an inventory alert."""
    try:
        alert = InventoryAlert.objects.get(pk=pk)
        alert.is_acknowledged = True
        alert.acknowledged_by = request.user
        alert.acknowledged_at = timezone.now()
        alert.save()
        
        return JsonResponse({'success': True})
    except InventoryAlert.DoesNotExist:
        return JsonResponse({'error': 'Alert not found'}, status=404)


@login_required
def get_product_stock(request, product_id):
    """Get stock levels for a product across all warehouses."""
    try:
        stock_levels = StockLevel.objects.filter(
            product_id=product_id, is_active=True
        ).select_related('warehouse').values(
            'warehouse__name', 'warehouse__code', 'quantity', 
            'reserved_quantity', 'safety_stock', 'reorder_point'
        )
        
        return JsonResponse({
            'product_id': product_id,
            'stock_levels': list(stock_levels),
            'total_available': sum(max(0, s['quantity'] - s['reserved_quantity']) for s in stock_levels)
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def inventory_dashboard_data(request):
    """API endpoint for inventory dashboard charts."""
    from datetime import timedelta
    
    today = timezone.now().date()
    last_7_days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    
    # Movements per day
    movements_in = []
    movements_out = []
    
    for day in last_7_days:
        day_movements = StockMovement.objects.filter(created__date=day, is_active=True)
        movements_in.append(day_movements.filter(quantity__gt=0).aggregate(total=Sum('quantity'))['total'] or 0)
        movements_out.append(abs(day_movements.filter(quantity__lt=0).aggregate(total=Sum('quantity'))['total'] or 0))
    
    # Stock by warehouse
    warehouse_stats = Warehouse.objects.filter(is_active=True).annotate(
        total_stock=Sum('stock_levels__quantity')
    ).values('name', 'total_stock')
    
    return JsonResponse({
        'dates': [d.strftime('%d %b') for d in last_7_days],
        'movements_in': movements_in,
        'movements_out': movements_out,
        'warehouse_distribution': {
            'labels': [w['name'] for w in warehouse_stats],
            'data': [w['total_stock'] or 0 for w in warehouse_stats]
        }
    })
