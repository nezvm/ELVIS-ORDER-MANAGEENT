"""
Universal Lead Sync & Conversion Tracking - Celery Tasks

Scheduled tasks for ALL leads (not just WhatsApp):
1. Daily lead sync at 02:00 IST - Update lead statuses, send conversions
2. Generate daily reports - Aggregate metrics
3. Check for late conversions
"""

import logging
from datetime import datetime, timedelta
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='marketing.sync_lead_statuses')
def sync_lead_statuses(self):
    """
    Daily task to sync lead statuses for ALL leads.
    
    Runs at 02:00 IST (configured via Celery Beat).
    
    Actions:
    1. Expire pending leads past matching period → Lost
    2. Send pending conversions to Meta CAPI (for ad leads)
    3. Check for late conversions
    """
    from marketing.services import LeadService
    
    logger.info("Starting daily lead status sync (all leads)...")
    
    try:
        # 1. Expire pending leads past matching period
        expired_count = LeadService.expire_pending_leads()
        logger.info(f"Expired {expired_count} pending leads (marked as Lost)")
        
        # 2. Send pending conversions to Meta CAPI
        sent_count, failed_count = LeadService.send_pending_meta_conversions()
        logger.info(f"Sent {sent_count} conversions to Meta CAPI, {failed_count} failed")
        
        # 3. Check for late conversions
        late_conversions = LeadService.check_late_conversions()
        logger.info(f"Found {late_conversions} late conversions")
        
        return {
            'expired_leads': expired_count,
            'conversions_sent': sent_count,
            'conversions_failed': failed_count,
            'late_conversions': late_conversions,
        }
        
    except Exception as e:
        logger.error(f"Lead status sync failed: {e}", exc_info=True)
        raise


@shared_task(bind=True, name='marketing.process_order_for_leads')
def process_order_for_leads(self, order_id: str):
    """
    Process an order for lead conversion matching.
    Called when an order is created/confirmed.
    
    Args:
        order_id: UUID of the order
    """
    from master.models import Order
    from marketing.services import LeadService
    
    logger.info(f"Processing order {order_id} for lead conversion...")
    
    try:
        order = Order.objects.get(id=order_id)
        
        # Try new conversion tracking
        matched = LeadService.process_order_conversion(order)
        
        # Also try legacy abandoned checkout tracking
        converted_abandoned = LeadService.check_order_for_lead_conversion(order)
        
        result = {
            'order_id': order_id,
            'matched_lead': matched,
            'converted_abandoned': converted_abandoned
        }
        
        if matched or converted_abandoned:
            logger.info(f"Order {order_id} matched to leads")
        
        return result
        
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found")
        return {'order_id': order_id, 'error': 'Order not found'}
    except Exception as e:
        logger.error(f"Order conversion processing failed: {e}", exc_info=True)
        raise


@shared_task(bind=True, name='marketing.generate_lead_daily_stats')
def generate_lead_daily_stats(self, date_str: str = None):
    """
    Generate daily lead statistics.
    
    Args:
        date_str: Date string in YYYY-MM-DD format (optional, defaults to yesterday)
    """
    from marketing.services import LeadService
    from marketing.models import Lead
    from django.db.models import Count, Sum, Q
    
    if date_str:
        report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        report_date = (timezone.now() - timedelta(days=1)).date()
    
    logger.info(f"Generating daily lead stats for {report_date}...")
    
    try:
        date_start = timezone.make_aware(datetime.combine(report_date, datetime.min.time()))
        date_end = timezone.make_aware(datetime.combine(report_date, datetime.max.time()))
        
        # Leads captured that day
        leads = Lead.objects.filter(
            captured_at__range=(date_start, date_end),
            is_active=True
        )
        
        stats = {
            'date': str(report_date),
            'total_leads': leads.count(),
            'by_source': list(leads.values('lead_source').annotate(count=Count('id')).order_by('-count')),
            'by_type': list(leads.values('source_type').annotate(count=Count('id'))),
            'conversions': Lead.objects.filter(
                won_at__range=(date_start, date_end),
                is_active=True
            ).count(),
            'revenue': Lead.objects.filter(
                won_at__range=(date_start, date_end),
                is_active=True
            ).aggregate(total=Sum('conversion_value'))['total'] or 0,
            'expired': Lead.objects.filter(
                lost_at__range=(date_start, date_end),
                is_active=True
            ).count(),
        }
        
        logger.info(f"Daily stats for {report_date}: {stats['total_leads']} leads, {stats['conversions']} conversions")
        
        return stats
        
    except Exception as e:
        logger.error(f"Daily stats generation failed: {e}", exc_info=True)
        raise


# =============================================================================
# CELERY BEAT SCHEDULE (add to settings.py if not present)
# =============================================================================
"""
Add/update in settings.py CELERY_BEAT_SCHEDULE:

CELERY_BEAT_SCHEDULE = {
    # Universal lead sync at 02:00 IST (20:30 UTC)
    'sync-all-lead-statuses-daily': {
        'task': 'marketing.sync_lead_statuses',
        'schedule': crontab(hour=20, minute=30),
    },
    # Daily stats at 02:15 IST
    'generate-lead-daily-stats': {
        'task': 'marketing.generate_lead_daily_stats',
        'schedule': crontab(hour=20, minute=45),
    },
}
"""
