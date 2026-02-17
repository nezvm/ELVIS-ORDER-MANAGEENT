from django.urls import path
from . import views
from . import leads_views
from . import meta_views

app_name = 'marketing'

urlpatterns = [
    # Dashboard
    path('', views.DailyInsightsDashboardView.as_view(), name='dashboard'),
    path('dashboard/', views.DailyInsightsDashboardView.as_view(), name='daily_insights'),
    
    # ==========================================================================
    # META MARKETING (ROAS + Attribution Dashboard)
    # ==========================================================================
    path('overview/', meta_views.MarketingOverviewView.as_view(), name='meta_overview'),
    path('meta/settings/', meta_views.MetaSettingsView.as_view(), name='meta_settings'),
    path('meta/campaigns/', meta_views.CampaignPerformanceView.as_view(), name='meta_campaigns'),
    path('meta/capi-logs/', meta_views.CapiEventLogsView.as_view(), name='capi_logs'),
    
    # Meta API actions
    path('api/meta/test-connection/', meta_views.api_test_meta_connection, name='api_test_meta_connection'),
    path('api/meta/send-test-event/', meta_views.api_send_test_event, name='api_send_test_event'),
    path('api/meta/sync-insights/', meta_views.api_sync_insights, name='api_sync_insights'),
    path('api/meta/run-attribution/', meta_views.api_run_attribution, name='api_run_attribution'),
    path('api/meta/send-pending-capi/', meta_views.api_send_pending_capi, name='api_send_pending_capi'),
    path('api/meta/lead/<uuid:pk>/attribution/', meta_views.api_update_lead_attribution, name='api_update_lead_attribution'),
    path('api/meta/chart-data/', meta_views.api_overview_chart_data, name='api_overview_chart_data'),
    
    # ==========================================================================
    # NEW LEADS MODULE (Revamped)
    # ==========================================================================
    path('leads/', leads_views.LeadsOverviewDashboardView.as_view(), name='leads_overview'),
    path('leads/whatsapp/', leads_views.WhatsAppLeadsView.as_view(), name='leads_whatsapp'),
    path('leads/shopify/', leads_views.ShopifyLeadsView.as_view(), name='leads_shopify'),
    path('leads/other/', leads_views.OtherLeadsView.as_view(), name='leads_other'),
    path('leads/<uuid:pk>/', leads_views.LeadDetailView.as_view(), name='lead_detail_new'),
    path('leads/api/chart-data/', leads_views.leads_chart_data, name='leads_chart_data'),
    
    # ==========================================================================
    # Legacy Leads (keep for backward compatibility)
    # ==========================================================================
    path('lead-list/', views.LeadListView.as_view(), name='lead_list'),
    path('lead/<uuid:pk>/', views.LeadDetailView.as_view(), name='lead_detail'),
    path('lead/new/', views.LeadCreateView.as_view(), name='lead_create'),
    path('lead/<uuid:pk>/update/', views.LeadUpdateView.as_view(), name='lead_update'),
    
    # WhatsApp
    path('whatsapp/', views.WhatsAppDashboardView.as_view(), name='whatsapp_dashboard'),
    path('whatsapp/providers/', views.ProviderListView.as_view(), name='provider_list'),
    path('whatsapp/provider/<uuid:pk>/', views.ProviderDetailView.as_view(), name='provider_detail'),
    path('whatsapp/provider/new/', views.ProviderCreateView.as_view(), name='provider_create'),
    path('whatsapp/provider/<uuid:pk>/update/', views.ProviderUpdateView.as_view(), name='provider_update'),
    path('whatsapp/templates/', views.TemplateListView.as_view(), name='template_list'),
    path('whatsapp/template/new/', views.TemplateCreateView.as_view(), name='template_create'),
    path('whatsapp/notifications/', views.NotificationEventsView.as_view(), name='notification_events'),
    path('whatsapp/logs/', views.MessageLogListView.as_view(), name='message_logs'),
    
    # Campaigns
    path('campaigns/', views.CampaignListView.as_view(), name='campaign_list'),
    path('campaign/<uuid:pk>/', views.CampaignDetailView.as_view(), name='campaign_detail'),
    path('campaign/new/', views.CampaignCreateView.as_view(), name='campaign_create'),
    path('campaign/<uuid:pk>/update/', views.CampaignUpdateView.as_view(), name='campaign_update'),
    
    # Market Insights
    path('insights/', views.MarketInsightsView.as_view(), name='insights'),
    path('insights/hotspots/', views.HotspotsView.as_view(), name='hotspots'),
    path('insights/cold-zones/', views.ColdZonesView.as_view(), name='cold_zones'),
    path('insights/abandoned/', views.AbandonedInsightsView.as_view(), name='abandoned_insights'),
    
    # API Endpoints
    path('api/leads/sync/', views.sync_google_leads, name='sync_leads'),
    path('api/lead/<uuid:pk>/match/', views.match_lead, name='match_lead'),
    path('api/lead/<uuid:pk>/convert/', views.convert_lead, name='convert_lead'),
    path('api/provider/<uuid:pk>/test/', views.test_provider, name='test_provider'),
    path('api/campaign/<uuid:pk>/start/', views.start_campaign, name='start_campaign'),
    path('api/campaign/<uuid:pk>/pause/', views.pause_campaign, name='pause_campaign'),
    path('api/insights/refresh/', views.refresh_insights, name='refresh_insights'),
    path('api/lead-stats/', views.lead_stats_api, name='lead_stats'),
]
