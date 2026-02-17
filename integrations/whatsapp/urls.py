from django.urls import path
from django.views.generic import RedirectView
from . import views

# All old UI routes redirect to Wabis. Webhook kept for backward compatibility.
urlpatterns = [
    # Webhook endpoint (public - no auth required) - KEEP for backward compatibility
    path('webhook/', views.whatsapp_webhook, name='whatsapp_webhook'),
    
    # Redirect all UI Views to Wabis BSP
    path('', RedirectView.as_view(pattern_name='integrations:wabis:dashboard', permanent=False), name='whatsapp_dashboard'),
    path('leads/', RedirectView.as_view(url='/marketing/leads/?lead_source=whatsapp', permanent=False), name='whatsapp_customer_list'),
    path('lead/<uuid:pk>/', RedirectView.as_view(url='/marketing/leads/?lead_source=whatsapp', permanent=False), name='whatsapp_customer_detail'),
    
    # Redirect Performance Dashboard to Marketing Dashboard
    path('performance/', RedirectView.as_view(pattern_name='marketing:dashboard', permanent=False), name='whatsapp_lead_performance'),
    
    # Redirect Lifecycle to Leads
    path('lead/<uuid:pk>/lifecycle/', RedirectView.as_view(url='/marketing/leads/?lead_source=whatsapp', permanent=False), name='whatsapp_customer_lifecycle'),
    
    # Redirect BSP Connection to Wabis
    path('connect/', RedirectView.as_view(pattern_name='integrations:wabis:dashboard', permanent=False), name='whatsapp_connect'),
    path('bsp-connect/', RedirectView.as_view(pattern_name='integrations:wabis:dashboard', permanent=False), name='whatsapp_bsp_connect'),
    path('disconnect/<uuid:number_id>/', RedirectView.as_view(pattern_name='integrations:wabis:dashboard', permanent=False), name='whatsapp_disconnect'),
    
    # API Endpoints - Redirect to marketing sync
    path('api/trigger-sync/', RedirectView.as_view(pattern_name='marketing:dashboard', permanent=False), name='whatsapp_trigger_sync'),
    path('api/send-conversions/', RedirectView.as_view(pattern_name='marketing:dashboard', permanent=False), name='whatsapp_send_conversions'),
]
