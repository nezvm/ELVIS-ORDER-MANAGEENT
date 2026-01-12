from django_tables2 import columns
from core.base import BaseTable
from .models import Warehouse, StockLevel, StockMovement, StockTransfer, InventoryAlert


class WarehouseTable(BaseTable):
    name = columns.Column(linkify=True)
    code = columns.Column()
    city = columns.Column()
    state = columns.Column()
    is_primary = columns.BooleanColumn(verbose_name="Primary")
    
    class Meta:
        model = Warehouse
        fields = ['name', 'code', 'city', 'state', 'is_primary', 'created']
        attrs = {'class': 'table table-striped table-bordered'}


class StockLevelTable(BaseTable):
    product = columns.Column(linkify=lambda record: record.get_absolute_url())
    warehouse = columns.Column()
    quantity = columns.Column()
    reserved_quantity = columns.Column(verbose_name="Reserved")
    available = columns.Column(accessor='available_quantity', verbose_name="Available")
    safety_stock = columns.Column(verbose_name="Safety")
    reorder_point = columns.Column(verbose_name="Reorder At")
    status = columns.Column(accessor='stock_status', verbose_name="Status")
    
    class Meta:
        model = StockLevel
        fields = ['product', 'warehouse', 'quantity', 'reserved_quantity', 'safety_stock', 'reorder_point']
        attrs = {'class': 'table table-striped table-bordered'}


class StockMovementTable(BaseTable):
    product = columns.Column()
    warehouse = columns.Column()
    movement_type = columns.Column()
    quantity = columns.Column()
    reference_id = columns.Column(verbose_name="Reference")
    performed_by = columns.Column(verbose_name="By")
    
    class Meta:
        model = StockMovement
        fields = ['product', 'warehouse', 'movement_type', 'quantity', 'reference_id', 'performed_by', 'created']
        attrs = {'class': 'table table-striped table-bordered'}


class StockTransferTable(BaseTable):
    transfer_number = columns.Column(linkify=True)
    source_warehouse = columns.Column(verbose_name="From")
    destination_warehouse = columns.Column(verbose_name="To")
    status = columns.Column()
    requested_by = columns.Column(verbose_name="Requested By")
    
    class Meta:
        model = StockTransfer
        fields = ['transfer_number', 'source_warehouse', 'destination_warehouse', 'status', 'requested_by', 'created']
        attrs = {'class': 'table table-striped table-bordered'}


class InventoryAlertTable(BaseTable):
    alert_type = columns.Column()
    priority = columns.Column()
    product = columns.Column()
    warehouse = columns.Column()
    current_stock = columns.Column()
    message = columns.Column()
    
    class Meta:
        model = InventoryAlert
        fields = ['alert_type', 'priority', 'product', 'warehouse', 'current_stock', 'message', 'created']
        attrs = {'class': 'table table-striped table-bordered'}
