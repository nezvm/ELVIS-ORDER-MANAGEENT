"""
WhatsApp Lead Attribution & Conversion - Celery Tasks

Scheduled tasks for:
1. Daily lead sync at 02:00 IST - Update lead statuses, send conversions
2. Generate daily reports - Aggregate metrics per WhatsApp number
3. Sync ad spend from Meta Ads API
"""

import logging
from datetime import datetime, timedelta
from celery import shared_task
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='whatsapp.sync_lead_statuses')
def sync_lead_statuses(self):
    """
    Daily task to sync lead statuses.
    
    Runs at 02:00 IST (configured via Celery Beat).
    
    Actions:
    1. Expire pending leads past matching period -> Lost
    2. Send pending conversions to Meta CAPI
    3. Check for orders that matched lost leads (late conversion)
    """
    from integrations.whatsapp.services import LeadConversionService
    
    logger.info("Starting daily lead status sync...")
    
    try:
        # 1. Expire pending leads past matching period
        expired_count = LeadConversionService.expire_pending_leads()
        logger.info(f"Expired {expired_count} pending leads (marked as Lost)")
        
        # 2. Send pending conversions to Meta CAPI
        sent_count, failed_count = LeadConversionService.send_pending_conversions()
        logger.info(f"Sent {sent_count} conversions to Meta CAPI, {failed_count} failed")
        
        # 3. Check for late conversions (orders that matched previously lost leads)
        late_conversions = check_late_conversions()
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


@shared_task(bind=True, name='whatsapp.generate_daily_reports')
def generate_daily_reports(self, report_date_str: str = None):
    """
    Generate daily lead reports for all WhatsApp numbers.
    
    If report_date_str is not provided, generates for yesterday.
    
    Args:
        report_date_str: Date string in YYYY-MM-DD format (optional)
    """
    from integrations.whatsapp.services import DailyReportService
    
    if report_date_str:
        report_date = datetime.strptime(report_date_str, '%Y-%m-%d').date()
    else:
        # Default to yesterday
        report_date = (timezone.now() - timedelta(days=1)).date()
    
    logger.info(f"Generating daily reports for {report_date}...")
    
    try:
        reports = DailyReportService.generate_daily_report(report_date)
        logger.info(f"Generated {len(reports)} daily reports")
        
        return {
            'report_date': str(report_date),
            'reports_generated': len(reports),
        }
        
    except Exception as e:
        logger.error(f"Daily report generation failed: {e}", exc_info=True)
        raise


@shared_task(bind=True, name='whatsapp.sync_ad_spend')
def sync_ad_spend(self, date_str: str = None):
    """
    Sync ad spend data from Meta Ads API.
    
    Args:
        date_str: Date string in YYYY-MM-DD format (optional, defaults to yesterday)
    """
    from integrations.whatsapp.services import MetaAdsService
    from integrations.whatsapp.models import DailyLeadReport
    
    if date_str:
        sync_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        sync_date = (timezone.now() - timedelta(days=1)).date()
    
    logger.info(f"Syncing ad spend for {sync_date}...")
    
    ads_service = MetaAdsService()
    
    if not ads_service.is_configured():
        logger.warning("Meta Ads API not configured, skipping ad spend sync")
        return {'status': 'skipped', 'reason': 'Meta Ads API not configured'}
    
    try:
        # Get daily spend data
        date_start = timezone.make_aware(
            datetime.combine(sync_date, datetime.min.time())
        )
        result = ads_service.get_daily_spend(date_start)
        
        if 'error' in result:
            return {'status': 'error', 'error': result['error']}
        
        # Update daily reports with spend data
        spend_data = result.get('data', [])
        
        # Calculate total spend
        from decimal import Decimal
        total_spend = sum(Decimal(row.get('spend', '0')) for row in spend_data)
        
        # Update aggregate report
        try:
            report = DailyLeadReport.objects.get(
                report_date=sync_date,
                phone_number_id=None,
                campaign_id=None
            )
            report.ad_spend = total_spend
            report.calculate_roas()
            report.save()
        except DailyLeadReport.DoesNotExist:
            pass
        
        # Update campaign-level reports
        for row in spend_data:
            campaign_id = row.get('campaign_id')
            spend = Decimal(row.get('spend', '0'))
            
            if campaign_id:
                report, created = DailyLeadReport.objects.get_or_create(
                    report_date=sync_date,
                    campaign_id=campaign_id,
                    defaults={'ad_spend': spend}
                )
                if not created:
                    report.ad_spend = spend
                    report.calculate_roas()
                    report.save()
        
        logger.info(f"Synced ad spend: {total_spend} for {len(spend_data)} campaigns")
        
        return {
            'status': 'success',
            'date': str(sync_date),
            'total_spend': str(total_spend),
            'campaigns': len(spend_data),
        }
        
    except Exception as e:
        logger.error(f"Ad spend sync failed: {e}", exc_info=True)
        raise


@shared_task(bind=True, name='whatsapp.process_order_conversion')
def process_order_conversion(self, order_id: str):
    """
    Process a single order for conversion matching.
    
    Called when an order is placed/confirmed.
    
    Args:
        order_id: UUID of the order
    """
    from master.models import Order
    from integrations.whatsapp.services import LeadConversionService
    
    logger.info(f"Processing order {order_id} for conversion...")
    
    try:
        order = Order.objects.get(id=order_id)
        matched = LeadConversionService.process_order_conversion(order)
        
        if matched:
            logger.info(f"Order {order_id} matched to WhatsApp lead")
        else:
            logger.debug(f"No WhatsApp lead found for order {order_id}")
        
        return {'order_id': order_id, 'matched': matched}
        
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found")
        return {'order_id': order_id, 'error': 'Order not found'}
    except Exception as e:
        logger.error(f"Order conversion processing failed: {e}", exc_info=True)
        raise


@shared_task(bind=True, name='whatsapp.send_conversion_event')
def send_conversion_event(self, customer_id: str, order_id: str):
    """
    Send a conversion event to Meta CAPI.
    
    Args:
        customer_id: UUID of WhatsAppCustomer
        order_id: UUID of Order
    """
    from integrations.whatsapp.models import WhatsAppCustomer
    from master.models import Order
    from integrations.whatsapp.services import MetaCAPIService
    
    logger.info(f"Sending conversion event for customer {customer_id}, order {order_id}")
    
    try:
        customer = WhatsAppCustomer.objects.get(id=customer_id)
        order = Order.objects.get(id=order_id)
        
        capi_service = MetaCAPIService()
        success, response = capi_service.send_purchase_event(customer, order)
        
        if success:
            customer.conversion_sent = True
            customer.conversion_sent_at = timezone.now()
            customer.save(update_fields=['conversion_sent', 'conversion_sent_at'])
            logger.info(f"Conversion event sent successfully")
        else:
            logger.error(f"Failed to send conversion event: {response}")
        
        return {'success': success, 'response': response}
        
    except (WhatsAppCustomer.DoesNotExist, Order.DoesNotExist) as e:
        logger.error(f"Customer or Order not found: {e}")
        return {'success': False, 'error': str(e)}
    except Exception as e:
        logger.error(f"Conversion event send failed: {e}", exc_info=True)
        raise


def check_late_conversions() -> int:
    """
    Check for orders that might have converted previously lost leads.
    
    If a lead was marked Lost but later an order came in with matching phone,
    we can retroactively mark it as Won.
    """
    from integrations.whatsapp.models import WhatsAppCustomer
    from master.models import Order
    from django.db.models import Q
    
    # Get recently lost leads (last 30 days)
    cutoff = timezone.now() - timedelta(days=30)
    lost_leads = WhatsAppCustomer.objects.filter(
        lead_status='lost',
        lost_at__gte=cutoff,
        is_active=True
    )
    
    late_conversions = 0
    
    for lead in lost_leads:
        # Check if there's an order for this customer
        phone = lead.wa_id
        phone_variants = [
            phone,
            f"+{phone}",
            f"91{phone}" if len(phone) == 10 else phone,
            phone[2:] if phone.startswith('91') and len(phone) == 12 else phone,
        ]
        
        # Find orders with matching phone after lead was lost
        matching_order = Order.objects.filter(
            Q(customer__phone_no__in=phone_variants) |
            Q(phone__in=phone_variants) |
            Q(mobile__in=phone_variants),
            created__gte=lead.lost_at,
            stage__in=['Confirm', 'Booked', 'Delivered']
        ).order_by('created').first()
        
        if matching_order:
            # Revert to Won
            lead.lead_status = 'won'
            lead.won_at = matching_order.created
            lead.converted_order = matching_order
            lead.conversion_value = matching_order.total_amount
            lead.lost_at = None
            lead.conversion_sent = False  # Will be sent on next CAPI sync
            lead.save()
            
            late_conversions += 1
            logger.info(f"Late conversion found: Lead {lead.id} matched to Order {matching_order.id}")
    
    return late_conversions


# =============================================================================
# CELERY BEAT SCHEDULE CONFIGURATION
# =============================================================================
# This should be added to settings.py or a separate celery_config.py

"""
Add to settings.py:

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Daily lead status sync at 02:00 IST (20:30 UTC)
    'sync-lead-statuses-daily': {
        'task': 'whatsapp.sync_lead_statuses',
        'schedule': crontab(hour=20, minute=30),  # 02:00 IST = 20:30 UTC previous day
    },
    # Generate daily reports at 02:15 IST
    'generate-daily-reports': {
        'task': 'whatsapp.generate_daily_reports',
        'schedule': crontab(hour=20, minute=45),  # 02:15 IST = 20:45 UTC
    },
    # Sync ad spend at 02:30 IST
    'sync-ad-spend-daily': {
        'task': 'whatsapp.sync_ad_spend',
        'schedule': crontab(hour=21, minute=0),  # 02:30 IST = 21:00 UTC
    },
}
"""
