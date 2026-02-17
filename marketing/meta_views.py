"""
Meta Marketing Views

Marketing section pages:
1. Overview (Attribution Dashboard) - Date-filtered KPIs, charts
2. Meta Integration Settings - Config form + test actions
3. Campaign Performance - Table by campaign/day
4. CAPI Event Logs - Filterable log viewer
"""

import json
from datetime import timedelta, datetime, date
from decimal import Decimal

from django.views.generic import TemplateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Avg, Q, F
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone
from django.shortcuts import redirect

from .models import Lead
from .meta_models import (
    MetaIntegrationConfig, MetaDailyInsights,
    CapiEventLog, MarketingDailyRollup,
)


def _parse_date_filter(request):
    """Parse date filter from request params."""
    preset = request.GET.get('preset', 'this_month')
    today = timezone.now().date()

    if preset == 'today':
        start_date = today
        end_date = today
        label = 'Today'
    elif preset == 'yesterday':
        start_date = today - timedelta(days=1)
        end_date = today - timedelta(days=1)
        label = 'Yesterday'
    elif preset == 'this_week':
        start_date = today - timedelta(days=today.weekday())
        end_date = today
        label = 'This Week'
    elif preset == 'this_month':
        start_date = today.replace(day=1)
        end_date = today
        label = 'This Month'
    elif preset == 'last_month':
        first_of_month = today.replace(day=1)
        end_date = first_of_month - timedelta(days=1)
        start_date = end_date.replace(day=1)
        label = 'Last Month'
    elif preset == 'custom':
        try:
            start_date = datetime.strptime(request.GET.get('start_date', ''), '%Y-%m-%d').date()
            end_date = datetime.strptime(request.GET.get('end_date', ''), '%Y-%m-%d').date()
        except (ValueError, TypeError):
            start_date = today - timedelta(days=30)
            end_date = today
        label = f'{start_date} to {end_date}'
    else:
        start_date = today.replace(day=1)
        end_date = today
        label = 'This Month'

    return start_date, end_date, label, preset


# =============================================================================
# 1. MARKETING OVERVIEW (Attribution Dashboard)
# =============================================================================

class MarketingOverviewView(LoginRequiredMixin, TemplateView):
    """
    Marketing Attribution Dashboard with date filters, KPIs, and charts.
    Shows both Meta-side and ERP-estimated ROAS.
    """
    template_name = 'marketing/meta/overview.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Marketing Overview'
        context['page'] = 'overview'

        start_date, end_date, label, preset = _parse_date_filter(self.request)
        context['date_label'] = label
        context['date_preset'] = preset
        context['start_date'] = start_date.strftime('%Y-%m-%d')
        context['end_date'] = end_date.strftime('%Y-%m-%d')

        # Filter leads by date range
        leads = Lead.objects.filter(
            created__date__gte=start_date,
            created__date__lte=end_date,
            is_active=True,
        )

        wa_filter = Q(lead_source__icontains='whatsapp') | Q(source_type='whatsapp')
        shopify_filter = Q(lead_source__icontains='shopify') | Q(source_type='shopify')

        # KPIs
        context['total_leads'] = leads.count()
        context['wa_leads'] = leads.filter(wa_filter).count()
        context['shopify_leads'] = leads.filter(shopify_filter).count()

        ads_leads = leads.filter(
            attribution_model__in=['probabilistic_ads', 'manual_ads']
        ).count()
        organic_leads_count = leads.filter(
            attribution_model__in=['organic', 'manual_organic']
        ).count()
        context['estimated_ads_leads'] = ads_leads
        context['organic_leads'] = organic_leads_count

        context['won_count'] = leads.filter(conversion_status='won').count()
        context['lost_count'] = leads.filter(conversion_status='lost').count()
        context['pending_count'] = leads.filter(conversion_status='pending').count()

        revenue = leads.filter(
            conversion_status='won'
        ).aggregate(total=Sum('conversion_value'))['total'] or Decimal('0')
        context['revenue'] = revenue

        # Spend from Meta
        insights_agg = MetaDailyInsights.objects.filter(
            insight_date__gte=start_date,
            insight_date__lte=end_date,
        ).aggregate(
            total_spend=Sum('spend'),
            total_conversations=Sum('messaging_conversations_started'),
        )
        spend = insights_agg['total_spend'] or Decimal('0')
        context['spend'] = spend

        # ROAS calculations
        revenue_ads = leads.filter(
            conversion_status='won',
            attribution_model__in=['probabilistic_ads', 'manual_ads'],
        ).aggregate(total=Sum('conversion_value'))['total'] or Decimal('0')

        context['estimated_roas'] = round(revenue_ads / spend, 2) if spend > 0 else Decimal('0')
        context['cost_per_lead'] = round(spend / ads_leads, 2) if ads_leads > 0 else Decimal('0')

        ads_purchases = leads.filter(
            conversion_status='won',
            attribution_model__in=['probabilistic_ads', 'manual_ads'],
        ).count()
        context['cost_per_purchase'] = round(spend / ads_purchases, 2) if ads_purchases > 0 else Decimal('0')

        # Meta-side metrics
        meta_agg = MetaDailyInsights.objects.filter(
            insight_date__gte=start_date,
            insight_date__lte=end_date,
        ).aggregate(
            meta_leads=Sum('meta_leads'),
            meta_purchases=Sum('meta_purchases'),
            meta_purchase_value=Sum('meta_purchase_value'),
        )
        context['meta_reported_leads'] = meta_agg['meta_leads'] or 0
        context['meta_reported_purchases'] = meta_agg['meta_purchases'] or 0
        context['meta_reported_revenue'] = meta_agg['meta_purchase_value'] or Decimal('0')
        context['meta_roas'] = round(
            (meta_agg['meta_purchase_value'] or 0) / spend, 2
        ) if spend > 0 else Decimal('0')

        # Chart data: Daily trends
        daily_data = []
        num_days = (end_date - start_date).days + 1
        for i in range(num_days):
            d = start_date + timedelta(days=i)
            day_leads = leads.filter(created__date=d)
            day_insights = MetaDailyInsights.objects.filter(insight_date=d).aggregate(
                spend=Sum('spend')
            )
            daily_data.append({
                'date': d.strftime('%Y-%m-%d'),
                'label': d.strftime('%d %b'),
                'leads': day_leads.count(),
                'won': day_leads.filter(conversion_status='won').count(),
                'lost': day_leads.filter(conversion_status='lost').count(),
                'pending': day_leads.filter(conversion_status='pending').count(),
                'ads': day_leads.filter(attribution_model__in=['probabilistic_ads', 'manual_ads']).count(),
                'organic': day_leads.filter(attribution_model__in=['organic', 'manual_organic']).count(),
                'revenue': float(day_leads.filter(conversion_status='won').aggregate(
                    t=Sum('conversion_value'))['t'] or 0),
                'spend': float(day_insights['spend'] or 0),
            })
        context['chart_data'] = json.dumps(daily_data)

        # Config status
        config = MetaIntegrationConfig.get_config()
        context['meta_config'] = config
        context['is_meta_configured'] = bool(config and config.is_active)

        return context


# =============================================================================
# 2. META INTEGRATION SETTINGS
# =============================================================================

class MetaSettingsView(LoginRequiredMixin, TemplateView):
    """Meta Integration configuration page."""
    template_name = 'marketing/meta/settings.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Meta Integration Settings'
        context['page'] = 'settings'
        context['config'] = MetaIntegrationConfig.get_config()

        # CAPI event stats
        context['capi_total'] = CapiEventLog.objects.count()
        context['capi_sent'] = CapiEventLog.objects.filter(status='sent').count()
        context['capi_failed'] = CapiEventLog.objects.filter(status='failed').count()
        context['capi_pending'] = CapiEventLog.objects.filter(status='pending').count()

        return context

    def post(self, request, *args, **kwargs):
        """Handle config save."""
        config = MetaIntegrationConfig.get_config()
        if not config:
            config = MetaIntegrationConfig()

        config.business_id = request.POST.get('business_id', '').strip()
        config.ad_account_id = request.POST.get('ad_account_id', '').strip()
        config.pixel_id = request.POST.get('pixel_id', '').strip() or None
        config.dataset_id = request.POST.get('dataset_id', '').strip() or None
        config.access_token = request.POST.get('access_token', '').strip()
        config.app_secret = request.POST.get('app_secret', '').strip() or None
        config.is_active = request.POST.get('is_active') == 'on'
        config.send_lead_events = request.POST.get('send_lead_events') == 'on'
        config.send_purchase_events = request.POST.get('send_purchase_events') == 'on'

        threshold = request.POST.get('attribution_threshold', '0.20')
        try:
            config.attribution_threshold = Decimal(threshold)
        except Exception:
            config.attribution_threshold = Decimal('0.20')

        config.save()

        return redirect('marketing:meta_settings')


# =============================================================================
# 3. CAMPAIGN PERFORMANCE
# =============================================================================

class CampaignPerformanceView(LoginRequiredMixin, TemplateView):
    """Campaign performance table from MetaDailyInsights."""
    template_name = 'marketing/meta/campaigns.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Campaign Performance'
        context['page'] = 'campaigns'

        start_date, end_date, label, preset = _parse_date_filter(self.request)
        context['date_label'] = label
        context['date_preset'] = preset
        context['start_date'] = start_date.strftime('%Y-%m-%d')
        context['end_date'] = end_date.strftime('%Y-%m-%d')

        # Get campaign insights
        insights = MetaDailyInsights.objects.filter(
            insight_date__gte=start_date,
            insight_date__lte=end_date,
        ).order_by('-insight_date', 'campaign_name')

        context['insights'] = insights

        # Summary by campaign
        campaign_summary = MetaDailyInsights.objects.filter(
            insight_date__gte=start_date,
            insight_date__lte=end_date,
        ).values(
            'campaign_id', 'campaign_name'
        ).annotate(
            total_spend=Sum('spend'),
            total_impressions=Sum('impressions'),
            total_clicks=Sum('clicks'),
            total_conversations=Sum('messaging_conversations_started'),
            total_meta_leads=Sum('meta_leads'),
            total_meta_purchases=Sum('meta_purchases'),
            total_meta_revenue=Sum('meta_purchase_value'),
            total_erp_leads=Sum('erp_attributed_leads'),
            total_erp_revenue=Sum('erp_attributed_revenue'),
        ).order_by('-total_spend')

        for cs in campaign_summary:
            cs['estimated_roas'] = (
                round(float(cs['total_erp_revenue'] or 0) / float(cs['total_spend']), 2)
                if cs['total_spend'] and float(cs['total_spend']) > 0 else 0
            )

        context['campaign_summary'] = campaign_summary

        # Totals
        totals = MetaDailyInsights.objects.filter(
            insight_date__gte=start_date,
            insight_date__lte=end_date,
        ).aggregate(
            total_spend=Sum('spend'),
            total_impressions=Sum('impressions'),
            total_clicks=Sum('clicks'),
            total_conversations=Sum('messaging_conversations_started'),
        )
        context['totals'] = totals

        return context


# =============================================================================
# 4. CAPI EVENT LOGS
# =============================================================================

class CapiEventLogsView(LoginRequiredMixin, ListView):
    """Filterable CAPI event log viewer."""
    model = CapiEventLog
    template_name = 'marketing/meta/capi_logs.html'
    context_object_name = 'events'
    paginate_by = 50

    def get_queryset(self):
        qs = CapiEventLog.objects.select_related('lead').order_by('-created')

        # Filters
        event_name = self.request.GET.get('event_name')
        status = self.request.GET.get('status')
        source = self.request.GET.get('source')

        if event_name:
            qs = qs.filter(event_name=event_name)
        if status:
            qs = qs.filter(status=status)
        if source:
            qs = qs.filter(source=source)

        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        if start_date:
            try:
                qs = qs.filter(created__date__gte=datetime.strptime(start_date, '%Y-%m-%d').date())
            except ValueError:
                pass
        if end_date:
            try:
                qs = qs.filter(created__date__lte=datetime.strptime(end_date, '%Y-%m-%d').date())
            except ValueError:
                pass

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'CAPI Event Logs'
        context['page'] = 'capi_logs'

        # Stats
        context['total_events'] = CapiEventLog.objects.count()
        context['sent_events'] = CapiEventLog.objects.filter(status='sent').count()
        context['failed_events'] = CapiEventLog.objects.filter(status='failed').count()
        context['pending_events'] = CapiEventLog.objects.filter(status='pending').count()

        # Current filters
        context['current_event_name'] = self.request.GET.get('event_name', '')
        context['current_status'] = self.request.GET.get('status', '')
        context['current_source'] = self.request.GET.get('source', '')

        return context


# =============================================================================
# API ENDPOINTS (Manual Triggers)
# =============================================================================

@login_required
@require_POST
def api_test_meta_connection(request):
    """Test Meta API connection."""
    config = MetaIntegrationConfig.get_config()
    if not config:
        return JsonResponse({'success': False, 'error': 'No Meta config found'})

    import requests as req
    try:
        # Test with a simple API call
        ad_account = config.ad_account_id
        if not ad_account.startswith('act_'):
            ad_account = f'act_{ad_account}'

        url = f'https://graph.facebook.com/v21.0/{ad_account}'
        resp = req.get(url, params={
            'access_token': config.access_token,
            'fields': 'name,account_status',
        }, timeout=15)
        data = resp.json()

        if 'error' in data:
            return JsonResponse({
                'success': False,
                'error': data['error'].get('message', 'Unknown error')
            })

        return JsonResponse({
            'success': True,
            'account_name': data.get('name', 'Unknown'),
            'account_status': data.get('account_status', 'Unknown'),
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
def api_send_test_event(request):
    """Send a test CAPI event."""
    from .meta_services import MetaCAPIService

    event_type = request.POST.get('event_type', 'lead')
    service = MetaCAPIService()

    if event_type == 'purchase':
        success, response = service.send_test_purchase_event()
    else:
        success, response = service.send_test_lead_event()

    return JsonResponse({
        'success': success,
        'event_type': event_type,
        'response': response,
    })


@login_required
@require_POST
def api_sync_insights(request):
    """Manually trigger Meta insights sync."""
    from .meta_services import MetaInsightsService

    service = MetaInsightsService()
    if not service.is_configured():
        return JsonResponse({'success': False, 'error': 'Meta Insights not configured'})

    # Try Celery first, fallback to sync
    try:
        from .meta_tasks import sync_meta_daily_insights
        sync_meta_daily_insights.delay()
        return JsonResponse({'success': True, 'message': 'Sync task queued'})
    except Exception:
        # Celery not available, run sync
        result = service.sync_daily_insights()
        return JsonResponse({'success': 'error' not in result, 'result': result})


@login_required
@require_POST
def api_run_attribution(request):
    """Manually trigger attribution engine."""
    from .meta_services import ProbabilisticAttributionEngine, MarketingRollupService

    results = {}
    yesterday = (timezone.now() - timedelta(days=1)).date()

    try:
        for days_ago in range(8):
            target = yesterday - timedelta(days=days_ago)
            results[str(target)] = ProbabilisticAttributionEngine.run_attribution(target)
            MarketingRollupService.compute_rollup(target)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': True, 'results': results})


@login_required
@require_POST
def api_send_pending_capi(request):
    """Manually send all pending CAPI events."""
    from .meta_services import MetaCAPIService

    service = MetaCAPIService()
    if not service.is_configured():
        return JsonResponse({'success': False, 'error': 'Meta CAPI not configured'})

    # Send pending lead events
    leads_to_send = Lead.objects.filter(
        lead_event_sent_to_meta=False,
        is_active=True,
    ).exclude(phone_no__isnull=True).exclude(phone_no='')[:100]

    sent_leads = 0
    for lead in leads_to_send:
        success, _ = service.send_lead_event(lead)
        if success:
            sent_leads += 1

    # Send pending purchase events
    leads_won = Lead.objects.filter(
        conversion_status='won',
        conversion_sent_to_meta=False,
        converted_order__isnull=False,
        is_active=True,
    )[:100]

    sent_purchases = 0
    for lead in leads_won:
        success, _ = service.send_purchase_event(lead)
        if success:
            sent_purchases += 1

    return JsonResponse({
        'success': True,
        'sent_leads': sent_leads,
        'sent_purchases': sent_purchases,
    })


@login_required
@require_POST
def api_update_lead_attribution(request, pk):
    """Manually override lead attribution."""
    try:
        lead = Lead.objects.get(pk=pk)
    except Lead.DoesNotExist:
        return JsonResponse({'error': 'Lead not found'}, status=404)

    model = request.POST.get('attribution_model')
    if model not in ['manual_ads', 'manual_organic']:
        return JsonResponse({'error': 'Invalid model. Use manual_ads or manual_organic'}, status=400)

    lead.attribution_model = model
    lead.attribution_confidence = Decimal('100.00')
    lead.attribution_reason = f"Manual override by {request.user.username} at {timezone.now()}"
    lead.attribution_updated_at = timezone.now()
    lead.save(update_fields=[
        'attribution_model', 'attribution_confidence',
        'attribution_reason', 'attribution_updated_at',
    ])

    return JsonResponse({
        'success': True,
        'attribution_model': model,
        'message': f'Lead attribution updated to {model}',
    })


@login_required
@require_GET
def api_overview_chart_data(request):
    """Get chart data for the overview dashboard (AJAX)."""
    start_date, end_date, _, _ = _parse_date_filter(request)

    leads = Lead.objects.filter(
        created__date__gte=start_date,
        created__date__lte=end_date,
        is_active=True,
    )

    daily_data = []
    num_days = (end_date - start_date).days + 1
    for i in range(min(num_days, 90)):  # Cap at 90 days
        d = start_date + timedelta(days=i)
        day_leads = leads.filter(created__date=d)
        day_insights = MetaDailyInsights.objects.filter(insight_date=d).aggregate(
            spend=Sum('spend')
        )
        daily_data.append({
            'date': d.strftime('%Y-%m-%d'),
            'label': d.strftime('%d %b'),
            'leads': day_leads.count(),
            'won': day_leads.filter(conversion_status='won').count(),
            'lost': day_leads.filter(conversion_status='lost').count(),
            'ads': day_leads.filter(attribution_model__in=['probabilistic_ads', 'manual_ads']).count(),
            'organic': day_leads.filter(attribution_model__in=['organic', 'manual_organic']).count(),
            'revenue': float(day_leads.filter(conversion_status='won').aggregate(
                t=Sum('conversion_value'))['t'] or 0),
            'spend': float(day_insights['spend'] or 0),
        })

    return JsonResponse({'data': daily_data})
