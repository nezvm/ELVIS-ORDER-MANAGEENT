"""
WhatsApp Lead Conversion Signals

Signal handlers to automatically match WhatsApp leads to orders
when orders are created or confirmed.
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='master.Order')
def match_order_to_whatsapp_lead(sender, instance, created, **kwargs):
    """
    Signal handler to match orders to WhatsApp leads for conversion tracking.
    
    Triggered when:
    - A new order is created
    - An order status is changed to 'Confirm' or 'Booked'
    
    This enables automatic conversion tracking for WhatsApp leads.
    """
    from .services import LeadConversionService
    from .tasks import process_order_conversion
    
    try:
        order = instance
        
        # Only process for orders with confirmed status
        confirmed_stages = ['Confirm', 'Booked', 'Delivered']
        
        if created or order.stage in confirmed_stages:
            # Check if this order is already linked to a conversion
            if hasattr(order, 'converted_whatsapp_leads') and order.converted_whatsapp_leads.exists():
                logger.debug(f"Order {order.id} already has linked WhatsApp lead, skipping")
                return
            
            # Try to match in background task (async) if Celery is available
            try:
                process_order_conversion.delay(str(order.id))
                logger.debug(f"Queued order {order.id} for WhatsApp lead matching")
            except Exception:
                # Celery not available, do synchronous matching
                matched = LeadConversionService.process_order_conversion(order)
                if matched:
                    logger.info(f"Order {order.id} matched to WhatsApp lead (sync)")
                    
    except Exception as e:
        logger.error(f"Error in match_order_to_whatsapp_lead signal: {e}", exc_info=True)
