"""
Wabis Signals - Auto-match orders to WhatsApp leads.
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='master.Order')
def match_order_to_wabis_lead(sender, instance, created, **kwargs):
    """Match orders to Wabis WhatsApp leads."""
    from .services import WabisConversionService
    
    try:
        order = instance
        confirmed_stages = ['Confirm', 'Booked', 'Delivered']
        
        if created or order.stage in confirmed_stages:
            if hasattr(order, 'wabis_converted_leads') and order.wabis_converted_leads.exists():
                return
            
            WabisConversionService.process_order_conversion(order)
            
    except Exception as e:
        logger.error(f"Error matching order to Wabis lead: {e}")
