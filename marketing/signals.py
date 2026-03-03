"""
Marketing Signals - Auto-match leads to orders for conversion tracking.
CAPI integration: Fire Lead/Purchase events to Meta.
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
    from .meta_tasks import process_order_for_leads
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


@receiver(post_save, sender='marketing.Lead')
def fire_capi_lead_event(sender, instance, created, **kwargs):
    """
    Send Lead event to Meta CAPI when a new lead is created.
    Also send Purchase event when lead transitions to Won.
    """
    if not instance.is_active:
        return

    # On creation: send Lead event
    if created and not instance.lead_event_sent_to_meta:
        try:
            from .meta_tasks import send_capi_lead_event
            send_capi_lead_event.delay(str(instance.id))
            logger.debug(f"Queued CAPI Lead event for lead {instance.id}")
        except Exception:
            # Celery not available - attempt sync
            try:
                from .meta_services import MetaCAPIService
                service = MetaCAPIService()
                if service.is_configured():
                    service.send_lead_event(instance)
            except Exception as e:
                logger.warning(f"CAPI Lead event sync failed: {e}")

    # On Won status: send Purchase event
    if not created and instance.conversion_status == 'won' and not instance.conversion_sent_to_meta:
        if instance.converted_order:
            try:
                from .meta_tasks import send_capi_purchase_event
                send_capi_purchase_event.delay(str(instance.id))
                logger.debug(f"Queued CAPI Purchase event for lead {instance.id}")
            except Exception:
                try:
                    from .meta_services import MetaCAPIService
                    service = MetaCAPIService()
                    if service.is_configured():
                        service.send_purchase_event(instance)
                except Exception as e:
                    logger.warning(f"CAPI Purchase event sync failed: {e}")
