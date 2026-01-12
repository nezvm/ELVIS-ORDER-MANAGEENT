import uuid
from django.db import models
from django.urls import reverse_lazy
from django.db.models import Sum, F
from core.base import BaseModel
from decimal import Decimal


class Warehouse(BaseModel):
    """Warehouses/storage locations."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    country = models.CharField(max_length=100, default='India')
    contact_person = models.CharField(max_length=200, blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    is_primary = models.BooleanField(default=False, help_text="Primary warehouse for fulfillment")
    
    class Meta:
        verbose_name = "Warehouse"
        verbose_name_plural = "Warehouses"
        ordering = ['-is_primary', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    @staticmethod
    def get_list_url():
        return reverse_lazy("inventory:warehouse_list")
    
    def get_absolute_url(self):
        return reverse_lazy("inventory:warehouse_detail", kwargs={"pk": str(self.pk)})
    
    def get_update_url(self):
        return reverse_lazy("inventory:warehouse_update", kwargs={"pk": str(self.pk)})
    
    def get_delete_url(self):
        return reverse_lazy("inventory:warehouse_delete", kwargs={"pk": str(self.pk)})
    
    def get_total_stock_value(self):
        """Calculate total stock value in this warehouse."""
        return StockLevel.objects.filter(
            warehouse=self, is_active=True
        ).aggregate(
            total=Sum(F('quantity') * F('product__price'))
        )['total'] or Decimal('0.00')


class StockLevel(BaseModel):
    """Current stock levels per product per warehouse."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey('master.Product', on_delete=models.CASCADE, related_name='stock_levels')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stock_levels')
    quantity = models.IntegerField(default=0)
    reserved_quantity = models.IntegerField(default=0, help_text="Quantity reserved for pending orders")
    safety_stock = models.IntegerField(default=0, help_text="Minimum stock level to maintain")
    reorder_point = models.IntegerField(default=0, help_text="Stock level that triggers reorder")
    reorder_quantity = models.IntegerField(default=0, help_text="Quantity to order when reorder point is reached")
    bin_location = models.CharField(max_length=100, blank=True, null=True, help_text="Location in warehouse (e.g., A-12-3)")
    last_counted_at = models.DateTimeField(null=True, blank=True)
    last_counted_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_counts')
    
    class Meta:
        verbose_name = "Stock Level"
        verbose_name_plural = "Stock Levels"
        unique_together = ['product', 'warehouse']
        ordering = ['product__product_name']
    
    def __str__(self):
        return f"{self.product} @ {self.warehouse.code}: {self.quantity}"
    
    @property
    def available_quantity(self):
        """Quantity available for sale (excluding reserved)."""
        return max(0, self.quantity - self.reserved_quantity)
    
    @property
    def is_low_stock(self):
        """Check if stock is below reorder point."""
        return self.quantity <= self.reorder_point
    
    @property
    def is_out_of_stock(self):
        """Check if stock is zero or negative."""
        return self.available_quantity <= 0
    
    @property
    def stock_status(self):
        """Get stock status as string."""
        if self.is_out_of_stock:
            return 'out_of_stock'
        elif self.is_low_stock:
            return 'low_stock'
        return 'in_stock'
    
    @staticmethod
    def get_list_url():
        return reverse_lazy("inventory:stock_list")
    
    def get_absolute_url(self):
        return reverse_lazy("inventory:stock_detail", kwargs={"pk": str(self.pk)})


class LotBatch(BaseModel):
    """Lot/Batch tracking for products."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey('master.Product', on_delete=models.CASCADE, related_name='lots')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='lots')
    lot_number = models.CharField(max_length=100)
    batch_number = models.CharField(max_length=100, blank=True, null=True)
    quantity = models.IntegerField(default=0)
    manufacturing_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    supplier = models.CharField(max_length=200, blank=True, null=True)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Lot/Batch"
        verbose_name_plural = "Lots/Batches"
        unique_together = ['product', 'warehouse', 'lot_number']
        ordering = ['expiry_date', 'lot_number']
    
    def __str__(self):
        return f"{self.product} - Lot: {self.lot_number}"
    
    @property
    def is_expired(self):
        from django.utils import timezone
        if self.expiry_date:
            return self.expiry_date < timezone.now().date()
        return False


class StockMovement(BaseModel):
    """Track all stock movements (in/out/transfers/adjustments)."""
    MOVEMENT_TYPES = [
        ('purchase', 'Purchase/Receipt'),
        ('sale', 'Sale/Dispatch'),
        ('return_in', 'Customer Return'),
        ('return_out', 'Return to Supplier'),
        ('transfer_in', 'Transfer In'),
        ('transfer_out', 'Transfer Out'),
        ('adjustment_in', 'Adjustment In'),
        ('adjustment_out', 'Adjustment Out'),
        ('damage', 'Damaged/Lost'),
        ('expired', 'Expired'),
        ('initial', 'Initial Stock'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey('master.Product', on_delete=models.CASCADE, related_name='movements')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='movements')
    movement_type = models.CharField(max_length=30, choices=MOVEMENT_TYPES)
    quantity = models.IntegerField(help_text="Positive for in, negative for out")
    reference_type = models.CharField(max_length=50, blank=True, null=True, help_text="Order, Transfer, Adjustment, etc.")
    reference_id = models.CharField(max_length=100, blank=True, null=True, help_text="Order number, Transfer ID, etc.")
    lot = models.ForeignKey(LotBatch, on_delete=models.SET_NULL, null=True, blank=True, related_name='movements')
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True, null=True)
    performed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='stock_movements')
    
    # Stock levels after movement
    stock_before = models.IntegerField(default=0)
    stock_after = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = "Stock Movement"
        verbose_name_plural = "Stock Movements"
        ordering = ['-created']
    
    def __str__(self):
        return f"{self.movement_type}: {self.product} x {self.quantity}"
    
    @staticmethod
    def get_list_url():
        return reverse_lazy("inventory:movement_list")
    
    def get_absolute_url(self):
        return reverse_lazy("inventory:movement_detail", kwargs={"pk": str(self.pk)})


class StockTransfer(BaseModel):
    """Stock transfers between warehouses."""
    TRANSFER_STATUS = [
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('in_transit', 'In Transit'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transfer_number = models.CharField(max_length=50, unique=True)
    source_warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='outgoing_transfers')
    destination_warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='incoming_transfers')
    status = models.CharField(max_length=20, choices=TRANSFER_STATUS, default='draft')
    notes = models.TextField(blank=True, null=True)
    
    requested_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='requested_transfers')
    approved_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_transfers')
    approved_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    received_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='received_transfers')
    
    class Meta:
        verbose_name = "Stock Transfer"
        verbose_name_plural = "Stock Transfers"
        ordering = ['-created']
    
    def __str__(self):
        return f"{self.transfer_number}: {self.source_warehouse.code} → {self.destination_warehouse.code}"
    
    @staticmethod
    def get_list_url():
        return reverse_lazy("inventory:transfer_list")
    
    def get_absolute_url(self):
        return reverse_lazy("inventory:transfer_detail", kwargs={"pk": str(self.pk)})


class StockTransferItem(BaseModel):
    """Items in a stock transfer."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transfer = models.ForeignKey(StockTransfer, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('master.Product', on_delete=models.CASCADE)
    quantity_requested = models.IntegerField()
    quantity_shipped = models.IntegerField(default=0)
    quantity_received = models.IntegerField(default=0)
    lot = models.ForeignKey(LotBatch, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Transfer Item"
        verbose_name_plural = "Transfer Items"
    
    def __str__(self):
        return f"{self.transfer.transfer_number}: {self.product} x {self.quantity_requested}"


class ReorderRule(BaseModel):
    """Automatic reorder rules based on stock levels and sales velocity."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey('master.Product', on_delete=models.CASCADE, related_name='reorder_rules')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, null=True, blank=True, related_name='reorder_rules')
    reorder_point = models.IntegerField(help_text="Stock level that triggers reorder")
    reorder_quantity = models.IntegerField(help_text="Quantity to order")
    lead_time_days = models.IntegerField(default=7, help_text="Supplier lead time in days")
    safety_stock_days = models.IntegerField(default=3, help_text="Extra days of stock to keep as buffer")
    auto_reorder = models.BooleanField(default=False, help_text="Automatically create purchase orders")
    preferred_supplier = models.CharField(max_length=200, blank=True, null=True)
    last_reorder_date = models.DateField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Reorder Rule"
        verbose_name_plural = "Reorder Rules"
        unique_together = ['product', 'warehouse']
    
    def __str__(self):
        warehouse_name = self.warehouse.code if self.warehouse else 'All'
        return f"{self.product} @ {warehouse_name}: Reorder at {self.reorder_point}"


class InventoryAlert(BaseModel):
    """Inventory alerts for low stock, expiry, etc."""
    ALERT_TYPES = [
        ('low_stock', 'Low Stock'),
        ('out_of_stock', 'Out of Stock'),
        ('overstock', 'Overstock'),
        ('expiry_warning', 'Expiry Warning'),
        ('expired', 'Expired'),
        ('reorder', 'Reorder Needed'),
    ]
    
    ALERT_PRIORITIES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPES)
    priority = models.CharField(max_length=20, choices=ALERT_PRIORITIES, default='medium')
    product = models.ForeignKey('master.Product', on_delete=models.CASCADE, related_name='alerts')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, null=True, blank=True, related_name='alerts')
    message = models.TextField()
    current_stock = models.IntegerField(default=0)
    threshold = models.IntegerField(default=0)
    is_acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='acknowledged_alerts')
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Inventory Alert"
        verbose_name_plural = "Inventory Alerts"
        ordering = ['-created']
    
    def __str__(self):
        return f"{self.alert_type}: {self.product}"
    
    @staticmethod
    def get_list_url():
        return reverse_lazy("inventory:alert_list")
