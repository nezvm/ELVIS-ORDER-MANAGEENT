import json
import logging
from datetime import datetime
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, ListView, DetailView
from django.urls import reverse
from django.db.models import Sum, Count, Q, Avg
from datetime import timedelta
from decimal import Decimal

from .models import (
    WhatsAppCustomer,
    WhatsAppNumberConfig,
    WhatsAppCustomerChannel,
    WhatsAppMessage,
    WhatsAppWebhookLog,
    WhatsAppConnectedNumber,
    MetaConversionConfig,
    MetaAdsConfig,
    DailyLeadReport,
    LeadConversionEvent,
)
from .services import (
    LeadAttributionService,
    LeadConversionService,
    MetaCAPIService,
    MetaAdsService,
    DailyReportService,
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
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            logger.error("Invalid JSON in webhook payload")
            return HttpResponse('OK', status=200)
        
        webhook_log = WhatsAppWebhookLog.objects.create(
            payload=payload,
            event_type='webhook_received'
        )
        
        events = extract_message_events(payload)
        
        if not events:
            webhook_log.event_type = 'no_messages'
            webhook_log.processed = True
            webhook_log.save()
            return HttpResponse('OK', status=200)
        
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
    
    return HttpResponse('OK', status=200)


def extract_message_events(payload):
    """
    Extract message events from Meta webhook payload.
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
            
            contact_map = {}
            for contact in contacts:
                wa_id = contact.get('wa_id')
                if wa_id:
                    contact_map[wa_id] = {
                        'profile_name': contact.get('profile', {}).get('name'),
                        'wa_id': wa_id
                    }
            
            for msg in messages:
                wa_id = msg.get('from')
                if not wa_id:
                    continue
                
                contact_info = contact_map.get(wa_id, {'wa_id': wa_id})
                
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
                    'referral': referral_data,
                })
    
    return events


@transaction.atomic
def process_message_event(event):
    """
    Process a single message event with proper deduplication and attribution.
    Returns (customer_created, customer_updated) booleans.
    """
    wa_id = event['wa_id']
    phone_number_id = event['phone_number_id']
    profile_name = event.get('profile_name')
    message_id = event.get('message_id')
    referral = event.get('referral')
    message_body = event.get('body')
    
    customer_created = False
    customer_updated = False
    
    # Check if message already processed
    if message_id and WhatsAppMessage.objects.filter(message_id=message_id).exists():
        logger.debug(f"Message {message_id} already processed, skipping")
        return False, False
    
    # Use LeadAttributionService for enhanced attribution detection
    attribution = LeadAttributionService.get_attribution_for_webhook(referral, message_body)
    
    # 1. Upsert WhatsAppCustomer
    customer, created = WhatsAppCustomer.objects.get_or_create(
        wa_id=wa_id,
        defaults={
            'profile_name': profile_name,
            'last_message_preview': message_body[:500] if message_body else None,
            'last_message_at': event['timestamp_utc'],
            'lead_created_at': event['timestamp_utc'],
            'lead_status': 'pending',
            # Attribution fields
            'is_from_ad': attribution.get('is_from_ad', False),
            'source_type': attribution.get('source_type', 'unknown'),
            'attribution_source': attribution.get('attribution_source', 'unknown'),
            'ad_platform': attribution.get('ad_platform'),
            'meta_ad_source_id': attribution.get('meta_ad_source_id'),
            'meta_ad_source_type': attribution.get('meta_ad_source_type'),
            'meta_ad_source_url': attribution.get('meta_ad_source_url'),
            'meta_ad_headline': attribution.get('meta_ad_headline'),
            'meta_ad_body': attribution.get('meta_ad_body'),
            'meta_ctwa_clid': attribution.get('meta_ctwa_clid'),
            'meta_fbclid': attribution.get('meta_fbclid'),
            'google_gclid': attribution.get('google_gclid'),
            'meta_campaign_id': attribution.get('meta_campaign_id'),
        }
    )
    
    if created:
        customer_created = True
        logger.info(f"New WhatsApp customer: {wa_id}, source_type: {attribution.get('source_type')}")
    else:
        customer_updated = True
        update_fields = ['last_seen', 'last_message_at', 'total_messages']
        
        if profile_name and profile_name != customer.profile_name:
            customer.profile_name = profile_name
            update_fields.append('profile_name')
        
        if message_body:
            customer.last_message_preview = message_body[:500]
            update_fields.append('last_message_preview')
        
        customer.last_message_at = event['timestamp_utc']
        customer.total_messages = (customer.total_messages or 0) + 1
        customer.save(update_fields=update_fields)
    
    # 2. Upsert WhatsAppNumberConfig
    number_config, _ = WhatsAppNumberConfig.objects.get_or_create(
        phone_number_id=phone_number_id,
        defaults={'display_phone_number': event.get('display_phone_number')}
    )
    number_config.last_webhook_at = timezone.now()
    number_config.webhook_count = (number_config.webhook_count or 0) + 1
    number_config.total_messages_received = (number_config.total_messages_received or 0) + 1
    number_config.save(update_fields=['last_webhook_at', 'webhook_count', 'total_messages_received', 'updated'])
    
    # 3. Upsert WhatsAppCustomerChannel
    channel, channel_created = WhatsAppCustomerChannel.objects.get_or_create(
        customer=customer,
        phone_number_id=phone_number_id,
        defaults={'number_config': number_config}
    )
    channel.message_count = (channel.message_count or 0) + 1
    channel.last_contact_at = event['timestamp_utc']
    channel.save(update_fields=['message_count', 'last_contact_at', 'updated'])
    
    if channel_created:
        customer.total_channels_contacted = customer.channels.count()
        customer.save(update_fields=['total_channels_contacted'])
        
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
            body=message_body,
            media_id=event.get('media_id'),
            timestamp_utc=event['timestamp_utc'],
            raw_payload=event.get('raw_message', {})
        )
    
    # 5. Create/Update Lead
    if customer_created:
        create_or_update_lead(customer, event, attribution)
    
    # 6. Check for location enrichment tags in message
    if message_body and '#' in message_body:
        try:
            from marketing.services import LeadService
            lead = Lead.objects.filter(phone_normalized=wa_id).first()
            if lead:
                lead, enriched = LeadService.enrich_from_whatsapp_tags(lead, message_body)
                if enriched:
                    logger.info(f"Lead location enriched from WhatsApp tags: {lead.state} {lead.pincode}")
        except Exception as e:
            logger.error(f"Error enriching lead from WhatsApp tags: {e}")
    
    return customer_created, customer_updated


def create_or_update_lead(customer, event, attribution):
    """
    Create or update a Lead record for unified lead management.
    """
    try:
        phone_no = f"+{customer.wa_id}" if customer.wa_id else None
        
        # Determine lead source based on attribution
        if customer.source_type == 'ad':
            if customer.ad_platform == 'instagram':
                lead_source = 'instagram_ad'
            elif customer.ad_platform == 'google':
                lead_source = 'google_ad'
            else:
                lead_source = 'whatsapp_ctwa_ad'
        else:
            lead_source = 'whatsapp_inbound'
        
        tags = []
        if customer.is_from_ad:
            tags.extend(['from_ad', 'ctwa'])
        else:
            tags.append('organic')
        
        if customer.attribution_source:
            tags.append(customer.attribution_source)
        
        if customer.ad_platform:
            tags.append(customer.ad_platform)
        
        lead = Lead.objects.filter(phone_no=phone_no).first()
        
        if not lead:
            lead = Lead.objects.create(
                phone_no=phone_no,
                phone_normalized=customer.wa_id,
                name=customer.profile_name or f"WhatsApp Lead {customer.wa_id[-4:]}",
                lead_source=lead_source,
                lead_status='new',
                captured_at=timezone.now(),
                tags=tags,
                notes=f"Auto-created from WhatsApp.\n" +
                      f"Source Type: {customer.source_type}\n" +
                      f"Attribution: {customer.get_attribution_source_display()}\n" +
                      f"From Ad: {'Yes' if customer.is_from_ad else 'No'}\n" +
                      (f"Ad Platform: {customer.ad_platform}\n" if customer.ad_platform else "") +
                      (f"Ad Headline: {customer.meta_ad_headline}\n" if customer.meta_ad_headline else "") +
                      (f"Campaign ID: {customer.meta_campaign_id}\n" if customer.meta_campaign_id else "") +
                      f"First message: {event.get('body', '')[:200] if event.get('body') else 'N/A'}"
            )
            logger.info(f"Created Lead from WhatsApp: {lead.id}, source: {lead_source}")
        else:
            existing_tags = lead.tags or []
            for tag in tags:
                if tag not in existing_tags:
                    existing_tags.append(tag)
            lead.tags = existing_tags
            
            update_note = f"\n\n[{timezone.now()}] Also contacted via WhatsApp."
            if customer.is_from_ad:
                update_note += f" (From {customer.ad_platform or 'Meta'} Ad)"
            lead.notes = (lead.notes or '') + update_note
            lead.save(update_fields=['notes', 'tags', 'updated'])
        
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
        
        # Connected numbers
        context['connected_numbers'] = WhatsAppConnectedNumber.objects.filter(
            is_active=True
        ).order_by('-created')
        
        # Numbers with activity (from webhooks)
        context['numbers'] = WhatsAppNumberConfig.objects.filter(is_active=True).order_by('-last_webhook_at')
        
        # Recent customers
        context['recent_customers'] = WhatsAppCustomer.objects.filter(is_active=True)[:10]
        
        # Stats
        context['total_customers'] = WhatsAppCustomer.objects.filter(is_active=True).count()
        context['total_messages'] = WhatsAppMessage.objects.count()
        context['total_numbers'] = WhatsAppConnectedNumber.objects.filter(is_active=True).count()
        context['ad_leads_count'] = WhatsAppCustomer.objects.filter(is_active=True, is_from_ad=True).count()
        
        # Recent webhook logs
        context['recent_webhooks'] = WhatsAppWebhookLog.objects.all()[:5]
        
        # Meta configs
        context['capi_config'] = MetaConversionConfig.objects.filter(is_active=True).first()
        context['ads_config'] = MetaAdsConfig.objects.filter(is_active=True).first()
        
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
        context['messages'] = self.object.messages.all()[:100]
        context['channels'] = self.object.channels.all()
        
        # Conversion events
        context['conversion_events'] = self.object.conversion_events.all()[:10]
        
        return context


class WhatsAppConnectView(LoginRequiredMixin, TemplateView):
    """Page to connect WhatsApp Business numbers via Embedded Signup."""
    template_name = 'integrations/whatsapp/connect.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Connect WhatsApp Number'
        context['is_integrations'] = True
        context['is_whatsapp'] = True
        
        # Facebook App credentials from settings
        context['fb_app_id'] = getattr(settings, 'FB_APP_ID', '')
        context['fb_config_id'] = getattr(settings, 'FB_CONFIG_ID', '')
        
        # Business Portfolio ID for existing portfolio
        context['meta_business_id'] = getattr(settings, 'META_BUSINESS_ID', '')
        
        # Connected numbers
        context['connected_numbers'] = WhatsAppConnectedNumber.objects.filter(
            is_active=True
        ).order_by('-created')
        
        return context


# =============================================================================
# LEAD PERFORMANCE DASHBOARD
# =============================================================================

class LeadPerformanceDashboardView(LoginRequiredMixin, TemplateView):
    """
    Lead Performance Dashboard showing:
    - Overall summary (leads, conversions, ROAS)
    - Per WhatsApp Number metrics
    - Campaign performance
    - Customer lifecycle
    """
    template_name = 'integrations/whatsapp/lead_performance.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Lead Performance Dashboard'
        context['is_integrations'] = True
        context['is_whatsapp'] = True
        context['is_performance'] = True
        
        # Date range (default last 30 days)
        date_end = timezone.now()
        date_start = date_end - timedelta(days=30)
        
        # Get date range from request
        if self.request.GET.get('date_start'):
            try:
                date_start = timezone.make_aware(
                    datetime.strptime(self.request.GET['date_start'], '%Y-%m-%d')
                )
            except ValueError:
                pass
        
        if self.request.GET.get('date_end'):
            try:
                date_end = timezone.make_aware(
                    datetime.strptime(self.request.GET['date_end'], '%Y-%m-%d')
                )
            except ValueError:
                pass
        
        context['date_start'] = date_start.date()
        context['date_end'] = date_end.date()
        
        # Overall Summary
        overall_stats = LeadConversionService.get_conversion_stats(
            date_start=date_start,
            date_end=date_end
        )
        context['overall_stats'] = overall_stats
        
        # Get ad spend
        ads_service = MetaAdsService()
        if ads_service.is_configured():
            ad_spend = ads_service.get_account_spend_by_date(date_start)
            context['ad_spend'] = ad_spend
            context['roas'] = (overall_stats['revenue'] / ad_spend) if ad_spend > 0 else Decimal('0')
        else:
            context['ad_spend'] = Decimal('0')
            context['roas'] = Decimal('0')
        
        # Per WhatsApp Number metrics
        numbers = WhatsAppNumberConfig.objects.filter(is_active=True)
        number_stats = []
        
        for number in numbers:
            stats = LeadConversionService.get_conversion_stats(
                phone_number_id=number.phone_number_id,
                date_start=date_start,
                date_end=date_end
            )
            stats['number'] = number
            number_stats.append(stats)
        
        context['number_stats'] = number_stats
        
        # Daily reports for charts
        daily_reports = DailyLeadReport.objects.filter(
            report_date__range=(date_start.date(), date_end.date()),
            phone_number_id__isnull=True,
            campaign_id__isnull=True
        ).order_by('report_date')
        context['daily_reports'] = daily_reports
        
        # Lead status breakdown
        leads = WhatsAppCustomer.objects.filter(
            lead_created_at__range=(date_start, date_end),
            is_active=True
        )
        context['pending_leads'] = leads.filter(lead_status='pending').count()
        context['won_leads'] = leads.filter(lead_status='won').count()
        context['lost_leads'] = leads.filter(lead_status='lost').count()
        
        # Campaign performance
        campaign_stats = leads.exclude(
            meta_campaign_id__isnull=True
        ).values('meta_campaign_id').annotate(
            total=Count('id'),
            won=Count('id', filter=Q(lead_status='won')),
            lost=Count('id', filter=Q(lead_status='lost')),
            revenue=Sum('conversion_value', filter=Q(lead_status='won'))
        ).order_by('-total')[:10]
        context['campaign_stats'] = campaign_stats
        
        # Recent conversions
        recent_conversions = WhatsAppCustomer.objects.filter(
            lead_status='won',
            won_at__gte=date_start,
            is_active=True
        ).select_related('converted_order').order_by('-won_at')[:10]
        context['recent_conversions'] = recent_conversions
        
        # Meta CAPI status
        capi_config = MetaConversionConfig.objects.filter(is_active=True).first()
        context['capi_configured'] = bool(capi_config and capi_config.access_token)
        context['capi_config'] = capi_config
        
        # Pending conversions to send
        context['pending_conversion_sends'] = WhatsAppCustomer.objects.filter(
            lead_status='won',
            conversion_sent=False,
            converted_order__isnull=False
        ).count()
        
        return context


class CustomerLifecycleView(LoginRequiredMixin, DetailView):
    """
    Customer Lifecycle View showing lead → order progression.
    """
    model = WhatsAppCustomer
    template_name = 'integrations/whatsapp/customer_lifecycle.html'
    context_object_name = 'customer'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Customer Lifecycle: {self.object.profile_name or self.object.wa_id}'
        context['is_integrations'] = True
        context['is_whatsapp'] = True
        
        # Timeline events
        timeline = []
        
        # Lead created
        timeline.append({
            'type': 'lead_created',
            'date': self.object.lead_created_at or self.object.first_seen,
            'title': 'Lead Created',
            'description': f"Source: {self.object.get_attribution_source_display()}",
            'icon': 'user-plus',
            'color': 'blue',
        })
        
        # First message
        first_message = self.object.messages.order_by('timestamp_utc').first()
        if first_message:
            timeline.append({
                'type': 'first_message',
                'date': first_message.timestamp_utc,
                'title': 'First Message',
                'description': first_message.body[:100] if first_message.body else 'Media message',
                'icon': 'message-circle',
                'color': 'green',
            })
        
        # Messages grouped by day
        messages_by_day = self.object.messages.values('timestamp_utc__date').annotate(
            count=Count('id')
        ).order_by('timestamp_utc__date')
        
        for day_data in messages_by_day[1:5]:  # Skip first (already shown), show next 4
            timeline.append({
                'type': 'messages',
                'date': day_data['timestamp_utc__date'],
                'title': f"{day_data['count']} Messages",
                'description': f"Conversation continued",
                'icon': 'messages',
                'color': 'gray',
            })
        
        # Won/Lost status
        if self.object.lead_status == 'won' and self.object.won_at:
            timeline.append({
                'type': 'converted',
                'date': self.object.won_at,
                'title': 'Converted (Won)',
                'description': f"Order value: ₹{self.object.conversion_value}",
                'icon': 'check-circle',
                'color': 'green',
            })
        elif self.object.lead_status == 'lost' and self.object.lost_at:
            timeline.append({
                'type': 'lost',
                'date': self.object.lost_at,
                'title': 'Marked as Lost',
                'description': 'No conversion within matching period',
                'icon': 'x-circle',
                'color': 'red',
            })
        
        # Conversion sent to Meta
        if self.object.conversion_sent and self.object.conversion_sent_at:
            timeline.append({
                'type': 'capi_sent',
                'date': self.object.conversion_sent_at,
                'title': 'Conversion Sent to Meta',
                'description': 'CAPI event recorded',
                'icon': 'send',
                'color': 'purple',
            })
        
        # Sort timeline by date
        timeline.sort(key=lambda x: x['date'] if x['date'] else timezone.now())
        context['timeline'] = timeline
        
        # Linked order details
        if self.object.converted_order:
            context['order'] = self.object.converted_order
        
        # Linked lead
        if self.object.linked_lead:
            context['lead'] = self.object.linked_lead
        
        # Linked customer
        if self.object.linked_customer:
            context['erp_customer'] = self.object.linked_customer
        
        # All messages
        context['messages'] = self.object.messages.all()[:50]
        
        # Channels contacted
        context['channels'] = self.object.channels.select_related('number_config').all()
        
        return context


# =============================================================================
# API ENDPOINTS
# =============================================================================

@require_http_methods(["POST"])
def save_whatsapp_connection(request):
    """
    API endpoint to save WhatsApp connection from Embedded Signup.
    """
    try:
        data = json.loads(request.body)
        phone_number_id = data.get('phone_number_id')
        waba_id = data.get('waba_id')
        auth_code = data.get('auth_code')
        
        if not phone_number_id or not waba_id:
            return JsonResponse({
                'success': False,
                'error': 'Missing phone_number_id or waba_id'
            }, status=400)
        
        existing = WhatsAppConnectedNumber.objects.filter(
            phone_number_id=phone_number_id
        ).first()
        
        if existing:
            existing.waba_id = waba_id
            existing.status = 'active'
            existing.is_active = True
            existing.save()
            connected_number = existing
            logger.info(f"Updated existing WhatsApp connection: {phone_number_id}")
        else:
            connected_number = WhatsAppConnectedNumber.objects.create(
                phone_number_id=phone_number_id,
                waba_id=waba_id,
                status='active',
                connected_by=request.user if request.user.is_authenticated else None,
                meta_data={
                    'auth_code': auth_code,
                    'connected_at': timezone.now().isoformat()
                }
            )
            logger.info(f"Created new WhatsApp connection: {phone_number_id}")
        
        # Also create WhatsAppNumberConfig for webhook tracking
        number_config, _ = WhatsAppNumberConfig.objects.get_or_create(
            phone_number_id=phone_number_id,
            defaults={'name': f'Connected Number {phone_number_id[-4:]}'}
        )
        number_config.connected_number = connected_number
        number_config.save()
        
        return JsonResponse({
            'success': True,
            'message': 'WhatsApp number connected successfully',
            'data': {
                'id': str(connected_number.id),
                'phone_number_id': connected_number.phone_number_id,
                'waba_id': connected_number.waba_id,
                'status': connected_number.status
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error saving WhatsApp connection: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def disconnect_whatsapp_number(request, number_id):
    """
    API endpoint to disconnect a WhatsApp number.
    """
    try:
        connected_number = WhatsAppConnectedNumber.objects.get(id=number_id)
        connected_number.status = 'disconnected'
        connected_number.is_active = False
        connected_number.save()
        
        logger.info(f"Disconnected WhatsApp number: {connected_number.phone_number_id}")
        
        return JsonResponse({
            'success': True,
            'message': 'Number disconnected successfully'
        })
        
    except WhatsAppConnectedNumber.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Number not found'}, status=404)
    except Exception as e:
        logger.error(f"Error disconnecting WhatsApp number: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def trigger_daily_sync(request):
    """
    Manually trigger the daily sync task.
    """
    from .tasks import sync_lead_statuses, generate_daily_reports
    
    try:
        # Trigger async tasks
        sync_lead_statuses.delay()
        generate_daily_reports.delay()
        
        return JsonResponse({
            'success': True,
            'message': 'Daily sync tasks triggered'
        })
    except Exception as e:
        logger.error(f"Error triggering daily sync: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def send_pending_conversions_api(request):
    """
    Manually trigger sending pending conversions to Meta CAPI.
    """
    from .tasks import send_conversion_event
    from .services import LeadConversionService
    
    try:
        sent, failed = LeadConversionService.send_pending_conversions()
        
        return JsonResponse({
            'success': True,
            'sent': sent,
            'failed': failed,
            'message': f'Sent {sent} conversions, {failed} failed'
        })
    except Exception as e:
        logger.error(f"Error sending pending conversions: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)



# =============================================================================
# DIRECT CONNECT API (for existing WABAs)
# =============================================================================

@csrf_exempt
@require_http_methods(["POST"])
def verify_connection(request):
    """
    Verify connection to Meta WhatsApp Cloud API with provided credentials.
    Tests that the access token and phone number ID are valid.
    """
    try:
        data = json.loads(request.body)
        waba_id = data.get('waba_id')
        phone_number_id = data.get('phone_number_id')
        access_token = data.get('access_token')
        
        if not phone_number_id or not access_token:
            return JsonResponse({
                'success': False,
                'error': 'Phone Number ID and Access Token are required'
            }, status=400)
        
        # Call Meta Graph API to verify credentials
        import requests
        url = f"https://graph.facebook.com/v18.0/{phone_number_id}"
        params = {
            'access_token': access_token,
            'fields': 'display_phone_number,verified_name,code_verification_status,quality_rating'
        }
        
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            api_data = response.json()
            return JsonResponse({
                'success': True,
                'phone_number': api_data.get('display_phone_number'),
                'verified_name': api_data.get('verified_name'),
                'status': api_data.get('code_verification_status', 'Unknown'),
                'quality_rating': api_data.get('quality_rating', 'Unknown')
            })
        else:
            error_data = response.json()
            error_message = error_data.get('error', {}).get('message', 'Unknown error')
            return JsonResponse({
                'success': False,
                'error': f"Meta API Error: {error_message}"
            }, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error verifying WhatsApp connection: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def direct_connect_number(request):
    """
    Direct Connect API - Connect an existing WABA number that you already own.
    This bypasses Embedded Signup and directly registers the number using provided credentials.
    """
    try:
        data = json.loads(request.body)
        waba_id = data.get('waba_id')
        phone_number_id = data.get('phone_number_id')
        display_phone_number = data.get('display_phone_number')
        display_name = data.get('display_name')
        access_token = data.get('access_token')
        
        if not waba_id or not phone_number_id or not access_token:
            return JsonResponse({
                'success': False,
                'error': 'WABA ID, Phone Number ID, and Access Token are required'
            }, status=400)
        
        # Optionally verify the connection first
        import requests
        url = f"https://graph.facebook.com/v18.0/{phone_number_id}"
        params = {
            'access_token': access_token,
            'fields': 'display_phone_number,verified_name'
        }
        
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code != 200:
            error_data = response.json()
            error_message = error_data.get('error', {}).get('message', 'Unable to verify connection')
            return JsonResponse({
                'success': False,
                'error': f"Invalid credentials: {error_message}"
            }, status=400)
        
        # Get additional info from API response
        api_data = response.json()
        if not display_phone_number:
            display_phone_number = api_data.get('display_phone_number')
        if not display_name:
            display_name = api_data.get('verified_name')
        
        # Create or update WhatsAppConnectedNumber
        existing = WhatsAppConnectedNumber.objects.filter(
            phone_number_id=phone_number_id
        ).first()
        
        if existing:
            existing.waba_id = waba_id
            existing.display_phone_number = display_phone_number
            existing.display_name = display_name
            existing.access_token = access_token
            existing.status = 'active'
            existing.is_active = True
            existing.webhook_verified = False  # User needs to configure webhook in Meta
            existing.meta_data = {
                'connection_type': 'direct',
                'connected_at': timezone.now().isoformat(),
            }
            existing.save()
            connected_number = existing
            logger.info(f"Updated existing WhatsApp connection via Direct Connect: {phone_number_id}")
        else:
            connected_number = WhatsAppConnectedNumber.objects.create(
                waba_id=waba_id,
                phone_number_id=phone_number_id,
                display_phone_number=display_phone_number,
                display_name=display_name,
                access_token=access_token,
                status='active',
                webhook_verified=False,
                connected_by=request.user if request.user.is_authenticated else None,
                meta_data={
                    'connection_type': 'direct',
                    'connected_at': timezone.now().isoformat(),
                }
            )
            logger.info(f"Created new WhatsApp connection via Direct Connect: {phone_number_id}")
        
        # Also create WhatsAppNumberConfig for webhook tracking
        number_config, _ = WhatsAppNumberConfig.objects.get_or_create(
            phone_number_id=phone_number_id,
            defaults={
                'name': display_name or f'Number {phone_number_id[-4:]}',
                'display_phone_number': display_phone_number
            }
        )
        number_config.connected_number = connected_number
        number_config.save()
        
        return JsonResponse({
            'success': True,
            'message': 'WhatsApp number connected successfully via Direct Connect',
            'data': {
                'id': str(connected_number.id),
                'phone_number_id': connected_number.phone_number_id,
                'waba_id': connected_number.waba_id,
                'display_name': connected_number.display_name,
                'display_phone_number': connected_number.display_phone_number,
                'status': connected_number.status
            },
            'next_steps': [
                'Configure webhook callback URL in Meta Developer Dashboard',
                'Subscribe to "messages" webhook field',
                'Test by sending a message to the connected number'
            ]
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error in Direct Connect: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
