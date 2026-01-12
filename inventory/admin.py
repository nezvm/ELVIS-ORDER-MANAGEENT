from django.contrib import admin
from core.base import BaseAdmin
from .models import (
    Warehouse, StockLevel, LotBatch, StockMovement,
    StockTransfer, StockTransferItem, ReorderRule, InventoryAlert
)


@admin.register(Warehouse)
class WarehouseAdmin(BaseAdmin):
    list_display = ['name', 'code', 'city', 'state', 'is_primary', 'is_active']
    list_filter = ['is_primary', 'state', 'is_active']
    search_fields = ['name', 'code', 'city']


@admin.register(StockLevel)
class StockLevelAdmin(BaseAdmin):
    list_display = ['product', 'warehouse', 'quantity', 'reserved_quantity', 'available_quantity', 'safety_stock', 'stock_status']
    list_filter = ['warehouse', 'is_active']
    search_fields = ['product__product_name', 'product__product_code']
    
    def available_quantity(self, obj):
        return obj.available_quantity
    available_quantity.short_description = 'Available'
    
    def stock_status(self, obj):
        return obj.stock_status
    stock_status.short_description = 'Status'


@admin.register(LotBatch)
class LotBatchAdmin(BaseAdmin):
    list_display = ['product', 'warehouse', 'lot_number', 'quantity', 'manufacturing_date', 'expiry_date', 'is_expired']
    list_filter = ['warehouse', 'is_active']
    search_fields = ['product__product_name', 'lot_number', 'batch_number']
    
    def is_expired(self, obj):
        return obj.is_expired
    is_expired.boolean = True


@admin.register(StockMovement)
class StockMovementAdmin(BaseAdmin):
    list_display = ['product', 'warehouse', 'movement_type', 'quantity', 'reference_type', 'reference_id', 'created']
    list_filter = ['movement_type', 'warehouse', 'created']
    search_fields = ['product__product_name', 'reference_id']
    readonly_fields = ['stock_before', 'stock_after']


class StockTransferItemInline(admin.TabularInline):
    model = StockTransferItem
    extra = 1


@admin.register(StockTransfer)
class StockTransferAdmin(BaseAdmin):
    list_display = ['transfer_number', 'source_warehouse', 'destination_warehouse', 'status', 'requested_by', 'created']
    list_filter = ['status', 'source_warehouse', 'destination_warehouse']
    search_fields = ['transfer_number']
    inlines = [StockTransferItemInline]


@admin.register(ReorderRule)
class ReorderRuleAdmin(BaseAdmin):
    list_display = ['product', 'warehouse', 'reorder_point', 'reorder_quantity', 'lead_time_days', 'auto_reorder']
    list_filter = ['warehouse', 'auto_reorder']
    search_fields = ['product__product_name']


@admin.register(InventoryAlert)
class InventoryAlertAdmin(BaseAdmin):
    list_display = ['alert_type', 'priority', 'product', 'warehouse', 'current_stock', 'is_acknowledged', 'created']
    list_filter = ['alert_type', 'priority', 'is_acknowledged', 'warehouse']
    search_fields = ['product__product_name', 'message']
