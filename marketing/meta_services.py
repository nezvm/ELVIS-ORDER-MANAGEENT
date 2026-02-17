"""
Meta CAPI & Marketing Measurement Services

Consolidated services for:
1. MetaCAPIService - Send Lead/Purchase events to Meta Conversions API
2. MetaInsightsService - Pull daily insights from Meta Marketing API
3. ProbabilisticAttributionEngine - Compute ads share and assign attribution
4. MarketingRollupService - Compute daily marketing rollups
"""

import hashlib
import json
import logging
import requests
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Optional, Dict, Any, List, Tuple

from django.conf import settings
from django.db import transaction
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone

logger = logging.getLogger(__name__)


# =============================================================================
# META CAPI SERVICE (Unified)
# =============================================================================

class MetaCAPIService:
    """
    Sends Lead and Purchase events to Meta Conversions API.
    Uses MetaIntegrationConfig from meta_models and logs to CapiEventLog.
    """

    API_VERSION = 'v21.0'
    BASE_URL = 'https://graph.facebook.com'

    def __init__(self, config=None):
        from .meta_models import MetaIntegrationConfig
        if config is None:
            config = MetaIntegrationConfig.get_config()
        self.config = config

    def is_configured(self) -> bool:
        if not self.config:
            return False
        return bool(self.config.capi_endpoint_id and self.config.access_token)

    @staticmethod
    def hash_value(value: str) -> Optional[str]:
        if not value:
            return None
        return hashlib.sha256(value.lower().strip().encode('utf-8')).hexdigest()

    def _build_user_data(self, lead) -> dict:
        """Build hashed user_data from a Lead object."""
        user_data = {}
        phone = lead.phone_normalized or lead.phone_no
        if phone:
            phone_clean = phone.replace('+', '').replace(' ', '').replace('-', '')
            if not phone_clean.startswith('91') and len(phone_clean) == 10:
                phone_clean = '91' + phone_clean
            user_data['ph'] = [self.hash_value(phone_clean)]

        email = lead.email_normalized or lead.email
        if email:
            user_data['em'] = [self.hash_value(email)]

        if lead.name:
            parts = lead.name.strip().split(' ', 1)
            user_data['fn'] = [self.hash_value(parts[0])]
            if len(parts) > 1:
                user_data['ln'] = [self.hash_value(parts[1])]

        if lead.meta_fbclid:
            user_data['fbc'] = lead.meta_fbclid

        return user_data

    def send_lead_event(self, lead) -> Tuple[bool, dict]:
        """
        Send a Lead event to Meta CAPI.
        Idempotent via event_id = sha256('lead:' + lead.id)
        """
        from .meta_models import CapiEventLog

        if not self.is_configured():
            return False, {'error': 'Meta CAPI not configured'}

        if not self.config.send_lead_events:
            return False, {'error': 'Lead events disabled in config'}

        event_id = CapiEventLog.generate_event_id('lead', str(lead.id))

        # Check idempotency
        existing = CapiEventLog.objects.filter(event_id=event_id, status='sent').first()
        if existing:
            return True, {'message': 'Already sent', 'event_id': event_id}

        user_data = self._build_user_data(lead)
        if not user_data.get('ph') and not user_data.get('em'):
            return False, {'error': 'No user identifiers (phone or email)'}

        event_time = lead.captured_at or lead.created
        event_data = {
            'event_name': 'Lead',
            'event_time': int(event_time.timestamp()),
            'event_id': event_id,
            'action_source': 'website',
            'user_data': user_data,
            'custom_data': {
                'lead_id': str(lead.id),
                'source': lead.lead_source or 'unknown',
            },
        }

        # Create or get log entry
        log_entry, created = CapiEventLog.objects.get_or_create(
            event_id=event_id,
            defaults={
                'event_name': 'Lead',
                'event_time': event_time,
                'lead': lead,
                'source': 'whatsapp' if 'whatsapp' in (lead.lead_source or '') else ('shopify' if 'shopify' in (lead.lead_source or '') else 'other'),
                'phone_hash_used': bool(user_data.get('ph')),
                'email_hash_used': bool(user_data.get('em')),
                'custom_data_json': event_data.get('custom_data', {}),
            }
        )

        return self._send_event(event_data, log_entry)

    def send_purchase_event(self, lead) -> Tuple[bool, dict]:
        """
        Send a Purchase event to Meta CAPI.
        Only when lead is Won and has a converted_order.
        Idempotent via event_id = sha256('purchase:' + order.id)
        """
        from .meta_models import CapiEventLog

        if not self.is_configured():
            return False, {'error': 'Meta CAPI not configured'}

        if not self.config.send_purchase_events:
            return False, {'error': 'Purchase events disabled in config'}

        order = lead.converted_order
        if not order:
            return False, {'error': 'No converted order linked'}

        event_id = CapiEventLog.generate_event_id('purchase', str(order.id))

        existing = CapiEventLog.objects.filter(event_id=event_id, status='sent').first()
        if existing:
            return True, {'message': 'Already sent', 'event_id': event_id}

        user_data = self._build_user_data(lead)
        if not user_data.get('ph') and not user_data.get('em'):
            return False, {'error': 'No user identifiers'}

        event_time = lead.won_at or timezone.now()
        value = float(lead.conversion_value or order.total_amount or 0)

        event_data = {
            'event_name': 'Purchase',
            'event_time': int(event_time.timestamp()),
            'event_id': event_id,
            'action_source': 'website',
            'user_data': user_data,
            'custom_data': {
                'value': value,
                'currency': 'INR',
                'content_type': 'product',
                'order_id': str(order.id),
                'lead_id': str(lead.id),
            },
        }

        log_entry, created = CapiEventLog.objects.get_or_create(
            event_id=event_id,
            defaults={
                'event_name': 'Purchase',
                'event_time': event_time,
                'lead': lead,
                'order': None,  # ShopifyOrder FK - set if applicable
                'source': 'whatsapp' if 'whatsapp' in (lead.lead_source or '') else ('shopify' if 'shopify' in (lead.lead_source or '') else 'other'),
                'value': Decimal(str(value)),
                'currency': 'INR',
                'phone_hash_used': bool(user_data.get('ph')),
                'email_hash_used': bool(user_data.get('em')),
                'custom_data_json': event_data.get('custom_data', {}),
            }
        )

        return self._send_event(event_data, log_entry)

    def _send_event(self, event_data: dict, log_entry) -> Tuple[bool, dict]:
        """Actually send the event to Meta CAPI endpoint."""
        endpoint_id = self.config.capi_endpoint_id
        url = f"{self.BASE_URL}/{self.API_VERSION}/{endpoint_id}/events"

        payload = {
            'data': [event_data],
            'access_token': self.config.access_token,
        }

        if self.config.app_secret:
            # Add appsecret_proof if app_secret is set
            import hmac
            proof = hmac.new(
                self.config.app_secret.encode(),
                self.config.access_token.encode(),
                hashlib.sha256
            ).hexdigest()
            payload['appsecret_proof'] = proof

        try:
            response = requests.post(url, json=payload, timeout=30)
            response_data = response.json()

            if response.status_code == 200:
                log_entry.mark_sent(response=response_data)
                # Update config stats
                self.config.capi_success_count += 1
                self.config.last_capi_send_at = timezone.now()
                self.config.save(update_fields=['capi_success_count', 'last_capi_send_at'])

                # Update lead CAPI tracking
                lead = log_entry.lead
                if lead and log_entry.event_name == 'Lead':
                    lead.lead_event_sent_to_meta = True
                    lead.lead_event_sent_at = timezone.now()
                    lead.lead_event_id = log_entry.event_id
                    lead.save(update_fields=['lead_event_sent_to_meta', 'lead_event_sent_at', 'lead_event_id'])
                elif lead and log_entry.event_name == 'Purchase':
                    lead.conversion_sent_to_meta = True
                    lead.conversion_sent_at = timezone.now()
                    lead.conversion_event_id = log_entry.event_id
                    lead.save(update_fields=['conversion_sent_to_meta', 'conversion_sent_at', 'conversion_event_id'])

                return True, response_data
            else:
                error_msg = response_data.get('error', {}).get('message', 'Unknown error')
                log_entry.mark_failed(error_msg)
                self.config.capi_failure_count += 1
                self.config.save(update_fields=['capi_failure_count'])
                return False, response_data

        except Exception as e:
            log_entry.mark_failed(str(e))
            self.config.capi_failure_count += 1
            self.config.save(update_fields=['capi_failure_count'])
            return False, {'error': str(e)}

    def send_test_lead_event(self) -> Tuple[bool, dict]:
        """Send a test Lead event for verification in Events Manager."""
        if not self.is_configured():
            return False, {'error': 'Meta CAPI not configured'}

        event_data = {
            'event_name': 'Lead',
            'event_time': int(timezone.now().timestamp()),
            'event_id': f'test_lead_{int(timezone.now().timestamp())}',
            'action_source': 'website',
            'user_data': {
                'ph': [self.hash_value('919999999999')],
                'fn': [self.hash_value('test')],
            },
            'custom_data': {
                'lead_id': 'test_lead',
                'source': 'test',
            },
        }

        endpoint_id = self.config.capi_endpoint_id
        url = f"{self.BASE_URL}/{self.API_VERSION}/{endpoint_id}/events"
        payload = {
            'data': [event_data],
            'access_token': self.config.access_token,
            'test_event_code': 'TEST_EVENT',
        }

        try:
            response = requests.post(url, json=payload, timeout=30)
            return response.status_code == 200, response.json()
        except Exception as e:
            return False, {'error': str(e)}

    def send_test_purchase_event(self) -> Tuple[bool, dict]:
        """Send a test Purchase event for verification."""
        if not self.is_configured():
            return False, {'error': 'Meta CAPI not configured'}

        event_data = {
            'event_name': 'Purchase',
            'event_time': int(timezone.now().timestamp()),
            'event_id': f'test_purchase_{int(timezone.now().timestamp())}',
            'action_source': 'website',
            'user_data': {
                'ph': [self.hash_value('919999999999')],
            },
            'custom_data': {
                'value': 999.00,
                'currency': 'INR',
                'content_type': 'product',
            },
        }

        endpoint_id = self.config.capi_endpoint_id
        url = f"{self.BASE_URL}/{self.API_VERSION}/{endpoint_id}/events"
        payload = {
            'data': [event_data],
            'access_token': self.config.access_token,
            'test_event_code': 'TEST_EVENT',
        }

        try:
            response = requests.post(url, json=payload, timeout=30)
            return response.status_code == 200, response.json()
        except Exception as e:
            return False, {'error': str(e)}


# =============================================================================
# META INSIGHTS SERVICE
# =============================================================================

class MetaInsightsService:
    """
    Pulls daily ad insights from Meta Marketing API.
    Stores into MetaDailyInsights.
    """

    API_VERSION = 'v21.0'
    BASE_URL = 'https://graph.facebook.com'

    def __init__(self, config=None):
        from .meta_models import MetaIntegrationConfig
        if config is None:
            config = MetaIntegrationConfig.get_config()
        self.config = config

    def is_configured(self) -> bool:
        if not self.config:
            return False
        return bool(self.config.ad_account_id and self.config.access_token)

    def sync_daily_insights(self, target_date: date = None, safety_days: int = 7) -> dict:
        """
        Pull daily insights for target_date and safety window.
        Returns summary dict.
        """
        from .meta_models import MetaDailyInsights

        if not self.is_configured():
            return {'error': 'Meta Insights not configured', 'synced': 0}

        if target_date is None:
            target_date = (timezone.now() - timedelta(days=1)).date()

        start_date = target_date - timedelta(days=safety_days)
        end_date = target_date

        ad_account_id = self.config.ad_account_id
        if not ad_account_id.startswith('act_'):
            ad_account_id = f'act_{ad_account_id}'

        params = {
            'access_token': self.config.access_token,
            'fields': ','.join([
                'date_start', 'date_stop',
                'campaign_id', 'campaign_name', 'objective',
                'adset_id', 'adset_name',
                'ad_id', 'ad_name',
                'spend', 'impressions', 'clicks', 'reach',
                'actions', 'action_values',
            ]),
            'time_range': json.dumps({
                'since': start_date.strftime('%Y-%m-%d'),
                'until': end_date.strftime('%Y-%m-%d'),
            }),
            'level': 'campaign',
            'time_increment': 1,
            'limit': 500,
        }

        url = f"{self.BASE_URL}/{self.API_VERSION}/{ad_account_id}/insights"
        synced = 0
        errors = []

        try:
            while url:
                response = requests.get(url, params=params, timeout=60)
                data = response.json()

                if 'error' in data:
                    error_msg = data['error'].get('message', 'Unknown error')
                    self.config.last_insights_sync_status = 'error'
                    self.config.last_insights_sync_message = error_msg
                    self.config.last_insights_sync_at = timezone.now()
                    self.config.save(update_fields=['last_insights_sync_status', 'last_insights_sync_message', 'last_insights_sync_at'])
                    return {'error': error_msg, 'synced': synced}

                for row in data.get('data', []):
                    insight_date = datetime.strptime(row['date_start'], '%Y-%m-%d').date()
                    campaign_id = row.get('campaign_id', '')
                    adset_id = row.get('adset_id') or None
                    ad_id = row.get('ad_id') or None

                    # Extract messaging metrics from actions
                    messaging_started = 0
                    messaging_first_reply = 0
                    meta_leads = 0
                    meta_purchases = 0
                    meta_purchase_value = Decimal('0')

                    for action in row.get('actions', []):
                        action_type = action.get('action_type', '')
                        action_value = int(action.get('value', 0))
                        if action_type == 'onsite_conversion.messaging_conversation_started_7d':
                            messaging_started = action_value
                        elif action_type == 'onsite_conversion.messaging_first_reply':
                            messaging_first_reply = action_value
                        elif action_type == 'lead':
                            meta_leads = action_value
                        elif action_type == 'purchase':
                            meta_purchases = action_value

                    for av in row.get('action_values', []):
                        if av.get('action_type') == 'purchase':
                            meta_purchase_value = Decimal(str(av.get('value', 0)))

                    defaults = {
                        'campaign_name': row.get('campaign_name', ''),
                        'campaign_objective': row.get('objective', ''),
                        'adset_name': row.get('adset_name', ''),
                        'ad_name': row.get('ad_name', ''),
                        'spend': Decimal(str(row.get('spend', 0))),
                        'impressions': int(row.get('impressions', 0)),
                        'clicks': int(row.get('clicks', 0)),
                        'reach': int(row.get('reach', 0)),
                        'messaging_conversations_started': messaging_started,
                        'messaging_first_reply': messaging_first_reply,
                        'meta_leads': meta_leads,
                        'meta_purchases': meta_purchases,
                        'meta_purchase_value': meta_purchase_value,
                        'raw_json': row,
                    }

                    MetaDailyInsights.objects.update_or_create(
                        insight_date=insight_date,
                        campaign_id=campaign_id,
                        adset_id=adset_id,
                        ad_id=ad_id,
                        defaults=defaults,
                    )
                    synced += 1

                # Handle pagination
                next_url = data.get('paging', {}).get('next')
                if next_url:
                    url = next_url
                    params = {}  # params are in the URL now
                else:
                    url = None

            # Update sync status
            self.config.last_insights_sync_status = 'success'
            self.config.last_insights_sync_message = f'Synced {synced} records'
            self.config.last_insights_sync_at = timezone.now()
            self.config.save(update_fields=['last_insights_sync_status', 'last_insights_sync_message', 'last_insights_sync_at'])

        except Exception as e:
            logger.error(f"Meta Insights sync error: {e}", exc_info=True)
            self.config.last_insights_sync_status = 'error'
            self.config.last_insights_sync_message = str(e)
            self.config.last_insights_sync_at = timezone.now()
            self.config.save(update_fields=['last_insights_sync_status', 'last_insights_sync_message', 'last_insights_sync_at'])
            return {'error': str(e), 'synced': synced}

        return {'synced': synced, 'date_range': f'{start_date} to {end_date}'}


# =============================================================================
# PROBABILISTIC ATTRIBUTION ENGINE
# =============================================================================

class ProbabilisticAttributionEngine:
    """
    Assigns probabilistic ads/organic attribution to leads based on
    Meta conversation metrics vs ERP lead counts in time buckets.

    Since BSP/Wabis does NOT provide fbclid/campaign IDs from CTWA,
    this uses a statistical approach:
    
    ads_share = clamp(meta_conversations_started / total_wa_leads, 0..1)
    
    If ads_share > threshold (default 0.20), lead is probabilistic_ads.
    Otherwise organic.
    
    Manual overrides (manual_ads / manual_organic) are NEVER overwritten.
    """

    @classmethod
    def run_attribution(cls, target_date: date = None) -> dict:
        """
        Run probabilistic attribution for a given date bucket.
        """
        from .models import Lead
        from .meta_models import MetaIntegrationConfig, MetaDailyInsights

        if target_date is None:
            target_date = (timezone.now() - timedelta(days=1)).date()

        config = MetaIntegrationConfig.get_config()
        threshold = float(config.attribution_threshold) if config else 0.20

        # Get Meta conversations started for the date
        meta_conversations = MetaDailyInsights.objects.filter(
            insight_date=target_date
        ).aggregate(
            total_conversations=Sum('messaging_conversations_started'),
            total_spend=Sum('spend'),
        )
        total_conversations = meta_conversations['total_conversations'] or 0
        total_spend = meta_conversations['total_spend'] or Decimal('0')

        # Get WA leads created on this date
        wa_filter = Q(lead_source__icontains='whatsapp') | Q(source_type='whatsapp')
        wa_leads = Lead.objects.filter(
            wa_filter,
            created__date=target_date,
            is_active=True,
        )
        total_wa_leads = wa_leads.count()

        # Calculate ads_share
        if total_wa_leads > 0:
            ads_share = min(max(total_conversations / total_wa_leads, 0), 1.0)
        else:
            ads_share = 0.0

        # Apply attribution to leads (skip manual overrides)
        updated_count = 0
        for lead in wa_leads.exclude(attribution_model__in=['manual_ads', 'manual_organic']):
            if ads_share > threshold:
                lead.attribution_model = 'probabilistic_ads'
                lead.attribution_confidence = Decimal(str(round(ads_share * 100, 2)))
            else:
                lead.attribution_model = 'organic'
                lead.attribution_confidence = Decimal(str(round((1 - ads_share) * 100, 2)))

            lead.attribution_reason = (
                f"Bucket {target_date}: {total_conversations} Meta conversations / "
                f"{total_wa_leads} WA leads = {ads_share:.2%} ads share. "
                f"Threshold: {threshold:.0%}. Spend: ₹{total_spend}"
            )
            lead.attribution_bucket_date = target_date
            lead.attribution_updated_at = timezone.now()
            lead.save(update_fields=[
                'attribution_model', 'attribution_confidence',
                'attribution_reason', 'attribution_bucket_date',
                'attribution_updated_at',
            ])
            updated_count += 1

        # Also handle Shopify leads - mark as organic by default unless from ad
        shopify_filter = Q(lead_source__icontains='shopify') | Q(source_type='shopify')
        shopify_leads = Lead.objects.filter(
            shopify_filter,
            created__date=target_date,
            is_active=True,
            attribution_model='unknown',
        ).exclude(attribution_model__in=['manual_ads', 'manual_organic'])

        for lead in shopify_leads:
            lead.attribution_model = 'organic'
            lead.attribution_confidence = Decimal('80.00')
            lead.attribution_reason = f"Shopify lead default: organic (no CTWA signal)"
            lead.attribution_bucket_date = target_date
            lead.attribution_updated_at = timezone.now()
            lead.save(update_fields=[
                'attribution_model', 'attribution_confidence',
                'attribution_reason', 'attribution_bucket_date',
                'attribution_updated_at',
            ])
            updated_count += 1

        return {
            'date': str(target_date),
            'total_wa_leads': total_wa_leads,
            'meta_conversations': total_conversations,
            'ads_share': round(ads_share, 4),
            'threshold': threshold,
            'updated_leads': updated_count,
            'spend': float(total_spend),
        }

    @classmethod
    def get_campaign_attribution(cls, target_date: date) -> List[dict]:
        """
        Proportionally allocate ERP leads/revenue to campaigns
        based on each campaign's conversation share.
        """
        from .meta_models import MetaDailyInsights

        insights = MetaDailyInsights.objects.filter(
            insight_date=target_date,
            messaging_conversations_started__gt=0,
        )

        total_conversations = sum(i.messaging_conversations_started for i in insights)
        if total_conversations == 0:
            return []

        result = []
        for insight in insights:
            share = insight.messaging_conversations_started / total_conversations
            result.append({
                'campaign_id': insight.campaign_id,
                'campaign_name': insight.campaign_name,
                'spend': float(insight.spend),
                'conversations': insight.messaging_conversations_started,
                'share': round(share, 4),
                'erp_attributed_leads': insight.erp_attributed_leads,
                'erp_attributed_revenue': float(insight.erp_attributed_revenue),
            })

        return result


# =============================================================================
# MARKETING ROLLUP SERVICE
# =============================================================================

class MarketingRollupService:
    """
    Computes daily marketing rollups from leads + Meta insights.
    """

    @classmethod
    def compute_rollup(cls, target_date: date = None) -> dict:
        """Compute and store MarketingDailyRollup for a date."""
        from .models import Lead
        from .meta_models import MetaDailyInsights, MarketingDailyRollup

        if target_date is None:
            target_date = (timezone.now() - timedelta(days=1)).date()

        # All leads created on this date
        date_leads = Lead.objects.filter(created__date=target_date, is_active=True)

        # Counts
        leads_total = date_leads.count()
        wa_filter = Q(lead_source__icontains='whatsapp') | Q(source_type='whatsapp')
        shopify_filter = Q(lead_source__icontains='shopify') | Q(source_type='shopify')
        wa_leads = date_leads.filter(wa_filter).count()
        shopify_leads = date_leads.filter(shopify_filter).count()
        other_leads = leads_total - wa_leads - shopify_leads

        # Attribution breakdown
        estimated_ads = date_leads.filter(attribution_model='probabilistic_ads').count()
        estimated_ads += date_leads.filter(attribution_model='manual_ads').count()
        organic = date_leads.filter(attribution_model__in=['organic', 'manual_organic']).count()
        unknown = date_leads.filter(attribution_model='unknown').count()

        # Conversion metrics
        won = date_leads.filter(conversion_status='won').count()
        lost = date_leads.filter(conversion_status='lost').count()
        pending = date_leads.filter(conversion_status='pending').count()

        # Revenue
        revenue_total = date_leads.filter(
            conversion_status='won'
        ).aggregate(total=Sum('conversion_value'))['total'] or Decimal('0')

        revenue_ads = date_leads.filter(
            conversion_status='won',
            attribution_model__in=['probabilistic_ads', 'manual_ads']
        ).aggregate(total=Sum('conversion_value'))['total'] or Decimal('0')

        revenue_organic = date_leads.filter(
            conversion_status='won',
            attribution_model__in=['organic', 'manual_organic']
        ).aggregate(total=Sum('conversion_value'))['total'] or Decimal('0')

        # Spend from Meta
        insights_agg = MetaDailyInsights.objects.filter(
            insight_date=target_date
        ).aggregate(
            total_spend=Sum('spend'),
            total_conversations=Sum('messaging_conversations_started'),
            total_meta_leads=Sum('meta_leads'),
            total_meta_purchases=Sum('meta_purchases'),
            total_meta_revenue=Sum('meta_purchase_value'),
        )

        spend_total = insights_agg['total_spend'] or Decimal('0')
        meta_conversations = insights_agg['total_conversations'] or 0
        meta_leads = insights_agg['total_meta_leads'] or 0
        meta_purchases = insights_agg['total_meta_purchases'] or 0
        meta_revenue = insights_agg['total_meta_revenue'] or Decimal('0')

        # ROAS calculations
        estimated_roas = (revenue_ads / spend_total) if spend_total > 0 else Decimal('0')
        cost_per_lead = (spend_total / estimated_ads) if estimated_ads > 0 else Decimal('0')

        ads_won = date_leads.filter(
            conversion_status='won',
            attribution_model__in=['probabilistic_ads', 'manual_ads']
        ).count()
        cost_per_purchase = (spend_total / ads_won) if ads_won > 0 else Decimal('0')

        # Ads share
        ads_share = 0
        if wa_leads > 0 and meta_conversations > 0:
            ads_share = min(max(meta_conversations / wa_leads, 0), 1.0)

        # Avg attribution confidence
        avg_conf = date_leads.exclude(
            attribution_model='unknown'
        ).aggregate(avg=Avg('attribution_confidence'))['avg'] or Decimal('0')

        rollup, created = MarketingDailyRollup.objects.update_or_create(
            rollup_date=target_date,
            defaults={
                'spend_total': spend_total,
                'leads_total': leads_total,
                'wa_leads': wa_leads,
                'shopify_leads': shopify_leads,
                'other_leads': other_leads,
                'estimated_ads_leads': estimated_ads,
                'organic_leads': organic,
                'unknown_leads': unknown,
                'won_count': won,
                'lost_count': lost,
                'pending_count': pending,
                'revenue_total': revenue_total,
                'revenue_estimated_ads': revenue_ads,
                'revenue_organic': revenue_organic,
                'estimated_roas': estimated_roas,
                'cost_per_lead': cost_per_lead,
                'cost_per_purchase': cost_per_purchase,
                'meta_conversations_started': meta_conversations,
                'meta_reported_leads': meta_leads,
                'meta_reported_purchases': meta_purchases,
                'meta_reported_revenue': meta_revenue,
                'avg_attribution_confidence': avg_conf,
                'ads_share_ratio': Decimal(str(round(ads_share, 4))),
            }
        )

        return {
            'date': str(target_date),
            'leads_total': leads_total,
            'spend': float(spend_total),
            'revenue': float(revenue_total),
            'estimated_roas': float(estimated_roas),
            'created': created,
        }
