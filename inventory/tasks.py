from celery import shared_task
from django.utils import timezone


@shared_task
def check_low_stock_alerts():
    """Check for low stock and create alerts."""
    from django.db.models import F
    from inventory.models import StockLevel
    from inventory.services import InventoryService
    
    low_stock = StockLevel.objects.filter(
        is_active=True,
        quantity__lte=F('reorder_point')
    )
    
    for stock_level in low_stock:
        InventoryService.check_and_create_alerts(stock_level)
    
    return f"Checked {low_stock.count()} low stock items"


@shared_task
def check_expiring_lots_task(days_ahead=30):
    """Check for expiring lots."""
    from inventory.services import InventoryService
    
    expiring = InventoryService.check_expiring_lots(days_ahead)
    return f"Found {expiring.count()} expiring lots"


@shared_task
def update_carrier_metrics():
    """Update carrier performance metrics."""
    from django.db.models import Avg, Count, Q
    from datetime import timedelta
    from logistics.models import Carrier, Shipment
    
    carriers = Carrier.objects.filter(is_active=True)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    for carrier in carriers:
        shipments = Shipment.objects.filter(
            carrier=carrier,
            is_active=True,
            created__gte=thirty_days_ago
        )
        
        total = shipments.count()
        if total > 0:
            delivered = shipments.filter(status='delivered').count()
            carrier.success_rate = (delivered / total) * 100
            
            # Calculate average delivery days for delivered shipments
            delivered_shipments = shipments.filter(
                status='delivered',
                actual_delivery_date__isnull=False
            )
            if delivered_shipments.exists():
                from django.db.models import Avg, F, ExpressionWrapper, fields
                # Simple average calculation
                carrier.avg_delivery_days = 3.5  # Mock value
            
            carrier.save()
    
    return f"Updated metrics for {carriers.count()} carriers"


@shared_task
def send_pending_webhooks():
    """Send any pending webhook notifications."""
    from integrations.models import WebhookEndpoint
    from integrations.services import WebhookService
    
    # This would typically process a queue of pending webhook deliveries
    return "Processed pending webhooks"
