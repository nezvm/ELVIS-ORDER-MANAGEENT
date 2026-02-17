"""
Wabis WhatsApp BSP Services

Webhook processing, message handling, and lead management.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum, Count, Q
from django.utils import timezone

from marketing.models import Lead, LeadActivity

logger = logging.getLogger(__name__)


class WabisWebhookProcessor:
    """
    Process incoming Wabis webhooks.
    Follows Meta's standard WhatsApp Cloud API format.
    """
    
    def process_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process webhook payload.
        
        Returns dict with:
        - success: bool
        - event_type: str
        - phone_number_id: str
        - messages_processed: int
        - customers_created: int
        - customers_updated: int
        - error: str (if any)
        """
        result = {
            'success': False,
            'event_type': None,
            'phone_number_id': None,
            'messages_processed': 0,
            'customers_created': 0,
            'customers_updated': 0,
        }
        
        try:
            # Validate payload structure
            if payload.get('object') != 'whatsapp_business_account':
                result['event_type'] = 'non_whatsapp'
                result['success'] = True
                return result
            
            # Extract message events
            events = self._extract_events(payload)
            
            if not events:
                result['event_type'] = 'no_messages'
                result['success'] = True
                return result
            
            # Process each event
            for event in events:
                created, updated = self._process_event(event)
                result['messages_processed'] += 1
                result['customers_created'] += 1 if created else 0
                result['customers_updated'] += 1 if updated else 0
            
            result['phone_number_id'] = events[0].get('phone_number_id') if events else None
            result['event_type'] = 'messages'
            result['success'] = True
            
        except Exception as e:
            logger.error(f"Webhook processing error: {e}", exc_info=True)
            result['error'] = str(e)
        
        return result
    
    def _extract_events(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract message events from webhook payload."""
        events = []
        
        for entry in payload.get('entry', []):
            for change in entry.get('changes', []):
                if change.get('field') != 'messages':
                    continue
                
                value = change.get('value', {})
                metadata = value.get('metadata', {})
                phone_number_id = metadata.get('phone_number_id')
                display_phone = metadata.get('display_phone_number')
                
                if not phone_number_id:
                    continue
                
                # Extract contacts
                contacts = {}
                for contact in value.get('contacts', []):
                    wa_id = contact.get('wa_id')
                    if wa_id:
                        contacts[wa_id] = {
                            'profile_name': contact.get('profile', {}).get('name'),
                            'wa_id': wa_id
                        }
                
                # Extract messages
                for msg in value.get('messages', []):
                    wa_id = msg.get('from')
                    if not wa_id:
                        continue
                    
                    contact_info = contacts.get(wa_id, {'wa_id': wa_id})
                    
                    # Parse message content
                    msg_type = msg.get('type', 'unknown')
                    body = None
                    media_id = None
                    
                    if msg_type == 'text':
                        body = msg.get('text', {}).get('body')
                    elif msg_type in ['image', 'video', 'audio', 'document', 'sticker']:
                        media_obj = msg.get(msg_type, {})
                        media_id = media_obj.get('id')
                        body = media_obj.get('caption')
                    elif msg_type == 'location':
                        loc = msg.get('location', {})
                        body = f"Location: {loc.get('latitude')}, {loc.get('longitude')}"
                    elif msg_type == 'interactive':
                        interactive = msg.get('interactive', {})
                        int_type = interactive.get('type')
                        if int_type == 'button_reply':
                            body = interactive.get('button_reply', {}).get('title')
                        elif int_type == 'list_reply':
                            body = interactive.get('list_reply', {}).get('title')
                    elif msg_type == 'button':
                        body = msg.get('button', {}).get('text')
                    
                    # Parse timestamp
                    timestamp_str = msg.get('timestamp')
                    try:
                        timestamp_utc = datetime.utcfromtimestamp(int(timestamp_str))
                        timestamp_utc = timezone.make_aware(timestamp_utc, timezone.utc)
                    except (ValueError, TypeError):
                        timestamp_utc = timezone.now()
                    
                    # Extract referral (ad attribution)
                    referral = msg.get('referral', {})
                    
                    events.append({
                        'phone_number_id': phone_number_id,
                        'display_phone': display_phone,
                        'wa_id': wa_id,
                        'profile_name': contact_info.get('profile_name'),
                        'message_id': msg.get('id'),
                        'msg_type': msg_type,
                        'body': body,
                        'media_id': media_id,
                        'timestamp_utc': timestamp_utc,
                        'raw_message': msg,
                        'referral': referral if referral else None,
                    })
        
        return events
    
    @transaction.atomic
    def _process_event(self, event: Dict[str, Any]) -> Tuple[bool, bool]:
        """Process a single message event. Returns (created, updated)."""
        from .models import WabisNumber, WabisCustomer, WabisCustomerChannel, WabisMessage
        
        wa_id = event['wa_id']
        phone_number_id = event['phone_number_id']
        message_id = event.get('message_id')
        referral = event.get('referral')
        
        # Deduplicate by message_id
        if message_id and WabisMessage.objects.filter(message_id=message_id).exists():
            return False, False
        
        # Parse attribution
        attribution = self._parse_attribution(referral, event.get('body'))
        
        created = False
        updated = False
        
        # 1. Get or create number
        number, _ = WabisNumber.objects.get_or_create(
            phone_number_id=phone_number_id,
            defaults={
                'display_phone_number': event.get('display_phone') or phone_number_id,
                'display_name': f'Number {phone_number_id[-4:]}',
                'status': 'active',
            }
        )
        number.last_message_at = timezone.now()
        number.total_messages_received = (number.total_messages_received or 0) + 1
        number.save(update_fields=['last_message_at', 'total_messages_received', 'updated'])
        
        # 2. Get or create customer (GLOBAL DEDUPE BY wa_id)
        customer, created = WabisCustomer.objects.get_or_create(
            wa_id=wa_id,
            defaults={
                'profile_name': event.get('profile_name'),
                'last_message_preview': event.get('body', '')[:500] if event.get('body') else None,
                'last_message_at': event['timestamp_utc'],
                'lead_created_at': event['timestamp_utc'],
                'conversion_status': 'pending',
                # Attribution
                'source_type': attribution.get('source_type', 'unknown'),
                'is_from_ad': attribution.get('is_from_ad', False),
                'meta_fbclid': attribution.get('meta_fbclid'),
                'meta_campaign_id': attribution.get('meta_campaign_id'),
                'meta_adset_id': attribution.get('meta_adset_id'),
                'meta_ad_id': attribution.get('meta_ad_id'),
                'meta_ctwa_clid': attribution.get('meta_ctwa_clid'),
                'ad_headline': attribution.get('ad_headline'),
                'ad_body': attribution.get('ad_body'),
                'ad_source_url': attribution.get('ad_source_url'),
            }
        )
        
        if not created:
            updated = True
            customer.last_message_at = event['timestamp_utc']
            customer.last_message_preview = event.get('body', '')[:500] if event.get('body') else customer.last_message_preview
            customer.total_messages = (customer.total_messages or 0) + 1
            if event.get('profile_name') and not customer.profile_name:
                customer.profile_name = event.get('profile_name')
            customer.save(update_fields=['last_message_at', 'last_message_preview', 'total_messages', 'profile_name', 'updated'])
        
        # 3. Get or create channel (touchpoint)
        channel, channel_created = WabisCustomerChannel.objects.get_or_create(
            customer=customer,
            number=number,
        )
        channel.message_count = (channel.message_count or 0) + 1
        channel.save(update_fields=['message_count', 'updated'])
        
        if channel_created:
            customer.total_channels = customer.channels.count()
            customer.save(update_fields=['total_channels'])
            number.total_customers = WabisCustomerChannel.objects.filter(number=number).values('customer').distinct().count()
            number.save(update_fields=['total_customers'])
        
        # 4. Create message
        if message_id:
            WabisMessage.objects.create(
                customer=customer,
                number=number,
                message_id=message_id,
                direction='inbound',
                msg_type=event.get('msg_type', 'unknown'),
                body=event.get('body'),
                media_id=event.get('media_id'),
                timestamp_utc=event['timestamp_utc'],
                raw_payload=event.get('raw_message', {})
            )
        
        # 5. Create/update Lead
        if created:
            self._create_lead(customer, event, attribution)
        
        return created, updated
    
    def _parse_attribution(self, referral: Dict, message_body: str = None) -> Dict[str, Any]:
        """Parse attribution data from referral and message."""
        import re
        
        attribution = {
            'source_type': 'unknown',
            'is_from_ad': False,
        }
        
        if referral:
            source_type = referral.get('source_type', '').lower()
            if source_type == 'ad':
                attribution['is_from_ad'] = True
                attribution['source_type'] = 'ads'
            elif source_type:
                attribution['source_type'] = 'organic'
            
            attribution['meta_ctwa_clid'] = referral.get('ctwa_clid')
            attribution['ad_headline'] = referral.get('headline')
            attribution['ad_body'] = referral.get('body')
            attribution['ad_source_url'] = referral.get('source_url')
            attribution['meta_ad_id'] = referral.get('source_id')
        else:
            attribution['source_type'] = 'organic'
        
        # Extract click IDs from message
        if message_body:
            # Facebook click ID
            match = re.search(r'fbclid=([a-zA-Z0-9_-]+)', message_body)
            if match:
                attribution['meta_fbclid'] = match.group(1)
                attribution['is_from_ad'] = True
                attribution['source_type'] = 'ads'
            
            # Campaign ID
            match = re.search(r'campaign[_-]?id=([a-zA-Z0-9_-]+)', message_body, re.IGNORECASE)
            if match:
                attribution['meta_campaign_id'] = match.group(1)
        
        return attribution
    
    def _create_lead(self, customer, event: Dict, attribution: Dict):
        """Create a marketing Lead from WhatsApp customer."""
        try:
            phone_no = f"+{customer.wa_id}" if customer.wa_id else None
            
            # Determine lead source
            if attribution.get('is_from_ad'):
                lead_source = 'whatsapp_ctwa_ad'
            else:
                lead_source = 'whatsapp_inbound'
            
            # Create tags
            tags = ['whatsapp', 'wabis']
            if attribution.get('is_from_ad'):
                tags.extend(['from_ad', 'ctwa'])
            else:
                tags.append('organic')
            
            lead = Lead.objects.create(
                phone_no=phone_no,
                phone_normalized=customer.wa_id,
                name=customer.profile_name or f"WhatsApp Lead {customer.wa_id[-4:]}",
                lead_source=lead_source,
                lead_status='new',
                source_type=attribution.get('source_type', 'unknown'),
                captured_at=timezone.now(),
                tags=tags,
                conversion_status='pending',
                # Attribution
                ad_platform='meta' if attribution.get('is_from_ad') else None,
                meta_campaign_id=attribution.get('meta_campaign_id'),
                meta_adset_id=attribution.get('meta_adset_id'),
                meta_ad_id=attribution.get('meta_ad_id'),
                meta_fbclid=attribution.get('meta_fbclid'),
                notes=f"Auto-created from WhatsApp (Wabis).\n" +
                      f"Source: {attribution.get('source_type')}\n" +
                      (f"Ad Headline: {attribution.get('ad_headline')}\n" if attribution.get('ad_headline') else "") +
                      f"First message: {event.get('body', '')[:200] if event.get('body') else 'N/A'}"
            )
            
            # Link lead to customer
            customer.linked_lead = lead
            customer.save(update_fields=['linked_lead'])
            
            logger.info(f"Created Lead {lead.id} from Wabis customer {customer.id}")
            
        except Exception as e:
            logger.error(f"Error creating lead: {e}", exc_info=True)


class WabisConversionService:
    """
    Service for managing lead conversions and matching.
    """
    
    MATCHING_PERIOD_DAYS = 7
    
    @classmethod
    def match_lead_to_order(cls, order):
        """Find matching Wabis customer for an order."""
        from .models import WabisCustomer
        
        customer = order.customer
        phone = customer.phone_no if customer else getattr(order, 'phone', None)
        
        if not phone:
            return None
        
        phone = phone.replace('+', '').replace(' ', '').replace('-', '')
        
        cutoff = timezone.now() - timedelta(days=cls.MATCHING_PERIOD_DAYS)
        
        return WabisCustomer.objects.filter(
            Q(wa_id=phone) | Q(wa_id=phone[-10:]) | Q(wa_id='91' + phone[-10:]),
            conversion_status='pending',
            lead_created_at__gte=cutoff,
            is_active=True
        ).order_by('-lead_created_at').first()
    
    @classmethod
    def process_order_conversion(cls, order):
        """Process order and match to Wabis lead."""
        wabis_customer = cls.match_lead_to_order(order)
        
        if wabis_customer:
            wabis_customer.mark_as_won(order, order.total_amount)
            logger.info(f"Order {order.id} matched to Wabis customer {wabis_customer.id}")
            return True
        
        return False
    
    @classmethod
    def expire_pending_leads(cls):
        """Mark old pending leads as Lost."""
        from .models import WabisCustomer
        
        cutoff = timezone.now() - timedelta(days=cls.MATCHING_PERIOD_DAYS)
        
        pending = WabisCustomer.objects.filter(
            conversion_status='pending',
            lead_created_at__lt=cutoff,
            is_active=True
        )
        
        count = 0
        for customer in pending:
            customer.mark_as_lost()
            count += 1
        
        return count
