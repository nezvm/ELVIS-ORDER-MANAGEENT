"""
Shopify Integration Portal Views

All views for the comprehensive Shopify Integration Portal with 7 tabs:
1. Overview
2. Connect Store  
3. Sync Rules
4. Connectors
5. Test & Diagnostics
6. Logs
7. Instructions
"""
import json
import logging
from datetime import datetime

from django.shortcuts import get_object_or_404, redirect
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from integrations.models import (
    ShopifyStore, ShopifyOrder, ShopifyAbandonedCheckout,
    ShopifyWebhookLog, ShopifyEventInbox, ShopifyOutbox, ShopifyExternalMap
)
from marketing.models import Lead
from .portal_services import (
    ShopifyConnectionService,
    ShopifyChannelSplitService,
    ShopifyCustomerSyncService,
    ShopifyOrderSyncService,
    ShopifyFulfillmentPushService,
    ShopifyAbandonedSyncService,
    ShopifyPortalStatsService,
    ShopifyAPIClient,
    ShopifyEventInboxService,
)

logger = logging.getLogger(__name__)


class ShopifyPortalView(LoginRequiredMixin, TemplateView):
    """Main Shopify Integration Portal with all 7 tabs."""
    template_name = 'integrations/shopify/portal.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        
        store = get_object_or_404(ShopifyStore, pk=pk) if pk else None
        
        # If no store, show the store selection / create page
        if not store:
            context['stores'] = ShopifyStore.objects.filter(is_active=True)
            context['no_store'] = True
            context['title'] = 'Shopify Integration Portal'
            context['is_integrations'] = True
            context['is_shopify'] = True
            return context
        
        # Get stats
        stats = ShopifyPortalStatsService.get_overview_stats(store)
        
        # Get connector statuses
        connectors = self._get_connector_statuses(store)
        
        # Recent logs
        recent_webhook_logs = ShopifyWebhookLog.objects.filter(store=store).order_by('-created')[:20]
        recent_outbox_logs = ShopifyOutbox.objects.filter(store=store).order_by('-created')[:20]
        recent_inbox_logs = ShopifyEventInbox.objects.filter(store=store).order_by('-received_at')[:20]
        
        # Abandoned recovery stats
        total_abandoned = ShopifyAbandonedCheckout.objects.filter(store=store).count()
        recovered_today = ShopifyAbandonedCheckout.objects.filter(
            store=store, is_recovered=True,
            completed_at__date=timezone.now().date()
        ).count()
        
        context.update({
            'title': f'Shopify Integration Portal - {store}',
            'store': store,
            'stats': stats,
            'connectors': connectors,
            'recent_webhook_logs': recent_webhook_logs,
            'recent_outbox_logs': recent_outbox_logs,
            'recent_inbox_logs': recent_inbox_logs,
            'total_abandoned': total_abandoned,
            'recovered_today': recovered_today,
            'cod_keywords_json': json.dumps(store.cod_keywords or ['COD', 'Cash on Delivery']),
            'active_tab': self.request.GET.get('tab', 'overview'),
            'is_integrations': True,
            'is_shopify': True,
        })
        return context
    
    def _get_connector_statuses(self, store: ShopifyStore) -> list:
        """Build connector status info."""
        return [
            {
                'name': 'Store Connection',
                'key': 'connection',
                'status': 'ON' if store.status == 'CONNECTED' else 'OFF',
                'description': 'OAuth / Token Setup',
                'last_run': store.installed_at,
                'icon': 'fa-plug',
                'color': 'green' if store.status == 'CONNECTED' else 'gray',
            },
            {
                'name': 'Orders Inbound',
                'key': 'orders',
                'status': 'ON' if store.sync_orders else 'OFF',
                'description': 'Sync orders from Shopify → ERP',
                'last_run': store.last_orders_sync_at,
                'icon': 'fa-shopping-cart',
                'color': 'blue' if store.sync_orders else 'gray',
            },
            {
                'name': 'Customers Inbound',
                'key': 'customers',
                'status': 'ON' if store.sync_customers else 'OFF',
                'description': 'Sync customers from Shopify → ERP Leads',
                'last_run': store.last_customers_sync_at,
                'icon': 'fa-users',
                'color': 'purple' if store.sync_customers else 'gray',
            },
            {
                'name': 'Fulfillment Outbound',
                'key': 'fulfillment',
                'status': 'ON' if store.auto_fulfill else 'OFF',
                'description': 'Push fulfillment from ERP → Shopify',
                'last_run': ShopifyOutbox.objects.filter(store=store, status='DONE').order_by('-sent_at').values_list('sent_at', flat=True).first(),
                'icon': 'fa-truck',
                'color': 'orange' if store.auto_fulfill else 'gray',
            },
            {
                'name': 'Abandoned Checkout',
                'key': 'abandoned',
                'status': 'ON' if store.sync_abandoned_checkouts else 'OFF',
                'description': f'Sync abandoned checkouts → Leads (every {store.abandoned_sync_interval_minutes}m)',
                'last_run': store.last_abandoned_sync_at,
                'icon': 'fa-cart-arrow-down',
                'color': 'yellow' if store.sync_abandoned_checkouts else 'gray',
            },
        ]


class ShopifyPortalSelectView(LoginRequiredMixin, TemplateView):
    """Select or create a Shopify store for the portal."""
    template_name = 'integrations/shopify/portal_select.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stores = ShopifyStore.objects.filter(is_active=True)
        context['stores'] = stores
        context['title'] = 'Shopify Integration Portal'
        context['is_integrations'] = True
        context['is_shopify'] = True
        
        # If only one store, redirect directly
        if stores.count() == 1:
            context['redirect_to'] = stores.first().get_portal_url()
        
        return context
    
    def get(self, request, *args, **kwargs):
        stores = ShopifyStore.objects.filter(is_active=True)
        if stores.count() == 1:
            return redirect('integrations:shopify_portal', pk=str(stores.first().pk))
        return super().get(request, *args, **kwargs)


# ============================================================
# API Endpoints for Portal
# ============================================================

@login_required
@require_POST
def api_connect_store(request, pk):
    """Connect/save credentials for a Shopify store."""
    try:
        store = get_object_or_404(ShopifyStore, pk=pk)
        data = json.loads(request.body)
        
        access_token = data.get('access_token', '').strip()
        api_version = data.get('api_version', '2024-01')
        shop_domain = data.get('shop_domain', '').strip()
        
        if shop_domain:
            store.shop_domain = shop_domain
            store.store_name = store.store_name or shop_domain
            store.name = store.name or shop_domain
        
        if not access_token:
            return JsonResponse({'success': False, 'message': 'Access token is required'}, status=400)
        
        result = ShopifyConnectionService.connect_store(store, access_token, api_version)
        return JsonResponse(result)
    except Exception as e:
        logger.error(f"Connect store error: {e}")
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@require_POST
def api_disconnect_store(request, pk):
    """Disconnect a Shopify store."""
    try:
        store = get_object_or_404(ShopifyStore, pk=pk)
        result = ShopifyConnectionService.disconnect_store(store)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
def api_verify_permissions(request, pk):
    """Verify Shopify API permissions."""
    try:
        store = get_object_or_404(ShopifyStore, pk=pk)
        result = ShopifyConnectionService.verify_permissions(store)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@require_POST
def api_register_webhooks(request, pk):
    """Register Shopify webhooks."""
    try:
        store = get_object_or_404(ShopifyStore, pk=pk)
        data = json.loads(request.body)
        base_url = data.get('base_url') or request.build_absolute_uri('/').rstrip('/')
        result = ShopifyConnectionService.register_webhooks(store, base_url)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@require_POST
def api_save_sync_rules(request, pk):
    """Save sync rules configuration."""
    try:
        store = get_object_or_404(ShopifyStore, pk=pk)
        data = json.loads(request.body)
        
        # Update COD keywords
        cod_keywords = data.get('cod_keywords', [])
        if isinstance(cod_keywords, list):
            store.cod_keywords = cod_keywords
        
        # Update toggles
        store.treat_pending_cod_as_confirmed = data.get('treat_pending_cod_as_confirmed', True)
        store.create_lead_for_every_customer = data.get('create_lead_for_every_customer', True)
        store.auto_promote_lead_to_customer = data.get('auto_promote_lead_to_customer', True)
        store.sync_orders = data.get('sync_orders', True)
        store.sync_customers = data.get('sync_customers', True)
        store.sync_abandoned_checkouts = data.get('sync_abandoned_checkouts', True)
        store.abandoned_sync_interval_minutes = int(data.get('abandoned_sync_interval_minutes', 15))
        store.auto_fulfill = data.get('auto_fulfill', False)
        store.push_partial_fulfillments = data.get('push_partial_fulfillments', True)
        
        store.save()
        return JsonResponse({'success': True, 'message': 'Sync rules saved successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
def api_get_shop_info(request, pk):
    """Test: Get shop info from Shopify."""
    try:
        store = get_object_or_404(ShopifyStore, pk=pk)
        if not store.access_token:
            return JsonResponse({'success': False, 'message': 'No access token configured'})
        
        client = ShopifyAPIClient(store)
        status_code, response = client.get_shop()
        
        if status_code == 200:
            shop = response.get('shop', {})
            return JsonResponse({
                'success': True,
                'shop_name': shop.get('name'),
                'shop_email': shop.get('email'),
                'shop_domain': shop.get('domain'),
                'currency': shop.get('currency'),
                'country': shop.get('country_name'),
                'timezone': shop.get('iana_timezone'),
                'plan': shop.get('plan_display_name'),
            })
        else:
            return JsonResponse({'success': False, 'message': f'API error {status_code}: {response.get("errors", "Unknown error")}',
                                 'status_code': status_code})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
def api_test_read_order(request, pk):
    """Test: Read a sample order from Shopify."""
    try:
        store = get_object_or_404(ShopifyStore, pk=pk)
        order_id = request.GET.get('order_id', '')
        
        if not store.access_token:
            return JsonResponse({'success': False, 'message': 'No access token configured'})
        
        client = ShopifyAPIClient(store)
        
        if order_id:
            status_code, response = client.get_order(order_id)
        else:
            # Get latest order
            status_code, response = client.get_orders({'limit': 1, 'status': 'any'})
            if status_code == 200:
                orders = response.get('orders', [])
                if orders:
                    return JsonResponse({'success': True, 'order': orders[0], 'note': 'Showing latest order'})
                return JsonResponse({'success': True, 'order': None, 'note': 'No orders found'})
        
        if status_code == 200:
            return JsonResponse({'success': True, 'order': response.get('order', response)})
        else:
            return JsonResponse({'success': False, 'message': f'API error {status_code}', 'response': response})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
def api_test_read_customer(request, pk):
    """Test: Read a customer from Shopify."""
    try:
        store = get_object_or_404(ShopifyStore, pk=pk)
        customer_id = request.GET.get('customer_id', '')
        
        if not store.access_token:
            return JsonResponse({'success': False, 'message': 'No access token configured'})
        
        if not customer_id:
            return JsonResponse({'success': False, 'message': 'Customer ID required'})
        
        client = ShopifyAPIClient(store)
        status_code, response = client.get_customer(customer_id)
        
        if status_code == 200:
            return JsonResponse({'success': True, 'customer': response.get('customer', response)})
        else:
            return JsonResponse({'success': False, 'message': f'API error {status_code}', 'response': response})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@require_POST
def api_simulate_webhook(request, pk):
    """Simulate receiving a webhook and show what ERP would do."""
    try:
        store = get_object_or_404(ShopifyStore, pk=pk)
        data = json.loads(request.body)
        
        topic = data.get('topic', 'orders/create')
        payload = data.get('payload', {})
        
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                return JsonResponse({'success': False, 'message': 'Invalid JSON payload'})
        
        # Simulate the processing
        result = {
            'topic': topic,
            'payload_entity_id': payload.get('id'),
        }
        
        if topic.startswith('orders/'):
            # Channel split analysis
            channel_info = ShopifyChannelSplitService.explain_channel(store, payload)
            result['channel'] = channel_info['channel']
            result['channel_reasons'] = channel_info['reasons']
            result['financial_status'] = channel_info['financial_status']
            result['gateway'] = channel_info['gateway']
            result['gateway_is_cod'] = channel_info['gateway_is_cod']
            
            # Would create lead?
            customer = payload.get('customer', {}) or {}
            shipping = payload.get('shipping_address', {}) or {}
            phone = customer.get('phone') or shipping.get('phone') or payload.get('phone', '')
            email = customer.get('email') or payload.get('email', '')
            result['would_create_lead'] = bool(phone or email)
            result['would_create_order'] = True
            
            # Check existing
            existing = ShopifyOrder.objects.filter(
                store=store, shopify_order_id=str(payload.get('id', ''))
            ).first()
            result['would_update_existing'] = existing is not None
            
        elif topic.startswith('checkouts/'):
            phone = payload.get('email') or ''
            email = payload.get('email', '')
            result['would_create_lead'] = True
            result['would_create_order'] = False
            result['channel'] = 'N/A (Abandoned Checkout)'
            
        elif topic.startswith('customers/'):
            result['would_create_lead'] = store.create_lead_for_every_customer
            result['would_create_order'] = False
            result['channel'] = 'N/A (Customer)'
        
        result['success'] = True
        result['note'] = 'This is a simulation - no data was actually saved'
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@require_POST
def api_test_fulfillment_push(request, pk):
    """Test fulfillment push to Shopify."""
    try:
        store = get_object_or_404(ShopifyStore, pk=pk)
        data = json.loads(request.body)
        
        shopify_order_id = data.get('shopify_order_id', '').strip()
        erp_order_id = data.get('erp_order_id', shopify_order_id)
        tracking_number = data.get('tracking_number', '').strip()
        tracking_url = data.get('tracking_url', '').strip()
        courier_name = data.get('courier_name', '').strip()
        
        if not shopify_order_id:
            return JsonResponse({'success': False, 'message': 'Shopify Order ID required'})
        if not tracking_number:
            return JsonResponse({'success': False, 'message': 'Tracking number required'})
        
        result = ShopifyFulfillmentPushService.push_fulfillment(
            store=store,
            erp_order_id=erp_order_id or shopify_order_id,
            shopify_order_id=shopify_order_id,
            tracking_number=tracking_number,
            tracking_url=tracking_url,
            courier_name=courier_name,
        )
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@require_POST
def api_run_abandoned_sync(request, pk):
    """Trigger abandoned checkout sync manually."""
    try:
        store = get_object_or_404(ShopifyStore, pk=pk)
        result = ShopifyAbandonedSyncService.sync_abandoned_checkouts(store)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
def api_get_logs(request, pk):
    """Get paginated logs for the store."""
    try:
        store = get_object_or_404(ShopifyStore, pk=pk)
        log_type = request.GET.get('type', 'webhook')  # webhook or outbox
        page = int(request.GET.get('page', 1))
        page_size = 25
        topic_filter = request.GET.get('topic', '')
        status_filter = request.GET.get('status', '')
        
        offset = (page - 1) * page_size
        
        if log_type == 'webhook':
            qs = ShopifyWebhookLog.objects.filter(store=store)
            if topic_filter:
                qs = qs.filter(webhook_topic=topic_filter)
            qs = qs.order_by('-created')[offset:offset + page_size]
            
            logs = []
            for log in qs:
                logs.append({
                    'id': str(log.id),
                    'timestamp': log.created.isoformat() if log.created else None,
                    'topic': log.webhook_topic,
                    'entity_id': log.payload.get('id') if log.payload else None,
                    'action': log.action_taken,
                    'status': 'processed' if log.processed else 'failed',
                    'error': log.error_message,
                    'processing_time_ms': log.processing_time_ms,
                })
        else:  # outbox
            qs = ShopifyOutbox.objects.filter(store=store)
            if status_filter:
                qs = qs.filter(status=status_filter)
            qs = qs.order_by('-created')[offset:offset + page_size]
            
            logs = []
            for log in qs:
                logs.append({
                    'id': str(log.id),
                    'timestamp': log.created.isoformat() if log.created else None,
                    'type': log.type,
                    'ref_id': log.ref_internal_id,
                    'shopify_id': log.ref_shopify_id,
                    'status': log.status,
                    'retries': log.retries,
                    'error': log.last_error,
                    'sent_at': log.sent_at.isoformat() if log.sent_at else None,
                })
        
        # Get distinct topics for filter
        topics = list(ShopifyWebhookLog.objects.filter(store=store).values_list('webhook_topic', flat=True).distinct())
        
        return JsonResponse({
            'success': True,
            'logs': logs,
            'page': page,
            'topics': topics,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@require_POST
def api_replay_event(request, pk):
    """Replay a failed event from the inbox."""
    try:
        store = get_object_or_404(ShopifyStore, pk=pk)
        data = json.loads(request.body)
        event_id = data.get('event_id', '')
        
        if not event_id:
            return JsonResponse({'success': False, 'message': 'Event ID required'})
        
        # Check webhook log or inbox
        log_type = data.get('type', 'webhook')
        
        if log_type == 'webhook':
            log = get_object_or_404(ShopifyWebhookLog, pk=event_id, store=store)
            # Re-process the webhook
            from integrations.shopify.services import ShopifyOrderService, ShopifyCheckoutService
            topic = log.webhook_topic
            payload = log.payload
            
            if topic.startswith('orders/'):
                ShopifyOrderService.process_order_webhook(store, payload, log)
            elif topic.startswith('checkouts/'):
                ShopifyCheckoutService.process_checkout_webhook(store, payload, log)
            
            return JsonResponse({'success': True, 'message': 'Event replayed successfully'})
        
        elif log_type == 'outbox':
            outbox = get_object_or_404(ShopifyOutbox, pk=event_id, store=store)
            outbox.status = 'PENDING'
            outbox.retries = 0
            outbox.last_error = None
            outbox.save()
            return JsonResponse({'success': True, 'message': 'Outbox item queued for retry'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@require_POST
def api_toggle_connector(request, pk):
    """Toggle a connector on/off."""
    try:
        store = get_object_or_404(ShopifyStore, pk=pk)
        data = json.loads(request.body)
        connector = data.get('connector', '')
        enabled = data.get('enabled', False)
        
        field_map = {
            'orders': 'sync_orders',
            'customers': 'sync_customers',
            'fulfillment': 'auto_fulfill',
            'abandoned': 'sync_abandoned_checkouts',
        }
        
        if connector in field_map:
            setattr(store, field_map[connector], enabled)
            store.save(update_fields=[field_map[connector]])
            return JsonResponse({'success': True, 'message': f'Connector {connector} {"enabled" if enabled else "disabled"}'})
        else:
            return JsonResponse({'success': False, 'message': f'Unknown connector: {connector}'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
