import json
import logging
from datetime import datetime
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_GET
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, ListView, DetailView
from django.urls import reverse

from .models import (
    WhatsAppCustomer,
    WhatsAppNumberConfig,
    WhatsAppCustomerChannel,
    WhatsAppMessage,
    WhatsAppWebhookLog
)
from marketing.models import Lead

logger = logging.getLogger(__name__)

# =============================================================================
# WEBHOOK ENDPOINTS
# =============================================================================

@csrf_exempt
@require_http_methods(["GET", "POST"])
def whatsapp_webhook(request):
    """
    Combined webhook endpoint for Meta WhatsApp Business Platform.
    - GET: Webhook verification
    - POST: Receive incoming messages/events
    """
    if request.method == "GET":
        return webhook_verify(request)
    else:
        return webhook_receive(request)


def webhook_verify(request):
    """
    Handle Meta webhook verification.
    Meta sends: hub.mode, hub.verify_token, hub.challenge
    We must return hub.challenge if token matches.
    """
    mode = request.GET.get('hub.mode')
    token = request.GET.get('hub.verify_token')
    challenge = request.GET.get('hub.challenge')
    
    # Get verify token from settings
    verify_token = getattr(settings, 'WA_VERIFY_TOKEN', 'elvis_whatsapp_verify_2024')
    
    logger.info(f"Webhook verification: mode={mode}, token_match={token == verify_token}")
    
    if mode == 'subscribe' and token == verify_token:
        logger.info("Webhook verified successfully")
        return HttpResponse(challenge, content_type='text/plain', status=200)
    else:
        logger.warning(f"Webhook verification failed: mode={mode}, token={token}")
        return HttpResponse('Verification failed', status=403)


def webhook_receive(request):
    """
    Handle incoming webhook POST from Meta.
    Always return 200 to prevent retry storms.
    """
    webhook_log = None
    try:
        # Parse payload
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            logger.error("Invalid JSON in webhook payload")
            return HttpResponse('OK', status=200)
        
        # Create webhook log
        webhook_log = WhatsAppWebhookLog.objects.create(
            payload=payload,
            event_type='webhook_received'
        )
        
        # Extract and process events
        events = extract_message_events(payload)
        
        if not events:
            webhook_log.event_type = 'no_messages'
            webhook_log.processed = True
            webhook_log.save()
            return HttpResponse('OK', status=200)
        
        # Process each event
        customers_created = 0
        customers_updated = 0
        messages_processed = 0
        
        for event in events:
            try:
                created, updated = process_message_event(event)
                if created:
                    customers_created += 1
                if updated:
                    customers_updated += 1
                messages_processed += 1
            except Exception as e:
                logger.error(f"Error processing event: {e}", exc_info=True)
        
        # Update webhook log
        webhook_log.phone_number_id = events[0].get('phone_number_id') if events else None
        webhook_log.event_type = 'messages'
        webhook_log.processed = True
        webhook_log.messages_processed = messages_processed
        webhook_log.customers_created = customers_created
        webhook_log.customers_updated = customers_updated
        webhook_log.save()
        
        logger.info(f"Webhook processed: {messages_processed} messages, {customers_created} new customers")
        
    except Exception as e:
        logger.error(f"Webhook processing error: {e}", exc_info=True)
        if webhook_log:
            webhook_log.processed = False
            webhook_log.error_message = str(e)
            webhook_log.save()
    
    # Always return 200
    return HttpResponse('OK', status=200)


def extract_message_events(payload):
    """
    Extract message events from Meta webhook payload.
    
    Payload structure:
    {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "<WABA_ID>",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": "...",
                        "phone_number_id": "..."
                    },
                    "contacts": [{"profile": {"name": "..."}, "wa_id": "..."}],
                    "messages": [{...}]
                },
                "field": "messages"
            }]
        }]
    }
    
    Referral structure (for Click-to-WhatsApp ads):
    "referral": {
        "source_url": "https://...",
        "source_type": "ad",
        "source_id": "123456789",
        "headline": "Ad headline",
        "body": "Ad body text",
        "ctwa_clid": "click_tracking_id"
    }
    """
    events = []
    
    if payload.get('object') != 'whatsapp_business_account':
        return events
    
    for entry in payload.get('entry', []):
        for change in entry.get('changes', []):
            if change.get('field') != 'messages':
                continue
            
            value = change.get('value', {})
            metadata = value.get('metadata', {})
            phone_number_id = metadata.get('phone_number_id')
            display_phone_number = metadata.get('display_phone_number')
            
            if not phone_number_id:
                continue
            
            contacts = value.get('contacts', [])
            messages = value.get('messages', [])
            
            # Build contact lookup
            contact_map = {}
            for contact in contacts:
                wa_id = contact.get('wa_id')
                if wa_id:
                    contact_map[wa_id] = {
                        'profile_name': contact.get('profile', {}).get('name'),
                        'wa_id': wa_id
                    }
            
            # Process each message
            for msg in messages:
                wa_id = msg.get('from')
                if not wa_id:
                    continue
                
                contact_info = contact_map.get(wa_id, {'wa_id': wa_id})
                
                # Extract message content
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
                elif msg_type == 'contacts':
                    body = f"Shared {len(msg.get('contacts', []))} contact(s)"
                elif msg_type == 'interactive':
                    interactive = msg.get('interactive', {})
                    int_type = interactive.get('type')
                    if int_type == 'button_reply':
                        body = interactive.get('button_reply', {}).get('title')
                    elif int_type == 'list_reply':
                        body = interactive.get('list_reply', {}).get('title')
                elif msg_type == 'button':
                    body = msg.get('button', {}).get('text')
                elif msg_type == 'reaction':
                    body = msg.get('reaction', {}).get('emoji')
                
                # Parse timestamp
                timestamp_str = msg.get('timestamp')
                try:
                    timestamp_utc = datetime.utcfromtimestamp(int(timestamp_str))
                    timestamp_utc = timezone.make_aware(timestamp_utc, timezone.utc)
                except (ValueError, TypeError):
                    timestamp_utc = timezone.now()
                
                # Extract referral data (for Click-to-WhatsApp ads)
                referral = msg.get('referral', {})
                referral_data = None
                if referral:
                    referral_data = {
                        'source_url': referral.get('source_url'),
                        'source_type': referral.get('source_type'),
                        'source_id': referral.get('source_id'),
                        'headline': referral.get('headline'),
                        'body': referral.get('body'),
                        'ctwa_clid': referral.get('ctwa_clid'),
                        'media_type': referral.get('media_type'),
                        'image_url': referral.get('image', {}).get('link') if referral.get('image') else None,
                        'video_url': referral.get('video', {}).get('link') if referral.get('video') else None,
                    }
                
                # Also check context for referral (some webhook versions)
                context = msg.get('context', {})
                if not referral_data and context.get('referral_from_message_id'):
                    referral_data = {
                        'source_type': 'referral',
                        'referral_message_id': context.get('referral_from_message_id')
                    }
                
                events.append({
                    'phone_number_id': phone_number_id,
                    'display_phone_number': display_phone_number,
                    'wa_id': wa_id,
                    'profile_name': contact_info.get('profile_name'),
                    'message_id': msg.get('id'),
                    'msg_type': msg_type,
                    'body': body,
                    'media_id': media_id,
                    'timestamp_utc': timestamp_utc,
                    'raw_message': msg,
                    'referral': referral_data,  # Ad attribution data
                })
    
    return events


@transaction.atomic
def process_message_event(event):
    """
    Process a single message event with proper deduplication.
    Returns (customer_created, customer_updated) booleans.
    """
    wa_id = event['wa_id']
    phone_number_id = event['phone_number_id']
    profile_name = event.get('profile_name')
    message_id = event.get('message_id')
    
    customer_created = False
    customer_updated = False
    
    # Check if message already processed (dedup by message_id)
    if message_id and WhatsAppMessage.objects.filter(message_id=message_id).exists():
        logger.debug(f"Message {message_id} already processed, skipping")
        return False, False
    
    # 1. Upsert WhatsAppCustomer (global dedup by wa_id)
    customer, created = WhatsAppCustomer.objects.get_or_create(
        wa_id=wa_id,
        defaults={
            'profile_name': profile_name,
            'last_message_preview': event.get('body', '')[:500] if event.get('body') else None,
            'last_message_at': event['timestamp_utc'],
        }
    )
    
    if created:
        customer_created = True
        logger.info(f"New WhatsApp customer: {wa_id}")
    else:
        # Update existing customer
        customer_updated = True
        update_fields = ['last_seen', 'last_message_at', 'total_messages']
        
        if profile_name and profile_name != customer.profile_name:
            customer.profile_name = profile_name
            update_fields.append('profile_name')
        
        if event.get('body'):
            customer.last_message_preview = event['body'][:500]
            update_fields.append('last_message_preview')
        
        customer.last_message_at = event['timestamp_utc']
        customer.total_messages = (customer.total_messages or 0) + 1
        customer.save(update_fields=update_fields)
    
    # 2. Upsert WhatsAppNumberConfig (track the sales number)
    number_config, _ = WhatsAppNumberConfig.objects.get_or_create(
        phone_number_id=phone_number_id,
        defaults={
            'display_phone_number': event.get('display_phone_number'),
        }
    )
    number_config.last_webhook_at = timezone.now()
    number_config.webhook_count = (number_config.webhook_count or 0) + 1
    number_config.total_messages_received = (number_config.total_messages_received or 0) + 1
    number_config.save(update_fields=['last_webhook_at', 'webhook_count', 'total_messages_received', 'modified'])
    
    # 3. Upsert WhatsAppCustomerChannel (touchpoint)
    channel, channel_created = WhatsAppCustomerChannel.objects.get_or_create(
        customer=customer,
        phone_number_id=phone_number_id,
        defaults={
            'number_config': number_config,
        }
    )
    channel.message_count = (channel.message_count or 0) + 1
    channel.last_contact_at = event['timestamp_utc']
    channel.save(update_fields=['message_count', 'last_contact_at', 'modified'])
    
    # Update customer's channel count if new channel
    if channel_created:
        customer.total_channels_contacted = customer.channels.count()
        customer.save(update_fields=['total_channels_contacted'])
        
        # Update number config's customer count
        number_config.total_customers = WhatsAppCustomerChannel.objects.filter(
            phone_number_id=phone_number_id
        ).values('customer').distinct().count()
        number_config.save(update_fields=['total_customers'])
    
    # 4. Create WhatsAppMessage
    if message_id:
        WhatsAppMessage.objects.create(
            customer=customer,
            phone_number_id=phone_number_id,
            message_id=message_id,
            direction='inbound',
            msg_type=event.get('msg_type', 'unknown'),
            body=event.get('body'),
            media_id=event.get('media_id'),
            timestamp_utc=event['timestamp_utc'],
            raw_payload=event.get('raw_message', {})
        )
    
    # 5. Create/Update Lead in marketing app for unified lead management
    if customer_created:
        create_or_update_lead(customer, event)
    
    return customer_created, customer_updated


def create_or_update_lead(customer, event):
    """
    Create or update a Lead record for unified lead management.
    """
    try:
        # Format phone number
        phone_no = f"+{customer.wa_id}" if customer.wa_id else None
        
        # Check if lead already exists with this phone
        lead = Lead.objects.filter(phone_no=phone_no).first()
        
        if not lead:
            # Create new lead
            lead = Lead.objects.create(
                phone_no=phone_no,
                phone_normalized=customer.wa_id,
                name=customer.profile_name or f"WhatsApp Lead {customer.wa_id[-4:]}",
                lead_source='whatsapp_inbound',
                lead_status='new',
                captured_at=timezone.now(),
                notes=f"Auto-created from WhatsApp inbound message. First message: {event.get('body', '')[:200] if event.get('body') else 'N/A'}"
            )
            logger.info(f"Created Lead from WhatsApp: {lead.id}")
        else:
            # Update existing lead if it was from a different source
            if lead.lead_source != 'whatsapp_inbound':
                lead.notes = (lead.notes or '') + f"\n\n[{timezone.now()}] Also contacted via WhatsApp."
                lead.save(update_fields=['notes', 'modified'])
        
        # Link customer to lead
        customer.linked_lead = lead
        customer.save(update_fields=['linked_lead'])
        
    except Exception as e:
        logger.error(f"Error creating lead from WhatsApp: {e}", exc_info=True)


# =============================================================================
# UI VIEWS
# =============================================================================

class WhatsAppDashboardView(LoginRequiredMixin, TemplateView):
    """WhatsApp connection setup and status page."""
    template_name = 'integrations/whatsapp/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'WhatsApp Integration'
        context['is_integrations'] = True
        context['is_whatsapp'] = True
        
        # Webhook URL
        context['webhook_url'] = self.request.build_absolute_uri(
            reverse('integrations:whatsapp_webhook')
        )
        
        # Verify token
        context['verify_token'] = getattr(settings, 'WA_VERIFY_TOKEN', 'elvis_whatsapp_verify_2024')
        
        # Connected numbers with stats
        context['numbers'] = WhatsAppNumberConfig.objects.filter(is_active=True).order_by('-last_webhook_at')
        
        # Recent customers
        context['recent_customers'] = WhatsAppCustomer.objects.filter(is_active=True)[:10]
        
        # Stats
        context['total_customers'] = WhatsAppCustomer.objects.filter(is_active=True).count()
        context['total_messages'] = WhatsAppMessage.objects.count()
        context['total_numbers'] = WhatsAppNumberConfig.objects.filter(is_active=True).count()
        
        # Recent webhook logs
        context['recent_webhooks'] = WhatsAppWebhookLog.objects.all()[:5]
        
        return context


class WhatsAppCustomerListView(LoginRequiredMixin, ListView):
    """List all WhatsApp customers/leads."""
    model = WhatsAppCustomer
    template_name = 'integrations/whatsapp/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 50
    
    def get_queryset(self):
        return WhatsAppCustomer.objects.filter(is_active=True).order_by('-last_message_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'WhatsApp Leads'
        context['is_integrations'] = True
        context['is_whatsapp'] = True
        context['is_customers'] = True
        return context


class WhatsAppCustomerDetailView(LoginRequiredMixin, DetailView):
    """View a single WhatsApp customer with message history."""
    model = WhatsAppCustomer
    template_name = 'integrations/whatsapp/customer_detail.html'
    context_object_name = 'customer'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'WhatsApp: {self.object.profile_name or self.object.wa_id}'
        context['is_integrations'] = True
        context['is_whatsapp'] = True
        
        # Messages
        context['messages'] = self.object.messages.all()[:100]
        
        # Channels (touchpoints)
        context['channels'] = self.object.channels.all()
        
        return context
