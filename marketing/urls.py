from django.urls import path
from . import views

app_name = 'marketing'

urlpatterns = [
    # Leads
    path('leads/', views.LeadListView.as_view(), name='lead_list'),
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
