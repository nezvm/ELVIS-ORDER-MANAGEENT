"""
Wabis API Client Service

This service connects to Wabis WhatsApp BSP API to:
- Fetch subscribers (leads)
- Get conversations
- Sync data to local ERP

API Documentation: https://bot.wabis.in/api/developer/console
"""
import requests
import logging
from datetime import datetime
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# Wabis API Base URL
WABIS_API_BASE = "https://bot.wabis.in/api/v1"


class WabisAPIClient:
    """Client for Wabis WhatsApp BSP API."""
    
    def __init__(self, api_token=None):
        """
        Initialize with API token.
        
        Args:
            api_token: Wabis API token. If not provided, reads from settings.
        """
        self.api_token = api_token or getattr(settings, 'WABIS_API_TOKEN', None)
        if not self.api_token:
            raise ValueError("WABIS_API_TOKEN is required")
        
        self.base_url = WABIS_API_BASE
        self.session = requests.Session()
    
    def _make_request(self, method, endpoint, data=None, params=None):
        """Make API request to Wabis."""
        url = f"{self.base_url}{endpoint}"
        
        # Add API token to request
        if data is None:
            data = {}
        data['apiToken'] = self.api_token
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, params={**data, **(params or {})})
            else:
                response = self.session.post(url, json=data)
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Wabis API error: {e}")
            raise
    
    # ==================== Subscriber APIs ====================
    
    def get_subscribers_list(self, whatsapp_bot_id, limit=100, offset=0, order_by=1):
        """
        Get list of subscribers (contacts/leads).
        
        Args:
            whatsapp_bot_id: The WhatsApp bot ID (phone_number_id in API docs)
            limit: Number of records to fetch (max 100)
            offset: Pagination offset
            order_by: 1 for latest first, 0 for default order
        
        Returns:
            dict: {status: '1', message: [...subscribers]}
        """
        return self._make_request('POST', '/whatsapp/subscriber/list', {
            'phone_number_id': whatsapp_bot_id,
            'limit': limit,
            'offset': offset,
            'orderBy': order_by
        })
    
    def get_subscriber(self, whatsapp_bot_id, phone_number):
        """
        Get single subscriber by phone number.
        
        Args:
            whatsapp_bot_id: The WhatsApp bot ID (phone_number_id in API docs)
            phone_number: Subscriber's phone number
        
        Returns:
            dict: Subscriber details
        """
        return self._make_request('POST', '/whatsapp/subscriber/get', {
            'phone_number_id': whatsapp_bot_id,
            'phone_number': phone_number
        })
    
    def create_subscriber(self, whatsapp_bot_id, phone_number, name=None, 
                          email=None, gender=None, city=None, birthday=None):
        """
        Create a new subscriber.
        
        Args:
            whatsapp_bot_id: The WhatsApp bot ID
            phone_number: Subscriber's phone number (required)
            name: Optional name
            email: Optional email
            gender: Optional gender
            city: Optional city
            birthday: Optional birthday (format: YYYY-MM-DD)
        
        Returns:
            dict: Created subscriber details
        """
        data = {
            'whatsapp_bot_id': whatsapp_bot_id,
            'phone_number': phone_number
        }
        if name:
            data['name'] = name
        if email:
            data['email'] = email
        if gender:
            data['gender'] = gender
        if city:
            data['city'] = city
        if birthday:
            data['birthday'] = birthday
        
        return self._make_request('POST', '/whatsapp/subscriber-create', data)
    
    # ==================== Conversation APIs ====================
    
    def get_conversation(self, whatsapp_bot_id, phone_number, limit=50, offset=0):
        """
        Get conversation history with a subscriber.
        
        Args:
            whatsapp_bot_id: The WhatsApp bot ID
            phone_number: Subscriber's phone number
            limit: Number of messages to fetch
            offset: Pagination offset
        
        Returns:
            dict: {success: bool, data: [...messages]}
        """
        return self._make_request('POST', '/whatsapp/get-conversation', {
            'whatsapp_bot_id': whatsapp_bot_id,
            'phone_number': phone_number,
            'limit': limit,
            'offset': offset
        })
    
    def get_message_delivery_status(self, whatsapp_bot_id, wa_message_id):
        """
        Check delivery status of a message.
        
        Args:
            whatsapp_bot_id: The WhatsApp bot ID
            wa_message_id: WhatsApp message ID
        
        Returns:
            dict: Delivery status details
        """
        return self._make_request('POST', '/whatsapp/delivery-message-status', {
            'whatsapp_bot_id': whatsapp_bot_id,
            'wa_message_id': wa_message_id
        })
    
    # ==================== Messaging APIs ====================
    
    def send_message(self, phone_number_id, recipient_phone, message_body):
        """
        Send a text message to a subscriber.
        
        Args:
            phone_number_id: Your WhatsApp phone number ID
            recipient_phone: Recipient's phone number
            message_body: Text message to send
        
        Returns:
            dict: Send result with message ID
        """
        return self._make_request('POST', '/whatsapp/send-message', {
            'phone_number_id': phone_number_id,
            'phone_number': recipient_phone,
            'message': message_body
        })
    
    def send_template_message(self, phone_number_id, recipient_phone, template_name, 
                               language_code='en', components=None):
        """
        Send a template message.
        
        Args:
            phone_number_id: Your WhatsApp phone number ID
            recipient_phone: Recipient's phone number
            template_name: Approved template name
            language_code: Template language code
            components: Template components (header, body, buttons)
        
        Returns:
            dict: Send result with message ID
        """
        data = {
            'phone_number_id': phone_number_id,
            'phone_number': recipient_phone,
            'template_name': template_name,
            'language_code': language_code
        }
        if components:
            data['components'] = components
        
        return self._make_request('POST', '/whatsapp/send-template-message', data)
    
    # ==================== Bot APIs ====================
    
    def get_bot_templates(self, whatsapp_bot_id):
        """
        Get message templates configured for a bot.
        
        Args:
            whatsapp_bot_id: The WhatsApp bot ID
        
        Returns:
            dict: List of templates
        """
        return self._make_request('POST', '/whatsapp/bot-template-get', {
            'whatsapp_bot_id': whatsapp_bot_id
        })
    
    def trigger_bot_flow(self, whatsapp_bot_id, phone_number, bot_flow_id):
        """
        Trigger a specific bot flow for a subscriber.
        
        Args:
            whatsapp_bot_id: The WhatsApp bot ID
            phone_number: Subscriber's phone number
            bot_flow_id: The flow ID to trigger
        
        Returns:
            dict: Trigger result
        """
        return self._make_request('POST', '/whatsapp/trigger-bot-flow', {
            'whatsapp_bot_id': whatsapp_bot_id,
            'phone_number': phone_number,
            'bot_flow_id': bot_flow_id
        })
    
    # ==================== Labels & Custom Fields ====================
    
    def get_labels_list(self, whatsapp_bot_id):
        """Get all labels for a bot."""
        return self._make_request('POST', '/whatsapp/label-list', {
            'whatsapp_bot_id': whatsapp_bot_id
        })
    
    def assign_label(self, whatsapp_bot_id, phone_number, label_id):
        """Assign a label to a subscriber."""
        return self._make_request('POST', '/whatsapp/assign-label', {
            'whatsapp_bot_id': whatsapp_bot_id,
            'phone_number': phone_number,
            'label_id': label_id
        })
    
    def get_custom_fields_list(self, whatsapp_bot_id):
        """Get all custom fields for a bot."""
        return self._make_request('POST', '/whatsapp/custom-field-list', {
            'whatsapp_bot_id': whatsapp_bot_id
        })
    
    def assign_custom_field(self, whatsapp_bot_id, phone_number, field_name, field_value):
        """Assign a custom field value to a subscriber."""
        return self._make_request('POST', '/whatsapp/assign-subscriber-custom-field', {
            'whatsapp_bot_id': whatsapp_bot_id,
            'phone_number': phone_number,
            'field_name': field_name,
            'field_value': field_value
        })


class WabisSubscriberSyncService:
    """Service to sync Wabis subscribers to local ERP."""
    
    def __init__(self, api_token=None):
        self.client = WabisAPIClient(api_token)
    
    def sync_all_numbers(self):
        """
        Sync subscribers from ALL configured WhatsApp numbers.
        
        Returns:
            dict: {total_created: int, total_updated: int, total_errors: int, numbers_synced: int, details: [...]}
        """
        from integrations.wabis.models import WabisNumber
        
        # Get all active numbers with bot IDs configured
        numbers = WabisNumber.objects.filter(
            is_active=True,
            wabis_bot_id__isnull=False
        ).exclude(wabis_bot_id='')
        
        total_stats = {
            'total_created': 0,
            'total_updated': 0,
            'total_errors': 0,
            'numbers_synced': 0,
            'details': []
        }
        
        for number in numbers:
            try:
                stats = self.sync_all_subscribers(
                    whatsapp_bot_id=number.wabis_bot_id,
                    wabis_number=number
                )
                total_stats['total_created'] += stats['created']
                total_stats['total_updated'] += stats['updated']
                total_stats['total_errors'] += stats['errors']
                total_stats['numbers_synced'] += 1
                total_stats['details'].append({
                    'number': number.display_phone_number,
                    'name': number.display_name,
                    'bot_id': number.wabis_bot_id,
                    'stats': stats
                })
            except Exception as e:
                total_stats['total_errors'] += 1
                total_stats['details'].append({
                    'number': number.display_phone_number,
                    'name': number.display_name,
                    'bot_id': number.wabis_bot_id,
                    'error': str(e)
                })
        
        return total_stats
    
    def sync_all_subscribers(self, whatsapp_bot_id, wabis_number=None, config=None):
        """
        Sync all subscribers from a single Wabis bot to local database.
        
        Args:
            whatsapp_bot_id: The WhatsApp bot ID to sync from
            wabis_number: WabisNumber instance (optional) - to link customers to specific number
            config: WabisConfig instance (optional)
        
        Returns:
            dict: {created: int, updated: int, errors: int}
        """
        from integrations.wabis.models import WabisCustomer, WabisNumber, WabisSyncLog
        from marketing.models import Lead
        import re
        
        stats = {'created': 0, 'updated': 0, 'errors': 0, 'total': 0}
        
        # Create sync log
        sync_log = WabisSyncLog.objects.create(
            sync_type='subscribers',
            status='in_progress'
        )
        
        try:
            offset = 0
            limit = 100
            
            while True:
                response = self.client.get_subscribers_list(
                    whatsapp_bot_id=whatsapp_bot_id,
                    limit=limit,
                    offset=offset
                )
                
                if not response.get('success') or not response.get('data'):
                    break
                
                subscribers = response['data']
                if not subscribers:
                    break
                
                for sub in subscribers:
                    stats['total'] += 1
                    try:
                        # Extract phone number
                        phone = sub.get('phone_number', '') or sub.get('phone', '')
                        if not phone:
                            continue
                        
                        # Normalize phone
                        phone_digits = re.sub(r'\D', '', phone)
                        wa_id = phone_digits[-10:] if len(phone_digits) >= 10 else phone_digits
                        
                        # Create or update WabisCustomer
                        customer, created = WabisCustomer.objects.update_or_create(
                            wa_id=wa_id,
                            defaults={
                                'profile_name': sub.get('name', '') or sub.get('first_name', ''),
                                'email': sub.get('email', ''),
                                'source_type': 'organic',  # Default, can be updated
                                'wabis_subscriber_id': sub.get('id'),
                                'last_message_at': timezone.now(),
                            }
                        )
                        
                        # Create/update Lead
                        lead, lead_created = Lead.objects.get_or_create(
                            phone_no__endswith=wa_id,
                            defaults={
                                'name': sub.get('name', '') or f"WhatsApp {wa_id}",
                                'phone_no': f"+91{wa_id}",
                                'email': sub.get('email', ''),
                                'lead_source': 'whatsapp_inbound',
                                'source_type': 'whatsapp',
                                'conversion_status': 'pending',
                            }
                        )
                        
                        if not lead_created and not lead.name:
                            lead.name = sub.get('name', '') or lead.name
                            lead.save()
                        
                        # Link customer to lead
                        if not customer.linked_lead:
                            customer.linked_lead = lead
                            customer.save()
                        
                        if created:
                            stats['created'] += 1
                        else:
                            stats['updated'] += 1
                            
                    except Exception as e:
                        logger.error(f"Error syncing subscriber {sub}: {e}")
                        stats['errors'] += 1
                
                offset += limit
                
                # Safety limit
                if offset > 10000:
                    break
            
            sync_log.status = 'completed'
            sync_log.items_processed = stats['total']
            sync_log.items_created = stats['created']
            sync_log.items_updated = stats['updated']
            sync_log.items_failed = stats['errors']
            sync_log.completed_at = timezone.now()
            sync_log.save()
            
        except Exception as e:
            sync_log.status = 'failed'
            sync_log.error_message = str(e)
            sync_log.save()
            raise
        
        return stats
    
    def sync_conversations(self, whatsapp_bot_id, phone_number, limit=50):
        """
        Sync conversation history for a specific subscriber.
        
        Args:
            whatsapp_bot_id: The WhatsApp bot ID
            phone_number: Subscriber's phone number
            limit: Number of messages to fetch
        
        Returns:
            int: Number of messages synced
        """
        from integrations.wabis.models import WabisCustomer, WabisMessage, WabisNumber
        import re
        
        response = self.client.get_conversation(
            whatsapp_bot_id=whatsapp_bot_id,
            phone_number=phone_number,
            limit=limit
        )
        
        if not response.get('success') or not response.get('data'):
            return 0
        
        messages = response['data']
        synced = 0
        
        # Find customer
        phone_digits = re.sub(r'\D', '', phone_number)
        wa_id = phone_digits[-10:] if len(phone_digits) >= 10 else phone_digits
        
        customer = WabisCustomer.objects.filter(wa_id=wa_id).first()
        if not customer:
            return 0
        
        # Get default number
        number = WabisNumber.objects.filter(is_active=True).first()
        if not number:
            return 0
        
        for msg in messages:
            try:
                msg_id = msg.get('wa_message_id', '') or f"wabis_{msg.get('id')}"
                WabisMessage.objects.get_or_create(
                    message_id=msg_id,
                    defaults={
                        'customer': customer,
                        'number': number,
                        'direction': 'inbound' if msg.get('type') == 'received' else 'outbound',
                        'msg_type': msg.get('message_type', 'text'),
                        'body': msg.get('message', '') or msg.get('body', ''),
                        'timestamp_utc': timezone.now(),
                        'raw_payload': msg,
                    }
                )
                synced += 1
            except Exception as e:
                logger.error(f"Error syncing message: {e}")
        
        return synced
