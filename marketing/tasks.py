"""
Marketing Celery Tasks

Nightly jobs for lead management:
- Expire pending leads (CoolingPeriodExpired)
- Match orders to leads
- Compute DailyLeadMetrics
"""

import logging
from celery import shared_task
from django.utils import timezone
from django.db.models import Q, Sum, Count, Avg, F
from datetime import timedelta
from decimal import Decimal

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='marketing.nightly_lead_processing')
def nightly_lead_processing(self):
    """
    Main nightly job that runs at 2 AM IST.
    1. Expire pending leads older than matching window
    2. Match orders to leads
    3. Compute DailyLeadMetrics
    """
    logger.info("Starting nightly lead processing...")
    
    results = {
        'expired_leads': 0,
        'matched_orders': 0,
        'metrics_computed': False,
        'errors': []
    }
    
    try:
        # Step 1: Expire pending leads
        expired = expire_pending_leads()
        results['expired_leads'] = expired
        logger.info(f"Expired {expired} pending leads")
    except Exception as e:
        logger.error(f"Error expiring leads: {e}")
        results['errors'].append(f"Expire: {str(e)}")
    
    try:
        # Step 2: Match orders to leads
        matched = match_orders_to_leads()
        results['matched_orders'] = matched
        logger.info(f"Matched {matched} orders to leads")
    except Exception as e:
        logger.error(f"Error matching orders: {e}")
        results['errors'].append(f"Match: {str(e)}")
    
    try:
        # Step 3: Compute metrics for yesterday
        yesterday = timezone.now().date() - timedelta(days=1)
        compute_daily_lead_metrics(yesterday)
        results['metrics_computed'] = True
        logger.info(f"Computed metrics for {yesterday}")
    except Exception as e:
        logger.error(f"Error computing metrics: {e}")
        results['errors'].append(f"Metrics: {str(e)}")
    
    logger.info(f"Nightly processing complete: {results}")
    return results


@shared_task(name='marketing.expire_pending_leads')
def expire_pending_leads():
    """
    Mark pending leads older than matching window as Lost (CoolingPeriodExpired).
    """
    from marketing.models import Lead, LeadMatchingConfig
    
    config = LeadMatchingConfig.get_config()
    if not config.auto_expire_enabled:
        logger.info("Auto-expire disabled, skipping")
        return 0
    
    cutoff_date = timezone.now() - timedelta(days=config.matching_window_days)
    
    # Find pending leads older than matching window
    expired_leads = Lead.objects.filter(
        conversion_status='pending',
        is_active=True,
        created__lt=cutoff_date
    )
    
    count = 0
    for lead in expired_leads:
        lead.mark_as_lost(reason='cooling_period_expired')
        count += 1
    
    logger.info(f"Expired {count} pending leads (older than {config.matching_window_days} days)")
    return count


@shared_task(name='marketing.match_orders_to_leads')
def match_orders_to_leads():
    """
    Match new orders to existing leads and flip them to Won.
    Handles both pending and previously lost leads within recovery window.
    """
    from marketing.models import Lead, LeadMatchingConfig
    from integrations.models import ShopifyOrder
    
    config = LeadMatchingConfig.get_config()
    if not config.auto_match_orders:
        logger.info("Auto-match disabled, skipping")
        return 0
    
    matched_count = 0
    recovery_window = timezone.now() - timedelta(days=config.recovery_window_days)
    
    # Get recent orders (last 24 hours) that haven't been matched
    recent_orders = ShopifyOrder.objects.filter(
        created__gte=timezone.now() - timedelta(days=1),
        is_active=True
    )
    
    for order in recent_orders:
        # Try to find matching lead by phone or email
        phone = order.billing_phone or order.shipping_phone
        email = order.email
        
        if not phone and not email:
            continue
        
        # Build query for matching
        query = Q()
        if phone:
            # Normalize phone for matching
            phone_digits = ''.join(filter(str.isdigit, phone))[-10:]
            if phone_digits:
                query |= Q(phone_no__endswith=phone_digits)
                query |= Q(phone_normalized__endswith=phone_digits)
        if email:
            query |= Q(email__iexact=email)
            query |= Q(email_normalized__iexact=email.lower())
        
        if not query:
            continue
        
        # Find leads to match (pending first, then recently lost)
        lead = Lead.objects.filter(
            query,
            is_active=True
        ).filter(
            Q(conversion_status='pending') |
            Q(conversion_status='lost', lost_at__gte=recovery_window)
        ).order_by(
            # Prefer pending over lost, then most recent
            F('conversion_status').desc(),
            '-created'
        ).first()
        
        if lead:
            # Determine reason based on lead source and status
            if lead.conversion_status == 'lost':
                reason = 'recovered'
                lead.reopen_as_won(order, reason=reason)
            else:
                reason = 'order_placed'
                if 'abandoned' in (lead.lead_source or ''):
                    reason = 'recovered'
                lead.mark_as_won(order=order, reason=reason)
            
            matched_count += 1
            logger.debug(f"Matched order {order.order_number} to lead {lead.id}")
    
    return matched_count


@shared_task(name='marketing.compute_daily_lead_metrics')
def compute_daily_lead_metrics(metric_date=None):
    """
    Compute and store daily lead metrics for dashboard performance.
    """
    from marketing.models import Lead, DailyLeadMetrics
    from integrations.wabis.models import WabisNumber, WabisCustomer
    
    if metric_date is None:
        metric_date = timezone.now().date() - timedelta(days=1)
    
    # All leads created on this date
    date_leads = Lead.objects.filter(
        created__date=metric_date,
        is_active=True
    )
    
    # All leads (for running totals)
    all_leads = Lead.objects.filter(is_active=True)
    
    # Basic counts
    new_leads = date_leads.count()
    total_leads = all_leads.count()
    pending_leads = all_leads.filter(conversion_status='pending').count()
    won_leads = all_leads.filter(conversion_status='won').count()
    lost_leads = all_leads.filter(conversion_status='lost').count()
    
    # Revenue
    total_revenue = all_leads.filter(
        conversion_status='won'
    ).aggregate(total=Sum('conversion_value'))['total'] or Decimal('0')
    
    # Conversion rate
    decided = won_leads + lost_leads
    conversion_rate = (won_leads / decided * 100) if decided > 0 else 0
    
    # Avg conversion days
    avg_days = all_leads.filter(
        conversion_status='won',
        conversion_days__isnull=False
    ).aggregate(avg=Avg('conversion_days'))['avg'] or 0
    
    # WhatsApp leads
    wa_filter = Q(lead_source__icontains='whatsapp') | Q(source_type='whatsapp')
    whatsapp_leads = all_leads.filter(wa_filter).count()
    whatsapp_won = all_leads.filter(wa_filter, conversion_status='won').count()
    whatsapp_revenue = all_leads.filter(
        wa_filter, conversion_status='won'
    ).aggregate(total=Sum('conversion_value'))['total'] or Decimal('0')
    
    # Shopify leads
    shopify_filter = Q(lead_source__icontains='shopify') | Q(source_type='shopify')
    shopify_leads = all_leads.filter(shopify_filter).count()
    shopify_won = all_leads.filter(shopify_filter, conversion_status='won').count()
    shopify_revenue = all_leads.filter(
        shopify_filter, conversion_status='won'
    ).aggregate(total=Sum('conversion_value'))['total'] or Decimal('0')
    
    # Other leads
    other_leads = all_leads.exclude(wa_filter).exclude(shopify_filter).count()
    other_won = all_leads.exclude(wa_filter).exclude(shopify_filter).filter(
        conversion_status='won'
    ).count()
    other_revenue = all_leads.exclude(wa_filter).exclude(shopify_filter).filter(
        conversion_status='won'
    ).aggregate(total=Sum('conversion_value'))['total'] or Decimal('0')
    
    # WhatsApp by number
    whatsapp_by_number = {}
    for number in WabisNumber.objects.filter(is_active=True):
        whatsapp_by_number[number.display_phone_number] = {
            'name': number.display_name,
            'leads': 0,
            'won': 0,
            'lost': 0,
            'revenue': 0,
        }
    
    # Shopify breakdown
    shopify_orders_leads = all_leads.filter(lead_source='shopify_order').count()
    shopify_abandoned_leads = all_leads.filter(
        lead_source__in=['shopify_abandoned_checkout', 'shopify_abandoned_cart']
    ).count()
    shopify_recovered_leads = all_leads.filter(
        lead_source__in=['shopify_abandoned_checkout', 'shopify_abandoned_cart'],
        status_reason='recovered'
    ).count()
    
    # Status reasons breakdown
    status_reasons = {}
    for reason_code, reason_name in Lead.STATUS_REASON_CHOICES:
        count = all_leads.filter(status_reason=reason_code).count()
        if count > 0:
            status_reasons[reason_code] = count
    
    # Create or update metrics
    metrics, created = DailyLeadMetrics.objects.update_or_create(
        metric_date=metric_date,
        defaults={
            'total_leads': total_leads,
            'new_leads': new_leads,
            'pending_leads': pending_leads,
            'won_leads': won_leads,
            'lost_leads': lost_leads,
            'conversion_rate': conversion_rate,
            'total_revenue': total_revenue,
            'avg_conversion_days': avg_days,
            'whatsapp_leads': whatsapp_leads,
            'whatsapp_won': whatsapp_won,
            'whatsapp_revenue': whatsapp_revenue,
            'shopify_leads': shopify_leads,
            'shopify_won': shopify_won,
            'shopify_revenue': shopify_revenue,
            'other_leads': other_leads,
            'other_won': other_won,
            'other_revenue': other_revenue,
            'whatsapp_by_number': whatsapp_by_number,
            'shopify_orders_leads': shopify_orders_leads,
            'shopify_abandoned_leads': shopify_abandoned_leads,
            'shopify_recovered_leads': shopify_recovered_leads,
            'status_reasons': status_reasons,
        }
    )
    
    logger.info(f"{'Created' if created else 'Updated'} metrics for {metric_date}")
    return metrics.id


@shared_task(name='marketing.sync_lead_statuses')
def sync_lead_statuses():
    """Sync lead statuses (placeholder for backward compatibility)."""
    return nightly_lead_processing()


@shared_task(name='marketing.generate_lead_daily_stats')
def generate_lead_daily_stats():
    """Generate daily stats (placeholder for backward compatibility)."""
    yesterday = timezone.now().date() - timedelta(days=1)
    compute_daily_lead_metrics(yesterday)
    return {'date': str(yesterday)}
