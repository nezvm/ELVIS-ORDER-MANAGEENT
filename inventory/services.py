from django.db.models import Sum, F, Q
from django.utils import timezone
from datetime import timedelta
from .models import StockLevel, StockMovement, InventoryAlert, LotBatch
from master.models import Product, OrderItem


class InventoryService:
    """Service for inventory operations."""
    
    @staticmethod
    def get_available_stock(product, warehouse=None):
        """Get available stock for a product."""
        qs = StockLevel.objects.filter(product=product, is_active=True)
        if warehouse:
            qs = qs.filter(warehouse=warehouse)
        
        total = qs.aggregate(
            total_qty=Sum('quantity'),
            total_reserved=Sum('reserved_quantity')
        )
        
        qty = total['total_qty'] or 0
        reserved = total['total_reserved'] or 0
        
        return max(0, qty - reserved)
    
    @staticmethod
    def reserve_stock(product, warehouse, quantity, reference_type=None, reference_id=None):
        """Reserve stock for an order."""
        stock_level = StockLevel.objects.filter(
            product=product, warehouse=warehouse, is_active=True
        ).first()
        
        if not stock_level:
            return False, "Stock record not found"
        
        if stock_level.available_quantity < quantity:
            return False, f"Insufficient stock. Available: {stock_level.available_quantity}"
        
        stock_level.reserved_quantity += quantity
        stock_level.save()
        
        return True, "Stock reserved successfully"
    
    @staticmethod
    def release_reservation(product, warehouse, quantity):
        """Release reserved stock."""
        stock_level = StockLevel.objects.filter(
            product=product, warehouse=warehouse, is_active=True
        ).first()
        
        if stock_level:
            stock_level.reserved_quantity = max(0, stock_level.reserved_quantity - quantity)
            stock_level.save()
            return True
        return False
    
    @staticmethod
    def deduct_stock(product, warehouse, quantity, reference_type=None, reference_id=None, user=None):
        """Deduct stock (e.g., when order is shipped)."""
        stock_level = StockLevel.objects.filter(
            product=product, warehouse=warehouse, is_active=True
        ).first()
        
        if not stock_level:
            return False, "Stock record not found"
        
        stock_before = stock_level.quantity
        
        # Check if enough stock
        if stock_level.quantity < quantity:
            return False, f"Insufficient stock. Available: {stock_level.quantity}"
        
        # Deduct stock
        stock_level.quantity -= quantity
        
        # Also release reservation if any
        if stock_level.reserved_quantity >= quantity:
            stock_level.reserved_quantity -= quantity
        
        stock_level.save()
        
        # Create movement record
        StockMovement.objects.create(
            product=product,
            warehouse=warehouse,
            movement_type='sale',
            quantity=-quantity,
            reference_type=reference_type,
            reference_id=reference_id,
            performed_by=user,
            stock_before=stock_before,
            stock_after=stock_level.quantity
        )
        
        # Check for low stock alert
        InventoryService.check_and_create_alerts(stock_level)
        
        return True, "Stock deducted successfully"
    
    @staticmethod
    def add_stock(product, warehouse, quantity, movement_type='purchase', reference_type=None, 
                  reference_id=None, unit_cost=0, user=None, lot=None):
        """Add stock (e.g., from purchase or return)."""
        stock_level, created = StockLevel.objects.get_or_create(
            product=product, warehouse=warehouse,
            defaults={'quantity': 0, 'is_active': True}
        )
        
        stock_before = stock_level.quantity
        stock_level.quantity += quantity
        stock_level.save()
        
        # Create movement record
        StockMovement.objects.create(
            product=product,
            warehouse=warehouse,
            movement_type=movement_type,
            quantity=quantity,
            reference_type=reference_type,
            reference_id=reference_id,
            unit_cost=unit_cost,
            performed_by=user,
            lot=lot,
            stock_before=stock_before,
            stock_after=stock_level.quantity
        )
        
        return True, "Stock added successfully"
    
    @staticmethod
    def adjust_stock(product, warehouse, new_quantity, reason=None, user=None):
        """Adjust stock to a specific quantity."""
        stock_level, created = StockLevel.objects.get_or_create(
            product=product, warehouse=warehouse,
            defaults={'quantity': 0, 'is_active': True}
        )
        
        stock_before = stock_level.quantity
        difference = new_quantity - stock_before
        
        movement_type = 'adjustment_in' if difference > 0 else 'adjustment_out'
        
        stock_level.quantity = new_quantity
        stock_level.last_counted_at = timezone.now()
        stock_level.last_counted_by = user
        stock_level.save()
        
        # Create movement record
        StockMovement.objects.create(
            product=product,
            warehouse=warehouse,
            movement_type=movement_type,
            quantity=difference,
            reference_type='adjustment',
            notes=reason,
            performed_by=user,
            stock_before=stock_before,
            stock_after=new_quantity
        )
        
        # Check for alerts
        InventoryService.check_and_create_alerts(stock_level)
        
        return True, f"Stock adjusted from {stock_before} to {new_quantity}"
    
    @staticmethod
    def check_and_create_alerts(stock_level):
        """Check stock level and create alerts if needed."""
        product = stock_level.product
        warehouse = stock_level.warehouse
        
        # Out of stock alert
        if stock_level.available_quantity <= 0:
            InventoryAlert.objects.get_or_create(
                product=product,
                warehouse=warehouse,
                alert_type='out_of_stock',
                is_acknowledged=False,
                defaults={
                    'priority': 'critical',
                    'message': f'{product} is out of stock at {warehouse.name}',
                    'current_stock': stock_level.quantity,
                    'threshold': 0
                }
            )
        # Low stock alert
        elif stock_level.is_low_stock:
            InventoryAlert.objects.get_or_create(
                product=product,
                warehouse=warehouse,
                alert_type='low_stock',
                is_acknowledged=False,
                defaults={
                    'priority': 'high',
                    'message': f'{product} is running low at {warehouse.name}. Current: {stock_level.quantity}, Reorder point: {stock_level.reorder_point}',
                    'current_stock': stock_level.quantity,
                    'threshold': stock_level.reorder_point
                }
            )
    
    @staticmethod
    def get_sales_velocity(product, days=30):
        """Calculate average daily sales for a product."""
        from_date = timezone.now().date() - timedelta(days=days)
        
        total_sold = OrderItem.objects.filter(
            product=product,
            order__is_active=True,
            order__created__date__gte=from_date
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        return total_sold / days if days > 0 else 0
    
    @staticmethod
    def calculate_reorder_recommendation(product, warehouse=None):
        """Calculate recommended reorder quantity based on sales velocity."""
        velocity = InventoryService.get_sales_velocity(product)
        
        # Default lead time of 7 days + 3 days safety stock
        lead_time_days = 7
        safety_stock_days = 3
        
        recommended_reorder_point = int(velocity * (lead_time_days + safety_stock_days))
        recommended_reorder_qty = int(velocity * 30)  # 30 days of stock
        
        return {
            'daily_velocity': round(velocity, 2),
            'recommended_reorder_point': recommended_reorder_point,
            'recommended_reorder_qty': recommended_reorder_qty
        }
    
    @staticmethod
    def check_expiring_lots(days_ahead=30):
        """Find lots expiring within specified days."""
        expiry_date = timezone.now().date() + timedelta(days=days_ahead)
        
        expiring = LotBatch.objects.filter(
            is_active=True,
            expiry_date__lte=expiry_date,
            expiry_date__gte=timezone.now().date(),
            quantity__gt=0
        ).select_related('product', 'warehouse')
        
        # Create alerts for expiring lots
        for lot in expiring:
            days_to_expiry = (lot.expiry_date - timezone.now().date()).days
            priority = 'critical' if days_to_expiry <= 7 else 'high' if days_to_expiry <= 14 else 'medium'
            
            InventoryAlert.objects.get_or_create(
                product=lot.product,
                warehouse=lot.warehouse,
                alert_type='expiry_warning',
                is_acknowledged=False,
                defaults={
                    'priority': priority,
                    'message': f'Lot {lot.lot_number} of {lot.product} expires on {lot.expiry_date} ({days_to_expiry} days)',
                    'current_stock': lot.quantity,
                    'threshold': days_to_expiry
                }
            )
        
        return expiring
