"""
Leads Module Views

Comprehensive leads management with:
- Overview Dashboard
- WhatsApp Leads
- Shopify Leads
- Other Leads
- Lead Detail with lifecycle
"""

import json
from datetime import timedelta, datetime
from decimal import Decimal

from django.views.generic import TemplateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Sum, Avg, Q, F
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .models import Lead, DailyLeadMetrics, LeadMatchingConfig, LeadActivity


def get_date_filter_params(request):
    """
    Extract date filter parameters from request.
    Returns (start_date, end_date, filter_label)
    """
    filter_type = request.GET.get('date_filter', 'this_month')
    today = timezone.now().date()
    
    if filter_type == 'today':
        return today, today, 'Today'
    elif filter_type == 'yesterday':
        yesterday = today - timedelta(days=1)
        return yesterday, yesterday, 'Yesterday'
    elif filter_type == 'this_week':
        start = today - timedelta(days=today.weekday())
        return start, today, 'This Week'
    elif filter_type == 'this_month':
        start = today.replace(day=1)
        return start, today, 'This Month'
    elif filter_type == 'last_7_days':
        return today - timedelta(days=7), today, 'Last 7 Days'
    elif filter_type == 'last_30_days':
        return today - timedelta(days=30), today, 'Last 30 Days'
    elif filter_type == 'custom':
        start = request.GET.get('start_date')
        end = request.GET.get('end_date')
        if start and end:
            try:
                start = datetime.strptime(start, '%Y-%m-%d').date()
                end = datetime.strptime(end, '%Y-%m-%d').date()
                return start, end, f'{start} to {end}'
            except ValueError:
                pass
        return today - timedelta(days=30), today, 'Last 30 Days'
    else:
        # Default to this month
        start = today.replace(day=1)
        return start, today, 'This Month'


class LeadsOverviewDashboardView(LoginRequiredMixin, TemplateView):
    """
    Main Leads Dashboard with KPIs, charts, and unified table.
    """
    template_name = 'marketing/leads/overview.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Leads Overview'
        context['is_leads'] = True
        context['active_tab'] = 'overview'
        
        # Date filter
        start_date, end_date, filter_label = get_date_filter_params(self.request)
        context['date_filter'] = self.request.GET.get('date_filter', 'this_month')
        context['filter_label'] = filter_label
        context['start_date'] = start_date
        context['end_date'] = end_date
        
        # Base queryset with date filter
        all_leads = Lead.objects.filter(is_active=True)
        filtered_leads = all_leads.filter(created__date__gte=start_date, created__date__lte=end_date)
        
        # === KPI Cards ===
        context['total_leads'] = filtered_leads.count()
        context['pending_leads'] = filtered_leads.filter(conversion_status='pending').count()
        context['won_leads'] = filtered_leads.filter(conversion_status='won').count()
        context['lost_leads'] = filtered_leads.filter(conversion_status='lost').count()
        
        # Conversion Rate
        decided = context['won_leads'] + context['lost_leads']
        context['conversion_rate'] = round((context['won_leads'] / decided * 100) if decided > 0 else 0, 1)
        
        # Revenue
        context['total_revenue'] = filtered_leads.filter(
            conversion_status='won'
        ).aggregate(total=Sum('conversion_value'))['total'] or Decimal('0')
        
        # Avg Time to Win
        context['avg_conversion_days'] = filtered_leads.filter(
            conversion_status='won',
            conversion_days__isnull=False
        ).aggregate(avg=Avg('conversion_days'))['avg'] or 0
        
        # === Source Breakdown ===
        wa_filter = Q(lead_source__icontains='whatsapp') | Q(source_type='whatsapp')
        shopify_filter = Q(lead_source__icontains='shopify') | Q(source_type='shopify')
        
        context['whatsapp_leads'] = filtered_leads.filter(wa_filter).count()
        context['shopify_leads'] = filtered_leads.filter(shopify_filter).count()
        context['other_leads'] = filtered_leads.exclude(wa_filter).exclude(shopify_filter).count()
        
        # === Leads Trend (daily) ===
        leads_by_day = filtered_leads.annotate(
            date=TruncDate('created')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        context['leads_trend'] = list(leads_by_day)
        context['leads_trend_json'] = json.dumps([
            {'date': item['date'].strftime('%Y-%m-%d'), 'count': item['count']}
            for item in leads_by_day
        ])
        
        # === Status Breakdown for Chart ===
        context['status_breakdown'] = {
            'pending': context['pending_leads'],
            'won': context['won_leads'],
            'lost': context['lost_leads'],
        }
        context['status_breakdown_json'] = json.dumps(context['status_breakdown'])
        
        # === Source Breakdown for Chart ===
        context['source_breakdown'] = {
            'WhatsApp': context['whatsapp_leads'],
            'Shopify': context['shopify_leads'],
            'Other': context['other_leads'],
        }
        context['source_breakdown_json'] = json.dumps(context['source_breakdown'])
        
        # === Recent Leads Table ===
        context['recent_leads'] = filtered_leads.select_related(
            'owner', 'converted_order'
        ).order_by('-created')[:50]
        
        # Status filter
        status_filter = self.request.GET.get('status')
        source_filter = self.request.GET.get('source')
        
        if status_filter:
            context['recent_leads'] = context['recent_leads'].filter(conversion_status=status_filter)
        if source_filter == 'whatsapp':
            context['recent_leads'] = context['recent_leads'].filter(wa_filter)
        elif source_filter == 'shopify':
            context['recent_leads'] = context['recent_leads'].filter(shopify_filter)
        elif source_filter == 'other':
            context['recent_leads'] = context['recent_leads'].exclude(wa_filter).exclude(shopify_filter)
        
        context['status_filter'] = status_filter
        context['source_filter'] = source_filter
        
        # Config
        context['config'] = LeadMatchingConfig.get_config()
        
        return context


class WhatsAppLeadsView(LoginRequiredMixin, TemplateView):
    """
    WhatsApp Leads subpage with per-number breakdown.
    """
    template_name = 'marketing/leads/whatsapp.html'
    
    def get_context_data(self, **kwargs):
        from integrations.wabis.models import WabisNumber, WabisCustomer
        
        context = super().get_context_data(**kwargs)
        context['title'] = 'WhatsApp Leads'
        context['is_leads'] = True
        context['active_tab'] = 'whatsapp'
        
        # Date filter
        start_date, end_date, filter_label = get_date_filter_params(self.request)
        context['date_filter'] = self.request.GET.get('date_filter', 'this_month')
        context['filter_label'] = filter_label
        context['start_date'] = start_date
        context['end_date'] = end_date
        
        # WhatsApp leads
        wa_filter = Q(lead_source__icontains='whatsapp') | Q(source_type='whatsapp')
        all_wa_leads = Lead.objects.filter(wa_filter, is_active=True)
        filtered_wa_leads = all_wa_leads.filter(
            created__date__gte=start_date,
            created__date__lte=end_date
        )
        
        # KPIs
        context['total_leads'] = filtered_wa_leads.count()
        context['pending_leads'] = filtered_wa_leads.filter(conversion_status='pending').count()
        context['won_leads'] = filtered_wa_leads.filter(conversion_status='won').count()
        context['lost_leads'] = filtered_wa_leads.filter(conversion_status='lost').count()
        
        decided = context['won_leads'] + context['lost_leads']
        context['conversion_rate'] = round((context['won_leads'] / decided * 100) if decided > 0 else 0, 1)
        
        context['total_revenue'] = filtered_wa_leads.filter(
            conversion_status='won'
        ).aggregate(total=Sum('conversion_value'))['total'] or Decimal('0')
        
        # Per-Number Breakdown
        numbers = WabisNumber.objects.filter(is_active=True)
        numbers_stats = []
        
        for number in numbers:
            # Get customers linked to this number
            customers = WabisCustomer.objects.filter(is_active=True)
            
            # For now, we'll count all WhatsApp leads
            # In production, link leads to specific numbers via phone matching
            number_leads = filtered_wa_leads
            
            stats = {
                'number': number,
                'leads_count': number_leads.count() // max(numbers.count(), 1),  # Distribute evenly for now
                'pending': number_leads.filter(conversion_status='pending').count() // max(numbers.count(), 1),
                'won': number_leads.filter(conversion_status='won').count() // max(numbers.count(), 1),
                'lost': number_leads.filter(conversion_status='lost').count() // max(numbers.count(), 1),
                'conversion_rate': context['conversion_rate'],
                'revenue': float(context['total_revenue']) / max(numbers.count(), 1),
                'last_message': number.last_message_at,
            }
            numbers_stats.append(stats)
        
        context['numbers_stats'] = numbers_stats
        
        # Recent WhatsApp Leads
        context['recent_leads'] = filtered_wa_leads.select_related('assigned_to').order_by('-created')[:50]
        
        # Phone number filter
        phone_filter = self.request.GET.get('phone_number')
        if phone_filter:
            context['recent_leads'] = context['recent_leads'].filter(phone_no__icontains=phone_filter)
        
        return context


class ShopifyLeadsView(LoginRequiredMixin, TemplateView):
    """
    Shopify Leads subpage with Orders/Abandoned/Recovered tabs.
    """
    template_name = 'marketing/leads/shopify.html'
    
    def get_context_data(self, **kwargs):
        from integrations.models import ShopifyOrder, ShopifyAbandonedCheckout
        
        context = super().get_context_data(**kwargs)
        context['title'] = 'Shopify Leads'
        context['is_leads'] = True
        context['active_tab'] = 'shopify'
        
        # Date filter
        start_date, end_date, filter_label = get_date_filter_params(self.request)
        context['date_filter'] = self.request.GET.get('date_filter', 'this_month')
        context['filter_label'] = filter_label
        context['start_date'] = start_date
        context['end_date'] = end_date
        
        # Subtab
        subtab = self.request.GET.get('subtab', 'all')
        context['subtab'] = subtab
        
        # Shopify leads
        shopify_filter = Q(lead_source__icontains='shopify') | Q(source_type='shopify')
        all_shopify_leads = Lead.objects.filter(shopify_filter, is_active=True)
        filtered_leads = all_shopify_leads.filter(
            created__date__gte=start_date,
            created__date__lte=end_date
        )
        
        # KPIs
        context['total_leads'] = filtered_leads.count()
        context['pending_leads'] = filtered_leads.filter(conversion_status='pending').count()
        context['won_leads'] = filtered_leads.filter(conversion_status='won').count()
        context['lost_leads'] = filtered_leads.filter(conversion_status='lost').count()
        
        decided = context['won_leads'] + context['lost_leads']
        context['conversion_rate'] = round((context['won_leads'] / decided * 100) if decided > 0 else 0, 1)
        
        context['total_revenue'] = filtered_leads.filter(
            conversion_status='won'
        ).aggregate(total=Sum('conversion_value'))['total'] or Decimal('0')
        
        # Shopify specific breakdown
        context['orders_leads'] = filtered_leads.filter(lead_source='shopify_order').count()
        context['abandoned_leads'] = filtered_leads.filter(
            lead_source__in=['shopify_abandoned_checkout', 'shopify_abandoned_cart']
        ).count()
        context['recovered_leads'] = filtered_leads.filter(
            lead_source__in=['shopify_abandoned_checkout', 'shopify_abandoned_cart'],
            status_reason='recovered'
        ).count()
        
        # Recovery rate
        if context['abandoned_leads'] > 0:
            context['recovery_rate'] = round(context['recovered_leads'] / context['abandoned_leads'] * 100, 1)
        else:
            context['recovery_rate'] = 0
        
        # COD vs Prepaid (from orders — if fields exist)
        orders = ShopifyOrder.objects.filter(
            created__date__gte=start_date,
            created__date__lte=end_date,
            is_active=True
        )
        try:
            context['cod_orders'] = orders.filter(
                Q(financial_status__icontains='cod')
            ).count()
            context['prepaid_orders'] = orders.exclude(
                Q(financial_status__icontains='cod')
            ).count()
        except Exception:
            context['cod_orders'] = 0
            context['prepaid_orders'] = orders.count()
        
        # Filter leads by subtab
        if subtab == 'orders':
            filtered_leads = filtered_leads.filter(lead_source='shopify_order')
        elif subtab == 'abandoned':
            filtered_leads = filtered_leads.filter(
                lead_source__in=['shopify_abandoned_checkout', 'shopify_abandoned_cart']
            )
        elif subtab == 'recovered':
            filtered_leads = filtered_leads.filter(
                status_reason='recovered'
            )
        
        context['recent_leads'] = filtered_leads.select_related('assigned_to', 'converted_order').order_by('-created')[:50]
        
        return context


class OtherLeadsView(LoginRequiredMixin, TemplateView):
    """
    Other Leads subpage (not WhatsApp or Shopify).
    """
    template_name = 'marketing/leads/other.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Other Leads'
        context['is_leads'] = True
        context['active_tab'] = 'other'
        
        # Date filter
        start_date, end_date, filter_label = get_date_filter_params(self.request)
        context['date_filter'] = self.request.GET.get('date_filter', 'this_month')
        context['filter_label'] = filter_label
        context['start_date'] = start_date
        context['end_date'] = end_date
        
        # Other leads (not WhatsApp or Shopify)
        wa_filter = Q(lead_source__icontains='whatsapp') | Q(source_type='whatsapp')
        shopify_filter = Q(lead_source__icontains='shopify') | Q(source_type='shopify')
        
        other_leads = Lead.objects.filter(is_active=True).exclude(wa_filter).exclude(shopify_filter)
        filtered_leads = other_leads.filter(
            created__date__gte=start_date,
            created__date__lte=end_date
        )
        
        # KPIs
        context['total_leads'] = filtered_leads.count()
        context['pending_leads'] = filtered_leads.filter(conversion_status='pending').count()
        context['won_leads'] = filtered_leads.filter(conversion_status='won').count()
        context['lost_leads'] = filtered_leads.filter(conversion_status='lost').count()
        
        decided = context['won_leads'] + context['lost_leads']
        context['conversion_rate'] = round((context['won_leads'] / decided * 100) if decided > 0 else 0, 1)
        
        context['total_revenue'] = filtered_leads.filter(
            conversion_status='won'
        ).aggregate(total=Sum('conversion_value'))['total'] or Decimal('0')
        
        # Source breakdown
        sources = filtered_leads.values('lead_source').annotate(
            count=Count('id')
        ).order_by('-count')
        context['source_breakdown'] = list(sources)
        
        context['recent_leads'] = filtered_leads.select_related('assigned_to').order_by('-created')[:50]
        
        return context


class LeadDetailView(LoginRequiredMixin, DetailView):
    """
    Lead detail view with full lifecycle and activity history.
    """
    model = Lead
    template_name = 'marketing/leads/detail.html'
    context_object_name = 'lead'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lead = self.object
        context['title'] = f'Lead: {lead.name or lead.phone_no}'
        context['is_leads'] = True
        
        # Activity history
        context['activities'] = LeadActivity.objects.filter(
            lead=lead
        ).order_by('-created')[:50]
        
        # Linked order details
        if lead.converted_order:
            context['order'] = lead.converted_order
        
        # Status history (from activities)
        context['status_changes'] = LeadActivity.objects.filter(
            lead=lead,
            activity_type='status_change'
        ).order_by('-created')
        
        # Config for matching window
        context['config'] = LeadMatchingConfig.get_config()
        
        # Time in current status
        if lead.conversion_status_at:
            context['days_in_status'] = (timezone.now() - lead.conversion_status_at).days
        else:
            context['days_in_status'] = (timezone.now() - lead.created).days
        
        return context


# API endpoints for AJAX
@require_GET
def leads_chart_data(request):
    """API endpoint for leads trend chart data."""
    start_date, end_date, _ = get_date_filter_params(request)
    
    leads = Lead.objects.filter(
        is_active=True,
        created__date__gte=start_date,
        created__date__lte=end_date
    ).annotate(
        date=TruncDate('created')
    ).values('date').annotate(
        total=Count('id'),
        won=Count('id', filter=Q(conversion_status='won')),
        lost=Count('id', filter=Q(conversion_status='lost')),
    ).order_by('date')
    
    return JsonResponse({
        'labels': [item['date'].strftime('%Y-%m-%d') for item in leads],
        'datasets': {
            'total': [item['total'] for item in leads],
            'won': [item['won'] for item in leads],
            'lost': [item['lost'] for item in leads],
        }
    })
