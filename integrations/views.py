from django.urls import reverse_lazy
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
from django.utils import timezone
import json

from core import mixins
from .models import (
    GoogleWorkspaceConfig, ContactSyncLog, SyncedContact,
    ShopifyStore, ShopifyOrder, ShopifySyncLog,
    IntegrationConfig, WebhookEndpoint
)
from .tables import (
    GoogleConfigTable, ShopifyStoreTable, ShopifyOrderTable,
    IntegrationConfigTable, WebhookEndpointTable
)
from .forms import (
    GoogleWorkspaceConfigForm, ShopifyStoreForm,
    IntegrationConfigForm, WebhookEndpointForm
)
from .services import MockGoogleContactsService, MockShopifyService


# Integration Dashboard
class IntegrationDashboardView(mixins.HybridTemplateView):
    template_name = 'integrations/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Integrations'
        context['is_integrations'] = True
        context['is_dashboard'] = True
        
        # Google configs
        context['google_configs'] = GoogleWorkspaceConfig.objects.filter(is_active=True)
        
        # Shopify stores
        context['shopify_stores'] = ShopifyStore.objects.filter(is_active=True)
        
        # Other integrations
        context['integrations'] = IntegrationConfig.objects.filter(is_active=True)
        
        # Webhooks
        context['webhooks'] = WebhookEndpoint.objects.filter(is_active=True)
        
        return context


# Google Workspace
class GoogleConfigListView(mixins.HybridListView):
    model = GoogleWorkspaceConfig
    table_class = GoogleConfigTable
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Google Workspace Configs'
        context['can_add'] = True
        context['new_link'] = reverse_lazy('integrations:google_config_create')
        context['is_integrations'] = True
        context['is_google'] = True
        return context


class GoogleConfigDetailView(mixins.HybridDetailView):
    model = GoogleWorkspaceConfig
    template_name = 'integrations/google_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Google Config: {self.object.name}'
        context['sync_logs'] = self.object.sync_logs.all()[:20]
        context['synced_contacts'] = self.object.synced_contacts.filter(is_active=True)[:50]
        context['is_integrations'] = True
        context['is_google'] = True
        return context


class GoogleConfigCreateView(mixins.HybridCreateView):
    model = GoogleWorkspaceConfig
    form_class = GoogleWorkspaceConfigForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'New Google Workspace Config'
        context['is_integrations'] = True
        context['is_google'] = True
        return context


class GoogleConfigUpdateView(mixins.HybridUpdateView):
    model = GoogleWorkspaceConfig
    form_class = GoogleWorkspaceConfigForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Update Config: {self.object.name}'
        context['is_integrations'] = True
        context['is_google'] = True
        return context


# Shopify
class ShopifyStoreListView(mixins.HybridListView):
    model = ShopifyStore
    table_class = ShopifyStoreTable
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Shopify Stores'
        context['can_add'] = True
        context['new_link'] = reverse_lazy('integrations:shopify_store_create')
        context['is_integrations'] = True
        context['is_shopify'] = True
        return context


class ShopifyStoreDetailView(mixins.HybridDetailView):
    model = ShopifyStore
    template_name = 'integrations/shopify_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Shopify Store: {self.object.name}'
        context['orders'] = self.object.shopify_orders.filter(is_active=True)[:50]
        context['sync_logs'] = self.object.sync_logs.all()[:20]
        context['is_integrations'] = True
        context['is_shopify'] = True
        return context


class ShopifyStoreCreateView(mixins.HybridCreateView):
    model = ShopifyStore
    form_class = ShopifyStoreForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'New Shopify Store'
        context['is_integrations'] = True
        context['is_shopify'] = True
        return context


class ShopifyStoreUpdateView(mixins.HybridUpdateView):
    model = ShopifyStore
    form_class = ShopifyStoreForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Update Store: {self.object.name}'
        context['is_integrations'] = True
        context['is_shopify'] = True
        return context


class ShopifyOrderListView(mixins.HybridListView):
    model = ShopifyOrder
    table_class = ShopifyOrderTable
    filterset_fields = {'store': ['exact'], 'sync_status': ['exact'], 'financial_status': ['exact']}
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Shopify Orders'
        context['is_integrations'] = True
        context['is_shopify'] = True
        return context


# Generic Integrations
class IntegrationConfigListView(mixins.HybridListView):
    model = IntegrationConfig
    table_class = IntegrationConfigTable
    filterset_fields = {'integration_type': ['exact'], 'is_enabled': ['exact']}
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Integration Configs'
        context['can_add'] = True
        context['new_link'] = reverse_lazy('integrations:config_create')
        context['is_integrations'] = True
        context['is_config'] = True
        return context


class IntegrationConfigDetailView(mixins.HybridDetailView):
    model = IntegrationConfig
    template_name = 'integrations/config_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Integration: {self.object.name}'
        context['is_integrations'] = True
        context['is_config'] = True
        return context


class IntegrationConfigCreateView(mixins.HybridCreateView):
    model = IntegrationConfig
    form_class = IntegrationConfigForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'New Integration'
        context['is_integrations'] = True
        context['is_config'] = True
        return context


class IntegrationConfigUpdateView(mixins.HybridUpdateView):
    model = IntegrationConfig
    form_class = IntegrationConfigForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Update Integration: {self.object.name}'
        context['is_integrations'] = True
        context['is_config'] = True
        return context


# Webhooks
class WebhookEndpointListView(mixins.HybridListView):
    model = WebhookEndpoint
    table_class = WebhookEndpointTable
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Webhook Endpoints'
        context['can_add'] = True
        context['new_link'] = reverse_lazy('integrations:webhook_create')
        context['is_integrations'] = True
        context['is_webhook'] = True
        return context


class WebhookEndpointCreateView(mixins.HybridCreateView):
    model = WebhookEndpoint
    form_class = WebhookEndpointForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'New Webhook'
        context['is_integrations'] = True
        context['is_webhook'] = True
        return context


class WebhookEndpointUpdateView(mixins.HybridUpdateView):
    model = WebhookEndpoint
    form_class = WebhookEndpointForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Update Webhook: {self.object.name}'
        context['is_integrations'] = True
        context['is_webhook'] = True
        return context


# API Endpoints
@login_required
@require_POST
def sync_google_contacts(request, pk):
    """Trigger Google contacts sync."""
    try:
        config = GoogleWorkspaceConfig.objects.get(pk=pk)
        sync_log = MockGoogleContactsService.fetch_contacts(config)
        return JsonResponse({
            'success': True,
            'sync_id': str(sync_log.id),
            'contacts_created': sync_log.contacts_created,
            'contacts_updated': sync_log.contacts_updated,
            'message': f'Sync completed. Created: {sync_log.contacts_created}, Updated: {sync_log.contacts_updated}'
        })
    except GoogleWorkspaceConfig.DoesNotExist:
        return JsonResponse({'error': 'Config not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def sync_shopify_orders(request, pk):
    """Trigger Shopify orders sync."""
    try:
        store = ShopifyStore.objects.get(pk=pk)
        sync_log = MockShopifyService.sync_orders(store)
        return JsonResponse({
            'success': True,
            'sync_id': str(sync_log.id),
            'orders_created': sync_log.items_created,
            'orders_updated': sync_log.items_updated,
            'message': f'Sync completed. Created: {sync_log.items_created}, Updated: {sync_log.items_updated}'
        })
    except ShopifyStore.DoesNotExist:
        return JsonResponse({'error': 'Store not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def test_shopify_connection(request, pk):
    """Test Shopify store connection."""
    try:
        store = ShopifyStore.objects.get(pk=pk)
        result = MockShopifyService.test_connection(store)
        return JsonResponse(result)
    except ShopifyStore.DoesNotExist:
        return JsonResponse({'error': 'Store not found'}, status=404)


@login_required
@require_POST
def send_fulfillment(request, order_pk):
    """Send fulfillment to Shopify."""
    try:
        data = json.loads(request.body)
        order = ShopifyOrder.objects.get(pk=order_pk)
        
        tracking_number = data.get('tracking_number')
        tracking_url = data.get('tracking_url')
        
        if not tracking_number:
            return JsonResponse({'error': 'Tracking number required'}, status=400)
        
        result = MockShopifyService.send_fulfillment(order, tracking_number, tracking_url)
        return JsonResponse(result)
        
    except ShopifyOrder.DoesNotExist:
        return JsonResponse({'error': 'Order not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def test_integration(request, pk):
    """Test an integration connection."""
    try:
        config = IntegrationConfig.objects.get(pk=pk)
        
        # Mock test result
        config.last_test_at = timezone.now()
        config.last_test_status = 'success'
        config.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Connection to {config.provider} successful (MOCK)'
        })
    except IntegrationConfig.DoesNotExist:
        return JsonResponse({'error': 'Config not found'}, status=404)
