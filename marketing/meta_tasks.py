"""
Meta Marketing Celery Tasks

Scheduled tasks:
1. sync_meta_daily_insights - Pull yesterday + safety window (02:00 IST)
2. run_attribution_and_rollups - Run probabilistic attribution + compute rollups (02:15 IST)
3. send_capi_lead_event - Async send lead event
4. send_capi_purchase_event - Async send purchase event on lead->Won
5. retry_failed_capi_events - Retry failed CAPI events with backoff
"""

import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='marketing.sync_meta_daily_insights', max_retries=3)
def sync_meta_daily_insights(self):
    """
    Pull Meta Ads insights for yesterday + 7-day safety window.
    Scheduled daily at 02:00 IST.
    """
    from marketing.meta_services import MetaInsightsService

    try:
        service = MetaInsightsService()
        if not service.is_configured():
            logger.info("Meta Insights not configured, skipping sync")
            return {'status': 'skipped', 'reason': 'not configured'}

        yesterday = (timezone.now() - timedelta(days=1)).date()
        result = service.sync_daily_insights(target_date=yesterday, safety_days=7)

        logger.info(f"Meta Insights sync complete: {result}")
        return result

    except Exception as exc:
        logger.error(f"Meta Insights sync failed: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=300)


@shared_task(bind=True, name='marketing.run_attribution_and_rollups')
def run_attribution_and_rollups(self):
    """
    Run probabilistic attribution engine + compute daily rollups.
    Scheduled daily at 02:15 IST.
    """
    from marketing.meta_services import ProbabilisticAttributionEngine, MarketingRollupService

    results = {
        'attribution': {},
        'rollups': {},
        'errors': [],
    }

    yesterday = (timezone.now() - timedelta(days=1)).date()

    try:
        # Run attribution for yesterday + last 7 days (catch late data)
        for days_ago in range(8):
            target = yesterday - timedelta(days=days_ago)
            attr_result = ProbabilisticAttributionEngine.run_attribution(target)
            results['attribution'][str(target)] = attr_result
    except Exception as e:
        logger.error(f"Attribution engine error: {e}", exc_info=True)
        results['errors'].append(f"Attribution: {str(e)}")

    try:
        # Compute rollups for yesterday + last 7 days
        for days_ago in range(8):
            target = yesterday - timedelta(days=days_ago)
            rollup_result = MarketingRollupService.compute_rollup(target)
            results['rollups'][str(target)] = rollup_result
    except Exception as e:
        logger.error(f"Rollup computation error: {e}", exc_info=True)
        results['errors'].append(f"Rollup: {str(e)}")

    logger.info(f"Attribution & Rollups complete: {len(results['errors'])} errors")
    return results


@shared_task(bind=True, name='marketing.send_capi_lead_event', max_retries=3)
def send_capi_lead_event(self, lead_id):
    """
    Send Lead event to Meta CAPI.
    Triggered async when a new lead is created.
    """
    from marketing.models import Lead
    from marketing.meta_services import MetaCAPIService

    try:
        lead = Lead.objects.get(pk=lead_id, is_active=True)
        service = MetaCAPIService()

        if not service.is_configured():
            logger.debug("Meta CAPI not configured, skipping lead event")
            return {'status': 'skipped', 'reason': 'not configured'}

        success, response = service.send_lead_event(lead)
        return {'status': 'sent' if success else 'failed', 'response': response}

    except Lead.DoesNotExist:
        logger.warning(f"Lead {lead_id} not found for CAPI event")
        return {'status': 'error', 'reason': 'lead not found'}
    except Exception as exc:
        logger.error(f"CAPI lead event failed: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, name='marketing.send_capi_purchase_event', max_retries=3)
def send_capi_purchase_event(self, lead_id):
    """
    Send Purchase event to Meta CAPI.
    Triggered when a lead transitions to Won status.
    """
    from marketing.models import Lead
    from marketing.meta_services import MetaCAPIService

    try:
        lead = Lead.objects.get(pk=lead_id, is_active=True)

        if lead.conversion_status != 'won':
            return {'status': 'skipped', 'reason': 'lead not won'}

        if not lead.converted_order:
            return {'status': 'skipped', 'reason': 'no converted order'}

        service = MetaCAPIService()
        if not service.is_configured():
            return {'status': 'skipped', 'reason': 'not configured'}

        success, response = service.send_purchase_event(lead)
        return {'status': 'sent' if success else 'failed', 'response': response}

    except Lead.DoesNotExist:
        return {'status': 'error', 'reason': 'lead not found'}
    except Exception as exc:
        logger.error(f"CAPI purchase event failed: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(name='marketing.retry_failed_capi_events')
def retry_failed_capi_events():
    """
    Retry failed CAPI events with exponential backoff.
    """
    from marketing.meta_models import CapiEventLog
    from marketing.meta_services import MetaCAPIService

    service = MetaCAPIService()
    if not service.is_configured():
        return {'status': 'skipped'}

    failed_events = CapiEventLog.objects.filter(
        status='pending',
        retries__lt=3,
    ).order_by('created')[:50]

    sent, failed = 0, 0
    for event in failed_events:
        if event.lead:
            if event.event_name == 'Lead':
                success, _ = service.send_lead_event(event.lead)
            elif event.event_name == 'Purchase':
                success, _ = service.send_purchase_event(event.lead)
            else:
                continue

            if success:
                sent += 1
            else:
                failed += 1

    return {'sent': sent, 'failed': failed}


@shared_task(name='marketing.process_order_for_leads')
def process_order_for_leads(order_id):
    """Process an order for lead conversion matching."""
    from marketing.services import LeadService
    from master.models import Order

    try:
        order = Order.objects.get(pk=order_id)
        LeadService.process_order_conversion(order)
        LeadService.check_order_for_lead_conversion(order)
    except Order.DoesNotExist:
        logger.warning(f"Order {order_id} not found")
    except Exception as e:
        logger.error(f"Error processing order {order_id}: {e}", exc_info=True)
