"""
Wabis WhatsApp BSP Integration Views

Webhook receiver and management UI.
"""

import json
import logging
import time
from datetime import datetime

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import transaction
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, ListView, DetailView
from django.urls import reverse

from .models import (
    WabisConfig,
    WabisNumber,
    WabisCustomer,
    WabisCustomerChannel,
    WabisMessage,
    WabisWebhookLog,
)
from .services import WabisWebhookProcessor

logger = logging.getLogger(__name__)


# =============================================================================
# WEBHOOK ENDPOINTS
# =============================================================================

@csrf_exempt
@require_http_methods(["GET", "POST"])
def wabis_webhook(request):
    """
    Webhook endpoint for Wabis WhatsApp BSP.
    - GET: Webhook verification
    - POST: Receive incoming messages/events
    """
    if request.method == "GET":
        return webhook_verify(request)
    else:
        return webhook_receive(request)


def webhook_verify(request):
    """
    Handle webhook verification handshake.
    Wabis/Meta sends: hub.mode, hub.verify_token, hub.challenge
    """
    mode = request.GET.get('hub.mode')
    token = request.GET.get('hub.verify_token')
    challenge = request.GET.get('hub.challenge')
    
    # Get verify token from config or settings
    config = WabisConfig.objects.filter(is_active=True).first()
    verify_token = config.verify_token if config else getattr(settings, 'WABIS_VERIFY_TOKEN', 'elvis_wabis_verify_2024')
    
    logger.info(f"Wabis webhook verification: mode={mode}, token_match={token == verify_token}")
    
    if mode == 'subscribe' and token == verify_token:
        logger.info("Wabis webhook verified successfully")
        return HttpResponse(challenge, content_type='text/plain', status=200)
    else:
        logger.warning(f"Wabis webhook verification failed")
        return HttpResponse('Verification failed', status=403)


def webhook_receive(request):
    """
    Handle incoming webhook POST from Wabis.
    Always return 200 to prevent retries.
    """
    start_time = time.time()
    webhook_log = None
    
    try:
        # Parse payload
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            logger.error("Invalid JSON in Wabis webhook payload")
            return HttpResponse('OK', status=200)
        
        # Extract headers
        headers = {
            'content-type': request.headers.get('Content-Type'),
            'x-hub-signature': request.headers.get('X-Hub-Signature-256'),
        }
        
        # Create webhook log - ALWAYS log raw payload for mapping
        webhook_log = WabisWebhookLog.objects.create(
            payload=payload,
            headers=headers,
            event_type='webhook_received'
        )
        
        # Process webhook
        processor = WabisWebhookProcessor()
        result = processor.process_webhook(payload)
        
        # Update log
        processing_time = int((time.time() - start_time) * 1000)
        webhook_log.phone_number_id = result.get('phone_number_id')
        webhook_log.event_type = result.get('event_type', 'messages')
        webhook_log.processed = result.get('success', False)
        webhook_log.processing_time_ms = processing_time
        webhook_log.messages_processed = result.get('messages_processed', 0)
        webhook_log.customers_created = result.get('customers_created', 0)
        webhook_log.customers_updated = result.get('customers_updated', 0)
        webhook_log.error_message = result.get('error')
        webhook_log.save()
        
        # Update config last_webhook_at
        WabisConfig.objects.filter(is_active=True).update(last_webhook_at=timezone.now())
        
        logger.info(f"Wabis webhook processed: {result}")
        
    except Exception as e:
        logger.error(f"Wabis webhook error: {e}", exc_info=True)
        if webhook_log:
            webhook_log.processed = False
            webhook_log.error_message = str(e)
            webhook_log.save()
    
    return HttpResponse('OK', status=200)


# =============================================================================
# MANAGEMENT UI VIEWS
# =============================================================================

class WabisDashboardView(LoginRequiredMixin, TemplateView):
    """Wabis integration dashboard."""
    template_name = 'integrations/wabis/dashboard.html'
    
    def get_context_data(self, **kwargs):
        from django.conf import settings
        
        context = super().get_context_data(**kwargs)
        context['title'] = 'Wabis WhatsApp Integration'
        context['is_integrations'] = True
        context['is_wabis'] = True
        
        # Config
        context['config'] = WabisConfig.objects.filter(is_active=True).first()
        
        # API Token status
        context['api_token_configured'] = bool(getattr(settings, 'WABIS_API_TOKEN', ''))
        
        # Webhook URL
        context['webhook_url'] = self.request.build_absolute_uri(
            reverse('integrations:wabis:webhook')
        )
        
        # Numbers
        context['numbers'] = WabisNumber.objects.filter(is_active=True).order_by('-last_message_at')
        
        # Stats
        context['total_customers'] = WabisCustomer.objects.filter(is_active=True).count()
        context['total_messages'] = WabisMessage.objects.count()
        context['ads_customers'] = WabisCustomer.objects.filter(is_active=True, source_type='ads').count()
        context['organic_customers'] = WabisCustomer.objects.filter(is_active=True, source_type='organic').count()
        
        # Recent customers
        context['recent_customers'] = WabisCustomer.objects.filter(is_active=True).order_by('-last_message_at')[:10]
        
        # Recent webhooks
        context['recent_webhooks'] = WabisWebhookLog.objects.all()[:10]
        
        # Recent errors
        context['recent_errors'] = WabisWebhookLog.objects.filter(
            processed=False,
            error_message__isnull=False
        )[:5]
        
        return context


class WabisNumberListView(LoginRequiredMixin, ListView):
    """List registered WhatsApp numbers."""
    model = WabisNumber
    template_name = 'integrations/wabis/number_list.html'
    context_object_name = 'numbers'
    
    def get_queryset(self):
        return WabisNumber.objects.filter(is_active=True).order_by('-last_message_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'WhatsApp Numbers'
        context['is_integrations'] = True
        context['is_wabis'] = True
        return context


class WabisCustomerListView(LoginRequiredMixin, ListView):
    """List WhatsApp customers/leads."""
    model = WabisCustomer
    template_name = 'integrations/wabis/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 50
    
    def get_queryset(self):
        qs = WabisCustomer.objects.filter(is_active=True).order_by('-last_message_at')
        
        # Filters
        source = self.request.GET.get('source')
        status = self.request.GET.get('status')
        number = self.request.GET.get('number')
        
        if source:
            qs = qs.filter(source_type=source)
        if status:
            qs = qs.filter(conversion_status=status)
        if number:
            qs = qs.filter(channels__number_id=number)
        
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'WhatsApp Leads'
        context['is_integrations'] = True
        context['is_wabis'] = True
        context['numbers'] = WabisNumber.objects.filter(is_active=True)
        return context


class WabisCustomerDetailView(LoginRequiredMixin, DetailView):
    """View WhatsApp customer details."""
    model = WabisCustomer
    template_name = 'integrations/wabis/customer_detail.html'
    context_object_name = 'customer'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'WhatsApp: {self.object.profile_name or self.object.wa_id}'
        context['messages'] = self.object.messages.all()[:100]
        context['channels'] = self.object.channels.select_related('number').all()
        return context


class WabisWebhookLogListView(LoginRequiredMixin, ListView):
    """View webhook logs."""
    model = WabisWebhookLog
    template_name = 'integrations/wabis/webhook_logs.html'
    context_object_name = 'logs'
    paginate_by = 50
    
    def get_queryset(self):
        qs = WabisWebhookLog.objects.all().order_by('-created')
        
        status = self.request.GET.get('status')
        if status == 'error':
            qs = qs.filter(processed=False)
        elif status == 'success':
            qs = qs.filter(processed=True)
        
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Webhook Logs'
        context['is_integrations'] = True
        context['is_wabis'] = True
        return context


# =============================================================================
# API ENDPOINTS
# =============================================================================

@csrf_exempt
@require_http_methods(["POST"])
def add_wabis_number(request):
    """Add a new WhatsApp number."""
    try:
        data = json.loads(request.body)
        
        phone_number_id = data.get('phone_number_id')
        display_phone_number = data.get('display_phone_number')
        display_name = data.get('display_name')
        waba_id = data.get('waba_id', '')
        
        if not phone_number_id or not display_phone_number or not display_name:
            return JsonResponse({
                'success': False,
                'error': 'Required fields: phone_number_id, display_phone_number, display_name'
            }, status=400)
        
        number, created = WabisNumber.objects.update_or_create(
            phone_number_id=phone_number_id,
            defaults={
                'display_phone_number': display_phone_number,
                'display_name': display_name,
                'waba_id': waba_id,
                'status': 'active',
                'is_active': True,
            }
        )
        
        return JsonResponse({
            'success': True,
            'created': created,
            'data': {
                'id': str(number.id),
                'phone_number_id': number.phone_number_id,
                'display_name': number.display_name,
            }
        })
        
    except Exception as e:
        logger.error(f"Error adding Wabis number: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def delete_wabis_number(request, pk):
    """Delete (deactivate) a WhatsApp number."""
    try:
        number = WabisNumber.objects.get(id=pk)
        number.is_active = False
        number.status = 'inactive'
        number.save()
        
        return JsonResponse({'success': True})
    except WabisNumber.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Number not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def sync_status(request):
    """Get sync status for health checks."""
    config = WabisConfig.objects.filter(is_active=True).first()
    
    # Get numbers with activity
    numbers = WabisNumber.objects.filter(is_active=True).values(
        'id', 'display_name', 'phone_number_id', 'status',
        'last_message_at', 'total_messages_received'
    )
    
    # Recent webhook status
    recent_webhooks = WabisWebhookLog.objects.filter(
        created__gte=timezone.now() - timezone.timedelta(hours=24)
    ).count()
    recent_errors = WabisWebhookLog.objects.filter(
        created__gte=timezone.now() - timezone.timedelta(hours=24),
        processed=False
    ).count()
    
    return JsonResponse({
        'status': 'ok' if config and config.connection_status == 'connected' else 'disconnected',
        'last_webhook': config.last_webhook_at.isoformat() if config and config.last_webhook_at else None,
        'numbers': list(numbers),
        'webhooks_24h': recent_webhooks,
        'errors_24h': recent_errors,
    })


@require_http_methods(["POST"])
def trigger_api_sync(request):
    """
    Trigger a sync of subscribers from Wabis API.
    Reads credentials from database config or settings.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
    
    # Try to get from database config first
    config = WabisConfig.objects.filter(is_active=True).first()
    
    if config and config.api_key and config.whatsapp_bot_id:
        api_token = config.api_key
        bot_id = config.whatsapp_bot_id
    else:
        # Fallback to settings
        from django.conf import settings
        api_token = getattr(settings, 'WABIS_API_TOKEN', '')
        bot_id = getattr(settings, 'WABIS_WHATSAPP_BOT_ID', '')
    
    if not api_token:
        return JsonResponse({
            'success': False, 
            'error': 'API Token not configured. Go to Settings to add it.'
        }, status=400)
    
    if not bot_id:
        return JsonResponse({
            'success': False,
            'error': 'WhatsApp Bot ID not configured. Go to Settings to add it.'
        }, status=400)
    
    try:
        from .api_client import WabisSubscriberSyncService
        
        sync_service = WabisSubscriberSyncService(api_token=api_token)
        stats = sync_service.sync_all_subscribers(whatsapp_bot_id=bot_id)
        
        # Update last sync time
        config = WabisConfig.objects.filter(is_active=True).first()
        if config:
            config.last_sync_at = timezone.now()
            config.save()
        
        return JsonResponse({
            'success': True,
            'message': f"Sync completed: {stats['created']} created, {stats['updated']} updated",
            'stats': stats
        })
    except Exception as e:
        logger.error(f"API sync error: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# =============================================================================
# CONFIGURATION VIEWS
# =============================================================================

class WabisConfigView(LoginRequiredMixin, TemplateView):
    """Wabis configuration page with setup instructions."""
    template_name = 'integrations/wabis/config.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Wabis Configuration'
        context['is_integrations'] = True
        context['is_wabis'] = True
        
        # Get or create config
        context['config'] = WabisConfig.objects.filter(is_active=True).first()
        
        # Webhook URL
        context['webhook_url'] = self.request.build_absolute_uri(
            reverse('integrations:wabis:webhook')
        )
        
        # Stats
        context['total_customers'] = WabisCustomer.objects.filter(is_active=True).count()
        context['total_messages'] = WabisMessage.objects.count()
        context['numbers_count'] = WabisNumber.objects.filter(is_active=True).count()
        
        return context


@require_http_methods(["POST"])
def save_wabis_config(request):
    """Save Wabis configuration (API Token, Bot ID)."""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
    
    try:
        data = json.loads(request.body)
        api_token = data.get('api_token', '').strip()
        whatsapp_bot_id = data.get('whatsapp_bot_id', '').strip()
        
        if not api_token:
            return JsonResponse({'success': False, 'error': 'API Token is required'}, status=400)
        
        if not whatsapp_bot_id:
            return JsonResponse({'success': False, 'error': 'WhatsApp Bot ID is required'}, status=400)
        
        # Get or create config
        config, created = WabisConfig.objects.get_or_create(
            is_active=True,
            defaults={'name': 'Default Wabis Config'}
        )
        
        config.api_key = api_token
        config.whatsapp_bot_id = whatsapp_bot_id
        config.connection_status = 'connected'
        config.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Configuration saved successfully'
        })
        
    except Exception as e:
        logger.error(f"Config save error: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def test_wabis_connection(request):
    """Test Wabis API connection with provided credentials."""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
    
    try:
        data = json.loads(request.body)
        api_token = data.get('api_token', '').strip()
        whatsapp_bot_id = data.get('whatsapp_bot_id', '').strip()
        
        if not api_token or not whatsapp_bot_id:
            return JsonResponse({
                'success': False, 
                'error': 'API Token and Bot ID are required'
            }, status=400)
        
        from .api_client import WabisAPIClient
        
        client = WabisAPIClient(api_token=api_token)
        
        # Try to fetch subscribers to test connection
        response = client.get_subscribers_list(
            whatsapp_bot_id=whatsapp_bot_id,
            limit=1
        )
        
        if response.get('success'):
            # Get total count if available
            subscriber_count = len(response.get('data', []))
            
            return JsonResponse({
                'success': True,
                'message': 'Connection successful',
                'subscriber_count': subscriber_count
            })
        else:
            return JsonResponse({
                'success': False,
                'error': response.get('message', 'API returned error')
            })
            
    except Exception as e:
        logger.error(f"Connection test error: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
