"""
WhatsApp Lead Attribution & Meta Conversion Services

Services for:
1. MetaCAPIService - Send conversion events to Meta Conversions API
2. MetaAdsService - Fetch ad spend from Meta Ads Insights API
3. LeadConversionService - Match leads to orders, manage conversion lifecycle
4. LeadAttributionService - Detect and parse attribution data from webhooks
"""

import hashlib
import json
import logging
import uuid
import requests
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List, Tuple

from django.conf import settings
from django.db import transaction
from django.db.models import Sum, Count, Q, F
from django.utils import timezone

logger = logging.getLogger(__name__)


# =============================================================================
# META CONVERSIONS API SERVICE
# =============================================================================

class MetaCAPIService:
    """
    Service for sending conversion events to Meta Conversions API (CAPI).
    
    Reference: https://developers.facebook.com/docs/marketing-api/conversions-api/
    """
    
    API_VERSION = 'v18.0'
    BASE_URL = 'https://graph.facebook.com'
    
    def __init__(self, config=None):
        """
        Initialize with MetaConversionConfig or use default.
        """
        from .models import MetaConversionConfig
        
        if config is None:
            config = MetaConversionConfig.objects.filter(is_active=True).first()
        
        self.config = config
        self.pixel_id = config.pixel_id if config else None
        self.access_token = config.access_token if config else None
        self.test_mode = config.test_mode if config else False
        self.test_event_code = config.test_event_code if config else None
    
    def is_configured(self) -> bool:
        """Check if service is properly configured."""
        return bool(self.pixel_id and self.access_token)
    
    @staticmethod
    def hash_value(value: str) -> str:
        """Hash a value using SHA256 (required by Meta CAPI)."""
        if not value:
            return None
        return hashlib.sha256(value.lower().strip().encode('utf-8')).hexdigest()
    
    def send_purchase_event(
        self,
        customer,
        order,
        event_id: str = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Send a Purchase conversion event to Meta CAPI.
        
        Args:
            customer: WhatsAppCustomer instance
            order: Order instance
            event_id: Optional unique event ID for deduplication
            
        Returns:
            Tuple of (success, response_data)
        """
        from .models import LeadConversionEvent
        
        if not self.is_configured():
            logger.warning("Meta CAPI not configured, skipping conversion send")
            return False, {'error': 'Meta CAPI not configured'}
        
        # Generate unique event ID if not provided
        if not event_id:
            event_id = f"purchase_{order.id}_{customer.id}_{int(timezone.now().timestamp())}"
        
        # Build user data (at least phone is required)
        user_data = {}
        
        # Phone number (hashed)
        phone = customer.wa_id
        if phone:
            # Normalize phone: remove +, spaces, etc. and add country code if needed
            phone = phone.replace('+', '').replace(' ', '').replace('-', '')
            if not phone.startswith('91') and len(phone) == 10:
                phone = '91' + phone
            user_data['ph'] = [self.hash_value(phone)]
        
        # Name (hashed)
        if customer.profile_name:
            names = customer.profile_name.split(' ', 1)
            user_data['fn'] = [self.hash_value(names[0])]
            if len(names) > 1:
                user_data['ln'] = [self.hash_value(names[1])]
        
        # Click ID (fbclid) - not hashed
        if customer.meta_fbclid:
            user_data['fbc'] = customer.meta_fbclid
        
        # CTWA Click ID - stored as external_id
        if customer.meta_ctwa_clid:
            user_data['external_id'] = [self.hash_value(customer.meta_ctwa_clid)]
        
        # Build custom data
        custom_data = {
            'value': float(order.total_amount),
            'currency': 'INR',
            'content_type': 'product',
            'order_id': str(order.id),
        }
        
        # Add content IDs if available
        try:
            order_items = order.orderitem_set.all()
            if order_items:
                custom_data['content_ids'] = [str(item.product.id) for item in order_items]
                custom_data['num_items'] = sum(item.quantity for item in order_items)
        except Exception:
            pass
        
        # Build event payload
        event_data = {
            'event_name': 'Purchase',
            'event_time': int(timezone.now().timestamp()),
            'event_id': event_id,
            'event_source_url': getattr(settings, 'SITE_URL', 'https://erp.example.com'),
            'action_source': 'website',
            'user_data': user_data,
            'custom_data': custom_data,
        }
        
        # Prepare API request
        payload = {
            'data': [event_data],
            'access_token': self.access_token,
        }
        
        # Add test event code if in test mode
        if self.test_mode and self.test_event_code:
            payload['test_event_code'] = self.test_event_code
        
        url = f"{self.BASE_URL}/{self.API_VERSION}/{self.pixel_id}/events"
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            response_data = response.json()
            
            # Create conversion event record
            conversion_event = LeadConversionEvent.objects.create(
                customer=customer,
                order=order,
                event_name='Purchase',
                event_time=timezone.now(),
                event_id=event_id,
                value=order.total_amount,
                currency='INR',
                fbclid=customer.meta_fbclid,
                ctwa_clid=customer.meta_ctwa_clid,
                campaign_id=customer.meta_campaign_id,
                sent=response.status_code == 200,
                sent_at=timezone.now() if response.status_code == 200 else None,
                response_code=response.status_code,
                response_body=json.dumps(response_data),
                error_message=response_data.get('error', {}).get('message') if response.status_code != 200 else None,
            )
            
            if response.status_code == 200:
                # Update config stats
                self.config.events_sent = (self.config.events_sent or 0) + 1
                self.config.last_event_at = timezone.now()
                self.config.last_error = None
                self.config.save(update_fields=['events_sent', 'last_event_at', 'last_error'])
                
                logger.info(f"Meta CAPI Purchase event sent: {event_id}, response: {response_data}")
                return True, response_data
            else:
                error_msg = response_data.get('error', {}).get('message', 'Unknown error')
                self.config.last_error = error_msg
                self.config.save(update_fields=['last_error'])
                
                logger.error(f"Meta CAPI error: {error_msg}")
                return False, response_data
                
        except Exception as e:
            logger.error(f"Meta CAPI request failed: {e}", exc_info=True)
            
            # Record failed attempt
            LeadConversionEvent.objects.create(
                customer=customer,
                order=order,
                event_name='Purchase',
                event_time=timezone.now(),
                event_id=event_id,
                value=order.total_amount,
                currency='INR',
                fbclid=customer.meta_fbclid,
                ctwa_clid=customer.meta_ctwa_clid,
                campaign_id=customer.meta_campaign_id,
                sent=False,
                error_message=str(e),
            )
            
            return False, {'error': str(e)}
    
    def send_lead_event(
        self,
        customer,
        event_id: str = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Send a Lead event to Meta CAPI (for lead generation tracking).
        """
        if not self.is_configured():
            return False, {'error': 'Meta CAPI not configured'}
        
        if not event_id:
            event_id = f"lead_{customer.id}_{int(timezone.now().timestamp())}"
        
        user_data = {}
        phone = customer.wa_id
        if phone:
            phone = phone.replace('+', '').replace(' ', '').replace('-', '')
            if not phone.startswith('91') and len(phone) == 10:
                phone = '91' + phone
            user_data['ph'] = [self.hash_value(phone)]
        
        if customer.profile_name:
            names = customer.profile_name.split(' ', 1)
            user_data['fn'] = [self.hash_value(names[0])]
        
        if customer.meta_fbclid:
            user_data['fbc'] = customer.meta_fbclid
        
        if customer.meta_ctwa_clid:
            user_data['external_id'] = [self.hash_value(customer.meta_ctwa_clid)]
        
        event_data = {
            'event_name': 'Lead',
            'event_time': int(customer.lead_created_at.timestamp()) if customer.lead_created_at else int(timezone.now().timestamp()),
            'event_id': event_id,
            'action_source': 'website',
            'user_data': user_data,
        }
        
        payload = {
            'data': [event_data],
            'access_token': self.access_token,
        }
        
        if self.test_mode and self.test_event_code:
            payload['test_event_code'] = self.test_event_code
        
        url = f"{self.BASE_URL}/{self.API_VERSION}/{self.pixel_id}/events"
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            return response.status_code == 200, response.json()
        except Exception as e:
            logger.error(f"Meta CAPI Lead event failed: {e}")
            return False, {'error': str(e)}


# =============================================================================
# META ADS INSIGHTS SERVICE
# =============================================================================

class MetaAdsService:
    """
    Service for fetching ad spend and insights from Meta Ads API.
    
    Reference: https://developers.facebook.com/docs/marketing-api/insights/
    """
    
    API_VERSION = 'v18.0'
    BASE_URL = 'https://graph.facebook.com'
    
    def __init__(self, config=None):
        """
        Initialize with MetaAdsConfig or use default.
        """
        from .models import MetaAdsConfig
        
        if config is None:
            config = MetaAdsConfig.objects.filter(is_active=True).first()
        
        self.config = config
        self.ad_account_id = config.ad_account_id if config else None
        self.access_token = config.access_token if config else None
    
    def is_configured(self) -> bool:
        """Check if service is properly configured."""
        return bool(self.ad_account_id and self.access_token)
    
    def get_daily_spend(
        self,
        date_start: datetime,
        date_end: datetime = None,
        campaign_ids: List[str] = None
    ) -> Dict[str, Any]:
        """
        Get daily ad spend from Meta Ads API.
        
        Args:
            date_start: Start date
            date_end: End date (defaults to date_start)
            campaign_ids: Optional list of campaign IDs to filter
            
        Returns:
            Dictionary with spend data by date and campaign
        """
        if not self.is_configured():
            logger.warning("Meta Ads API not configured")
            return {'error': 'Meta Ads API not configured'}
        
        if date_end is None:
            date_end = date_start
        
        # Build time range
        time_range = {
            'since': date_start.strftime('%Y-%m-%d'),
            'until': date_end.strftime('%Y-%m-%d'),
        }
        
        params = {
            'access_token': self.access_token,
            'fields': 'date_start,date_stop,campaign_id,campaign_name,spend,impressions,clicks,reach',
            'time_range': json.dumps(time_range),
            'level': 'campaign',
            'time_increment': 1,  # Daily breakdown
        }
        
        # Filter by campaign IDs if provided
        if campaign_ids:
            params['filtering'] = json.dumps([{
                'field': 'campaign.id',
                'operator': 'IN',
                'value': campaign_ids
            }])
        
        url = f"{self.BASE_URL}/{self.API_VERSION}/act_{self.ad_account_id}/insights"
        
        try:
            response = requests.get(url, params=params, timeout=60)
            data = response.json()
            
            if 'error' in data:
                error_msg = data['error'].get('message', 'Unknown error')
                logger.error(f"Meta Ads API error: {error_msg}")
                
                if self.config:
                    self.config.last_error = error_msg
                    self.config.save(update_fields=['last_error'])
                
                return {'error': error_msg}
            
            # Update last sync time
            if self.config:
                self.config.last_sync_at = timezone.now()
                self.config.last_error = None
                self.config.save(update_fields=['last_sync_at', 'last_error'])
            
            return {
                'data': data.get('data', []),
                'paging': data.get('paging', {}),
            }
            
        except Exception as e:
            logger.error(f"Meta Ads API request failed: {e}", exc_info=True)
            return {'error': str(e)}
    
    def get_account_spend_by_date(
        self,
        date: datetime
    ) -> Decimal:
        """
        Get total ad spend for a specific date.
        """
        result = self.get_daily_spend(date)
        
        if 'error' in result:
            return Decimal('0')
        
        total_spend = Decimal('0')
        for row in result.get('data', []):
            spend = row.get('spend', '0')
            total_spend += Decimal(spend)
        
        return total_spend
    
    def get_campaign_spend(
        self,
        campaign_id: str,
        date_start: datetime,
        date_end: datetime = None
    ) -> Decimal:
        """
        Get total spend for a specific campaign in date range.
        """
        result = self.get_daily_spend(date_start, date_end, [campaign_id])
        
        if 'error' in result:
            return Decimal('0')
        
        total_spend = Decimal('0')
        for row in result.get('data', []):
            spend = row.get('spend', '0')
            total_spend += Decimal(spend)
        
        return total_spend


# =============================================================================
# LEAD CONVERSION SERVICE
# =============================================================================

class LeadConversionService:
    """
    Service for managing lead conversion lifecycle.
    
    - Match leads to orders
    - Update lead statuses (Pending -> Won/Lost)
    - Trigger Meta CAPI events
    - Calculate conversion metrics
    """
    
    MATCHING_PERIOD_DAYS = 7
    
    @classmethod
    def match_lead_to_order(cls, order) -> Optional['WhatsAppCustomer']:
        """
        Find and match a WhatsApp lead to an order.
        
        Matching logic:
        1. Find lead by customer phone number
        2. Lead must be Pending status
        3. Lead must be within matching period (7 days)
        4. If multiple leads exist, use most recent Pending lead
        
        Returns:
            Matched WhatsAppCustomer or None
        """
        from .models import WhatsAppCustomer
        
        # Get customer phone from order
        customer = order.customer
        phone = customer.phone_no if customer else None
        
        if not phone:
            return None
        
        # Normalize phone (remove +, spaces, dashes)
        phone = phone.replace('+', '').replace(' ', '').replace('-', '')
        
        # Remove country code for comparison
        if phone.startswith('91') and len(phone) > 10:
            phone_without_code = phone[2:]
        else:
            phone_without_code = phone
        
        # Calculate matching period cutoff
        cutoff_date = timezone.now() - timedelta(days=cls.MATCHING_PERIOD_DAYS)
        
        # Find matching lead
        lead = WhatsAppCustomer.objects.filter(
            Q(wa_id=phone) | Q(wa_id=phone_without_code) | Q(wa_id='91' + phone_without_code),
            lead_status='pending',
            lead_created_at__gte=cutoff_date,
            is_active=True
        ).order_by('-lead_created_at').first()
        
        return lead
    
    @classmethod
    def process_order_conversion(cls, order) -> bool:
        """
        Process an order and match it to a WhatsApp lead.
        
        If a matching lead is found:
        1. Mark lead as Won
        2. Record conversion value
        3. Queue CAPI event (will be sent by Celery)
        
        Returns:
            True if conversion was recorded, False otherwise
        """
        lead = cls.match_lead_to_order(order)
        
        if not lead:
            logger.debug(f"No matching WhatsApp lead found for order {order.id}")
            return False
        
        # Mark lead as won
        lead.mark_as_won(order, order.total_amount)
        
        logger.info(f"Order {order.id} matched to WhatsApp lead {lead.id}, marked as Won")
        
        return True
    
    @classmethod
    def expire_pending_leads(cls) -> int:
        """
        Mark pending leads as Lost if they've exceeded the matching period.
        
        Called by daily Celery task.
        
        Returns:
            Number of leads marked as Lost
        """
        from .models import WhatsAppCustomer
        
        cutoff_date = timezone.now() - timedelta(days=cls.MATCHING_PERIOD_DAYS)
        
        pending_leads = WhatsAppCustomer.objects.filter(
            lead_status='pending',
            lead_created_at__lt=cutoff_date,
            is_active=True
        )
        
        count = 0
        for lead in pending_leads:
            lead.mark_as_lost()
            count += 1
            logger.debug(f"Lead {lead.id} marked as Lost (expired)")
        
        return count
    
    @classmethod
    def send_pending_conversions(cls) -> Tuple[int, int]:
        """
        Send conversion events to Meta CAPI for all Won leads
        that haven't been sent yet.
        
        Returns:
            Tuple of (sent_count, failed_count)
        """
        from .models import WhatsAppCustomer
        
        capi_service = MetaCAPIService()
        
        if not capi_service.is_configured():
            logger.warning("Meta CAPI not configured, skipping conversion sends")
            return 0, 0
        
        # Find won leads with unsent conversions
        won_leads = WhatsAppCustomer.objects.filter(
            lead_status='won',
            conversion_sent=False,
            converted_order__isnull=False,
            is_active=True
        ).select_related('converted_order')
        
        sent_count = 0
        failed_count = 0
        
        for lead in won_leads:
            success, response = capi_service.send_purchase_event(
                lead,
                lead.converted_order
            )
            
            if success:
                lead.conversion_sent = True
                lead.conversion_sent_at = timezone.now()
                lead.conversion_event_id = response.get('events_received', [{}])[0].get('event_id')
                lead.save(update_fields=['conversion_sent', 'conversion_sent_at', 'conversion_event_id'])
                sent_count += 1
            else:
                failed_count += 1
        
        return sent_count, failed_count
    
    @classmethod
    def get_conversion_stats(
        cls,
        phone_number_id: str = None,
        date_start: datetime = None,
        date_end: datetime = None
    ) -> Dict[str, Any]:
        """
        Get conversion statistics for reporting.
        """
        from .models import WhatsAppCustomer, WhatsAppCustomerChannel
        
        filters = {'is_active': True}
        
        if date_start:
            filters['lead_created_at__gte'] = date_start
        if date_end:
            filters['lead_created_at__lte'] = date_end
        
        queryset = WhatsAppCustomer.objects.filter(**filters)
        
        # Filter by phone number if provided
        if phone_number_id:
            customer_ids = WhatsAppCustomerChannel.objects.filter(
                phone_number_id=phone_number_id
            ).values_list('customer_id', flat=True)
            queryset = queryset.filter(id__in=customer_ids)
        
        total = queryset.count()
        won = queryset.filter(lead_status='won').count()
        lost = queryset.filter(lead_status='lost').count()
        pending = queryset.filter(lead_status='pending').count()
        
        ad_leads = queryset.filter(source_type='ad').count()
        organic_leads = queryset.filter(source_type='organic').count()
        
        revenue = queryset.filter(
            lead_status='won'
        ).aggregate(total=Sum('conversion_value'))['total'] or Decimal('0')
        
        conversion_rate = (won / total * 100) if total > 0 else 0
        
        return {
            'total_leads': total,
            'won': won,
            'lost': lost,
            'pending': pending,
            'ad_leads': ad_leads,
            'organic_leads': organic_leads,
            'revenue': revenue,
            'conversion_rate': round(conversion_rate, 2),
        }


# =============================================================================
# LEAD ATTRIBUTION SERVICE
# =============================================================================

class LeadAttributionService:
    """
    Service for detecting and parsing attribution data from webhooks.
    
    Supports:
    - Facebook Click ID (fbclid)
    - Google Click ID (gclid)
    - Meta CTWA Click ID (ctwa_clid)
    - Campaign IDs from referral data
    """
    
    @staticmethod
    def parse_referral_attribution(referral: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse attribution data from Meta webhook referral object.
        
        Args:
            referral: Referral object from webhook
            
        Returns:
            Dictionary with parsed attribution fields
        """
        if not referral:
            return {
                'source_type': 'organic',
                'is_from_ad': False,
                'attribution_source': 'organic',
                'ad_platform': None,
            }
        
        source_type = referral.get('source_type', '').lower()
        
        # Determine if from ad
        is_from_ad = source_type == 'ad'
        
        # Determine attribution source
        if source_type == 'ad':
            attribution_source = 'ctwa_ad'
        elif source_type:
            attribution_source = 'meta_ad'
        else:
            attribution_source = 'unknown'
        
        # Determine ad platform from source URL
        ad_platform = None
        source_url = referral.get('source_url', '')
        if source_url:
            if 'facebook.com' in source_url or 'fb.com' in source_url:
                ad_platform = 'facebook'
            elif 'instagram.com' in source_url:
                ad_platform = 'instagram'
        
        return {
            'source_type': 'ad' if is_from_ad else ('unknown' if source_type else 'organic'),
            'is_from_ad': is_from_ad,
            'attribution_source': attribution_source,
            'ad_platform': ad_platform,
            'meta_ad_source_id': referral.get('source_id'),
            'meta_ad_source_type': referral.get('source_type'),
            'meta_ad_source_url': referral.get('source_url'),
            'meta_ad_headline': referral.get('headline'),
            'meta_ad_body': referral.get('body'),
            'meta_ctwa_clid': referral.get('ctwa_clid'),
        }
    
    @staticmethod
    def extract_click_ids_from_message(message_body: str) -> Dict[str, str]:
        """
        Extract click IDs from message text.
        
        Sometimes ads include URLs with click IDs in the first message.
        
        Args:
            message_body: Message text
            
        Returns:
            Dictionary with extracted click IDs
        """
        import re
        
        result = {}
        
        if not message_body:
            return result
        
        # Extract fbclid
        fbclid_match = re.search(r'fbclid=([a-zA-Z0-9_-]+)', message_body)
        if fbclid_match:
            result['meta_fbclid'] = fbclid_match.group(1)
        
        # Extract gclid
        gclid_match = re.search(r'gclid=([a-zA-Z0-9_-]+)', message_body)
        if gclid_match:
            result['google_gclid'] = gclid_match.group(1)
        
        # Extract campaign ID from URL params
        campaign_match = re.search(r'campaign[_-]?id=([a-zA-Z0-9_-]+)', message_body, re.IGNORECASE)
        if campaign_match:
            result['meta_campaign_id'] = campaign_match.group(1)
        
        return result
    
    @classmethod
    def get_attribution_for_webhook(
        cls,
        referral: Dict[str, Any],
        message_body: str = None
    ) -> Dict[str, Any]:
        """
        Get complete attribution data from webhook event.
        
        Combines referral data and message text parsing.
        """
        # Parse referral
        attribution = cls.parse_referral_attribution(referral)
        
        # Extract click IDs from message
        if message_body:
            click_ids = cls.extract_click_ids_from_message(message_body)
            attribution.update(click_ids)
        
        return attribution


# =============================================================================
# DAILY REPORT SERVICE
# =============================================================================

class DailyReportService:
    """
    Service for generating daily lead reports.
    """
    
    @classmethod
    def generate_daily_report(cls, report_date: datetime.date) -> List['DailyLeadReport']:
        """
        Generate daily lead reports for all WhatsApp numbers.
        
        Args:
            report_date: Date to generate report for
            
        Returns:
            List of created DailyLeadReport instances
        """
        from .models import (
            WhatsAppCustomer,
            WhatsAppCustomerChannel,
            WhatsAppNumberConfig,
            DailyLeadReport
        )
        
        reports = []
        
        # Get date range
        date_start = timezone.make_aware(
            datetime.combine(report_date, datetime.min.time())
        )
        date_end = timezone.make_aware(
            datetime.combine(report_date, datetime.max.time())
        )
        
        # Get all number configs
        number_configs = WhatsAppNumberConfig.objects.filter(is_active=True)
        
        for number_config in number_configs:
            # Get customers for this number on this date
            customer_ids = WhatsAppCustomerChannel.objects.filter(
                phone_number_id=number_config.phone_number_id,
                first_contact_at__range=(date_start, date_end)
            ).values_list('customer_id', flat=True)
            
            customers = WhatsAppCustomer.objects.filter(
                id__in=customer_ids,
                lead_created_at__range=(date_start, date_end)
            )
            
            total_leads = customers.count()
            ad_leads = customers.filter(source_type='ad').count()
            organic_leads = customers.filter(source_type='organic').count()
            
            won_leads = customers.filter(lead_status='won').count()
            lost_leads = customers.filter(lead_status='lost').count()
            pending_leads = customers.filter(lead_status='pending').count()
            
            revenue = customers.filter(
                lead_status='won'
            ).aggregate(total=Sum('conversion_value'))['total'] or Decimal('0')
            
            conversion_rate = (won_leads / total_leads * 100) if total_leads > 0 else 0
            
            # Get ad spend from Meta Ads API
            ads_service = MetaAdsService()
            ad_spend = Decimal('0')
            if ads_service.is_configured():
                ad_spend = ads_service.get_account_spend_by_date(date_start)
            
            # Calculate ROAS
            roas = (revenue / ad_spend) if ad_spend > 0 else Decimal('0')
            
            # Create or update report
            report, created = DailyLeadReport.objects.update_or_create(
                report_date=report_date,
                phone_number_id=number_config.phone_number_id,
                defaults={
                    'number_config': number_config,
                    'total_leads': total_leads,
                    'ad_leads': ad_leads,
                    'organic_leads': organic_leads,
                    'conversions': won_leads,
                    'conversion_rate': conversion_rate,
                    'revenue': revenue,
                    'ad_spend': ad_spend,
                    'roas': roas,
                    'pending_leads': pending_leads,
                    'won_leads': won_leads,
                    'lost_leads': lost_leads,
                }
            )
            reports.append(report)
        
        # Generate aggregate report (all numbers)
        all_customers = WhatsAppCustomer.objects.filter(
            lead_created_at__range=(date_start, date_end),
            is_active=True
        )
        
        total_leads = all_customers.count()
        ad_leads = all_customers.filter(source_type='ad').count()
        organic_leads = all_customers.filter(source_type='organic').count()
        
        won_leads = all_customers.filter(lead_status='won').count()
        lost_leads = all_customers.filter(lead_status='lost').count()
        pending_leads = all_customers.filter(lead_status='pending').count()
        
        revenue = all_customers.filter(
            lead_status='won'
        ).aggregate(total=Sum('conversion_value'))['total'] or Decimal('0')
        
        conversion_rate = (won_leads / total_leads * 100) if total_leads > 0 else 0
        
        # Get total ad spend
        ads_service = MetaAdsService()
        ad_spend = Decimal('0')
        if ads_service.is_configured():
            ad_spend = ads_service.get_account_spend_by_date(date_start)
        
        roas = (revenue / ad_spend) if ad_spend > 0 else Decimal('0')
        
        aggregate_report, _ = DailyLeadReport.objects.update_or_create(
            report_date=report_date,
            phone_number_id=None,
            campaign_id=None,
            defaults={
                'total_leads': total_leads,
                'ad_leads': ad_leads,
                'organic_leads': organic_leads,
                'conversions': won_leads,
                'conversion_rate': conversion_rate,
                'revenue': revenue,
                'ad_spend': ad_spend,
                'roas': roas,
                'pending_leads': pending_leads,
                'won_leads': won_leads,
                'lost_leads': lost_leads,
            }
        )
        reports.append(aggregate_report)
        
        return reports
