"""
Marketing Signals - Auto-match leads to orders for conversion tracking.
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='master.Order')
def match_order_to_leads(sender, instance, created, **kwargs):
    """
    Signal handler to match orders to leads for conversion tracking.
    
    Triggered when:
    - A new order is created
    - An order status is changed to 'Confirm', 'Booked', or 'Delivered'
    
    This enables automatic conversion tracking for ALL lead sources.
    """
    from .tasks import process_order_for_leads
    from .services import LeadService
    
    try:
        order = instance
        
        # Only process for confirmed orders
        confirmed_stages = ['Confirm', 'Booked', 'Delivered']
        
        if created or order.stage in confirmed_stages:
            # Check if already linked
            if hasattr(order, 'converted_leads') and order.converted_leads.exists():
                logger.debug(f"Order {order.id} already has linked leads, skipping")
                return
            
            # Try async first
            try:
                process_order_for_leads.delay(str(order.id))
                logger.debug(f"Queued order {order.id} for lead matching")
            except Exception:
                # Celery not available, do sync
                LeadService.process_order_conversion(order)
                LeadService.check_order_for_lead_conversion(order)
                    
    except Exception as e:
        logger.error(f"Error in match_order_to_leads signal: {e}", exc_info=True)
