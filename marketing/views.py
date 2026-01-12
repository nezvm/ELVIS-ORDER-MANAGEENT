from django.urls import reverse_lazy
from django.http import JsonResponse
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Sum, Avg, Q, F
from django.utils import timezone
import json

from .models import (
    Lead, LeadActivity, WhatsAppProvider, WhatsAppTemplate,
    NotificationEvent, Campaign, CampaignRecipient, MessageLog,
    DoNotMessage, GeoMarketStats
)
from .forms import (
    LeadForm, WhatsAppProviderForm, WhatsAppTemplateForm,
    CampaignForm, NotificationEventForm
)
from .services import LeadService, WhatsAppService, CampaignService, MarketInsightsService


# Leads
class LeadListView(LoginRequiredMixin, TemplateView):
    template_name = 'marketing/leads/list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Leads'
        
        # Get filters
        match_status = self.request.GET.get('match_status')
        lead_status = self.request.GET.get('lead_status')
        state = self.request.GET.get('state')
        search = self.request.GET.get('search')
        
        leads = Lead.objects.filter(is_active=True).select_related('assigned_to', 'matched_customer')
        
        if match_status:
            leads = leads.filter(match_status=match_status)
        if lead_status:
            leads = leads.filter(lead_status=lead_status)
        if state:
            leads = leads.filter(state=state)
        if search:
            leads = leads.filter(
                Q(name__icontains=search) | Q(phone_no__icontains=search)
            )
        
        context['leads'] = leads[:100]
        context['total_count'] = leads.count()
        context['win_count'] = leads.filter(match_status='win').count()
        context['loss_count'] = leads.filter(match_status='loss').count()
        context['states'] = Lead.objects.filter(is_active=True, state__isnull=False).values_list('state', flat=True).distinct()
        
        return context


class LeadDetailView(LoginRequiredMixin, DetailView):
    model = Lead
    template_name = 'marketing/leads/detail.html'
    context_object_name = 'lead'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Lead: {self.object.name or self.object.phone_no}'
        context['activities'] = self.object.activities.all()[:20]
        context['campaigns'] = CampaignRecipient.objects.filter(lead=self.object).select_related('campaign')[:10]
        return context


class LeadCreateView(LoginRequiredMixin, CreateView):
    model = Lead
    form_class = LeadForm
    template_name = 'marketing/leads/form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'New Lead'
        return context
    
    def get_success_url(self):
        return reverse_lazy('marketing:lead_detail', kwargs={'pk': self.object.pk})


class LeadUpdateView(LoginRequiredMixin, UpdateView):
    model = Lead
    form_class = LeadForm
    template_name = 'marketing/leads/form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Edit Lead: {self.object.name or self.object.phone_no}'
        return context
    
    def get_success_url(self):
        return reverse_lazy('marketing:lead_detail', kwargs={'pk': self.object.pk})


# WhatsApp
class WhatsAppDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'marketing/whatsapp/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'WhatsApp Marketing'
        
        context['providers'] = WhatsAppProvider.objects.filter(is_active=True)
        context['templates'] = WhatsAppTemplate.objects.filter(is_active=True)[:10]
        context['events'] = NotificationEvent.objects.filter(is_active=True)
        context['recent_logs'] = MessageLog.objects.filter(is_active=True)[:20]
        
        # Stats
        today = timezone.now().date()
        context['messages_today'] = MessageLog.objects.filter(created__date=today).count()
        context['delivered_today'] = MessageLog.objects.filter(created__date=today, status='delivered').count()
        
        return context


class ProviderListView(LoginRequiredMixin, ListView):
    model = WhatsAppProvider
    template_name = 'marketing/whatsapp/providers.html'
    context_object_name = 'providers'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'WhatsApp Providers'
        return context


class ProviderDetailView(LoginRequiredMixin, DetailView):
    model = WhatsAppProvider
    template_name = 'marketing/whatsapp/provider_detail.html'
    context_object_name = 'provider'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Provider: {self.object.name}'
        context['templates'] = self.object.templates.filter(is_active=True)
        context['recent_logs'] = MessageLog.objects.filter(provider=self.object)[:20]
        return context


class ProviderCreateView(LoginRequiredMixin, CreateView):
    model = WhatsAppProvider
    form_class = WhatsAppProviderForm
    template_name = 'marketing/whatsapp/provider_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'New WhatsApp Provider'
        return context
    
    def get_success_url(self):
        return reverse_lazy('marketing:provider_detail', kwargs={'pk': self.object.pk})


class ProviderUpdateView(LoginRequiredMixin, UpdateView):
    model = WhatsAppProvider
    form_class = WhatsAppProviderForm
    template_name = 'marketing/whatsapp/provider_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Edit Provider: {self.object.name}'
        return context
    
    def get_success_url(self):
        return reverse_lazy('marketing:provider_detail', kwargs={'pk': self.object.pk})


class TemplateListView(LoginRequiredMixin, ListView):
    model = WhatsAppTemplate
    template_name = 'marketing/whatsapp/templates.html'
    context_object_name = 'templates'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Message Templates'
        return context


class TemplateCreateView(LoginRequiredMixin, CreateView):
    model = WhatsAppTemplate
    form_class = WhatsAppTemplateForm
    template_name = 'marketing/whatsapp/template_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'New Template'
        return context
    
    def get_success_url(self):
        return reverse_lazy('marketing:template_list')


class NotificationEventsView(LoginRequiredMixin, TemplateView):
    template_name = 'marketing/whatsapp/notifications.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Notification Events'
        context['events'] = NotificationEvent.objects.all()
        context['providers'] = WhatsAppProvider.objects.filter(is_active=True, status='connected')
        context['templates'] = WhatsAppTemplate.objects.filter(is_active=True, status='approved')
        return context


class MessageLogListView(LoginRequiredMixin, ListView):
    model = MessageLog
    template_name = 'marketing/whatsapp/logs.html'
    context_object_name = 'logs'
    paginate_by = 50
    
    def get_queryset(self):
        qs = super().get_queryset().filter(is_active=True)
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        return qs.select_related('provider', 'template')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Message Logs'
        return context


# Campaigns
class CampaignListView(LoginRequiredMixin, ListView):
    model = Campaign
    template_name = 'marketing/campaigns/list.html'
    context_object_name = 'campaigns'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Campaigns'
        return context


class CampaignDetailView(LoginRequiredMixin, DetailView):
    model = Campaign
    template_name = 'marketing/campaigns/detail.html'
    context_object_name = 'campaign'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Campaign: {self.object.name}'
        context['recipients'] = self.object.recipients.all()[:50]
        return context


class CampaignCreateView(LoginRequiredMixin, CreateView):
    model = Campaign
    form_class = CampaignForm
    template_name = 'marketing/campaigns/form.html'
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'New Campaign'
        return context
    
    def get_success_url(self):
        return reverse_lazy('marketing:campaign_detail', kwargs={'pk': self.object.pk})


class CampaignUpdateView(LoginRequiredMixin, UpdateView):
    model = Campaign
    form_class = CampaignForm
    template_name = 'marketing/campaigns/form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Edit Campaign: {self.object.name}'
        return context
    
    def get_success_url(self):
        return reverse_lazy('marketing:campaign_detail', kwargs={'pk': self.object.pk})


# Market Insights
class MarketInsightsView(LoginRequiredMixin, TemplateView):
    template_name = 'marketing/insights/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Market Insights'
        
        # Active tab
        tab = self.request.GET.get('tab', 'orders')
        context['active_tab'] = tab
        
        # TAB 1: Order Markets (from shipping address)
        context['order_stats'] = OrderMarketStats.objects.filter(
            period_type='all_time',
            district__isnull=True,
            pincode__isnull=True
        ).order_by('-revenue')[:20]
        
        # TAB 2: Lead Markets (enriched only)
        context['lead_stats'] = LeadMarketStats.objects.filter(
            period_type='all_time',
            district__isnull=True,
            pincode__isnull=True
        ).order_by('-leads_count')[:20]
        
        # Unknown Location Stats
        context['unknown_stats'] = LeadService.get_unknown_location_stats()
        
        # Hotspots, Cold Zones, New Markets
        context['hotspots'] = MarketInsightsService.get_hotspot_markets(5)
        context['cold_zones'] = MarketInsightsService.get_cold_markets(5)
        context['new_markets'] = MarketInsightsService.get_new_markets(30, 5)
        
        # Abandoned Metrics
        context['abandoned_metrics'] = AbandonedMetrics.objects.filter(
            period_type='all_time',
            state__isnull=True
        ).first()
        
        # Loss Markets (enriched abandoned)
        context['loss_markets'] = MarketInsightsService.get_loss_markets_by_state(5)
        
        # Summary totals
        order_totals = OrderMarketStats.objects.filter(period_type='all_time').aggregate(
            total_orders=Sum('orders_count'),
            total_revenue=Sum('revenue')
        )
        lead_totals = LeadMarketStats.objects.filter(period_type='all_time').aggregate(
            total_leads=Sum('leads_count')
        )
        
        context['totals'] = {
            'total_leads': lead_totals.get('total_leads') or 0,
            'total_orders': order_totals.get('total_orders') or 0,
            'total_revenue': order_totals.get('total_revenue') or 0,
        }
        
        # Legacy for backward compatibility
        context['stats'] = context['order_stats']
        
        return context


class HotspotsView(LoginRequiredMixin, TemplateView):
    template_name = 'marketing/insights/hotspots.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Hot Markets'
        context['markets'] = MarketInsightsService.get_hotspot_markets(50)
        return context


class ColdZonesView(LoginRequiredMixin, TemplateView):
    template_name = 'marketing/insights/cold_zones.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Cold Zones'
        context['markets'] = MarketInsightsService.get_cold_markets(50)
        return context


class AbandonedInsightsView(LoginRequiredMixin, TemplateView):
    """Abandoned checkout insights with top products and loss markets."""
    template_name = 'marketing/insights/abandoned.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Abandoned Insights'
        
        # Abandoned metrics
        metrics = AbandonedMetrics.objects.filter(
            period_type='all_time',
            state__isnull=True
        ).first()
        context['metrics'] = metrics
        
        # Loss markets by state (enriched only)
        context['loss_markets'] = MarketInsightsService.get_loss_markets_by_state(20)
        
        # Top abandoned leads
        context['abandoned_leads'] = Lead.objects.filter(
            lead_source__in=['shopify_abandoned_checkout', 'shopify_abandoned_cart'],
            is_active=True
        ).order_by('-cart_value')[:20]
        
        return context


# API Endpoints
@login_required
@require_POST
def sync_google_leads(request):
    """Sync Google contacts to Leads (mock)."""
    from integrations.services import MockGoogleContactsService
    from integrations.models import GoogleWorkspaceConfig
    
    config_id = request.POST.get('config_id')
    try:
        config = GoogleWorkspaceConfig.objects.get(pk=config_id)
        
        # Generate mock contacts and sync to Leads
        mock_contacts = MockGoogleContactsService._generate_mock_contacts(15)
        
        created = 0
        updated = 0
        
        for contact_data in mock_contacts:
            lead, status = LeadService.sync_google_contact(contact_data, config)
            if status == 'created':
                created += 1
            elif status == 'updated':
                updated += 1
        
        return JsonResponse({
            'success': True,
            'created': created,
            'updated': updated,
            'message': f'Synced {created + updated} leads'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def match_lead(request, pk):
    """Re-match a lead against customers/orders."""
    try:
        lead = Lead.objects.get(pk=pk)
        LeadService.match_lead(lead)
        return JsonResponse({
            'success': True,
            'match_status': lead.match_status,
            'message': f'Lead is now {lead.match_status.upper()}'
        })
    except Lead.DoesNotExist:
        return JsonResponse({'error': 'Lead not found'}, status=404)


@login_required
@require_POST
def convert_lead(request, pk):
    """Convert a lead to customer."""
    try:
        lead = Lead.objects.get(pk=pk)
        LeadService.convert_lead_to_customer(lead, request.user)
        return JsonResponse({
            'success': True,
            'message': 'Lead converted successfully'
        })
    except Lead.DoesNotExist:
        return JsonResponse({'error': 'Lead not found'}, status=404)


@login_required
@require_POST
def test_provider(request, pk):
    """Test WhatsApp provider connection."""
    try:
        provider = WhatsAppProvider.objects.get(pk=pk)
        result = WhatsAppService.test_provider_connection(provider)
        return JsonResponse(result)
    except WhatsAppProvider.DoesNotExist:
        return JsonResponse({'error': 'Provider not found'}, status=404)


@login_required
@require_POST
def start_campaign(request, pk):
    """Start a campaign."""
    try:
        campaign = Campaign.objects.get(pk=pk)
        
        if campaign.status not in ['draft', 'scheduled', 'paused']:
            return JsonResponse({'error': 'Campaign cannot be started'}, status=400)
        
        # Create recipients if not exists
        if campaign.total_recipients == 0:
            CampaignService.create_campaign_recipients(campaign)
        
        campaign.status = 'running'
        campaign.started_at = timezone.now()
        campaign.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Campaign started with {campaign.total_recipients} recipients'
        })
    except Campaign.DoesNotExist:
        return JsonResponse({'error': 'Campaign not found'}, status=404)


@login_required
@require_POST
def pause_campaign(request, pk):
    """Pause a campaign."""
    try:
        campaign = Campaign.objects.get(pk=pk)
        campaign.status = 'paused'
        campaign.save()
        return JsonResponse({'success': True, 'message': 'Campaign paused'})
    except Campaign.DoesNotExist:
        return JsonResponse({'error': 'Campaign not found'}, status=404)


@login_required
@require_POST
def refresh_insights(request):
    """Refresh market insights."""
    try:
        stats = MarketInsightsService.compute_geo_stats()
        return JsonResponse({
            'success': True,
            'message': f'Computed stats for {stats.count()} regions'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_GET
def lead_stats_api(request):
    """Get lead statistics for dashboard."""
    leads = Lead.objects.filter(is_active=True)
    
    return JsonResponse({
        'total': leads.count(),
        'win': leads.filter(match_status='win').count(),
        'loss': leads.filter(match_status='loss').count(),
        'by_lifecycle': dict(leads.values('lifecycle_stage').annotate(count=Count('id')).values_list('lifecycle_stage', 'count')),
        'by_value': dict(leads.values('value_tier').annotate(count=Count('id')).values_list('value_tier', 'count')),
    })
