from django.urls import path
from . import views

urlpatterns = [
    # Webhook endpoint (public - no auth required)
    path('webhook/', views.whatsapp_webhook, name='whatsapp_webhook'),
    
    # UI Views (auth required)
    path('', views.WhatsAppDashboardView.as_view(), name='whatsapp_dashboard'),
    path('leads/', views.WhatsAppCustomerListView.as_view(), name='whatsapp_customer_list'),
    path('lead/<uuid:pk>/', views.WhatsAppCustomerDetailView.as_view(), name='whatsapp_customer_detail'),
    
    # Lead Performance Dashboard
    path('performance/', views.LeadPerformanceDashboardView.as_view(), name='whatsapp_lead_performance'),
    
    # Customer Lifecycle View
    path('lead/<uuid:pk>/lifecycle/', views.CustomerLifecycleView.as_view(), name='whatsapp_customer_lifecycle'),
    
    # Connect Numbers
    path('connect/', views.WhatsAppConnectView.as_view(), name='whatsapp_connect'),
    path('save-connection/', views.save_whatsapp_connection, name='whatsapp_save_connection'),
    path('disconnect/<uuid:number_id>/', views.disconnect_whatsapp_number, name='whatsapp_disconnect'),
    
    # Direct Connect API (for existing WABAs)
    path('direct-connect/', views.direct_connect_number, name='whatsapp_direct_connect'),
    path('verify-connection/', views.verify_connection, name='whatsapp_verify_connection'),
    
    # API Endpoints
    path('api/trigger-sync/', views.trigger_daily_sync, name='whatsapp_trigger_sync'),
    path('api/send-conversions/', views.send_pending_conversions_api, name='whatsapp_send_conversions'),
]
