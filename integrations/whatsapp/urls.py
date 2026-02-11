from django.urls import path
from . import views

# These URLs will be included under 'integrations/' namespace
# but we need to add a 'whatsapp/' prefix in the main integrations/urls.py

urlpatterns = [
    # Webhook endpoint (public - no auth required)
    path('webhook/', views.whatsapp_webhook, name='whatsapp_webhook'),
    
    # UI Views (auth required)
    path('', views.WhatsAppDashboardView.as_view(), name='whatsapp_dashboard'),
    path('customers/', views.WhatsAppCustomerListView.as_view(), name='whatsapp_customer_list'),
    path('customer/<uuid:pk>/', views.WhatsAppCustomerDetailView.as_view(), name='whatsapp_customer_detail'),
    
    # Direct Import - Primary method for existing numbers
    path('import/', views.WhatsAppImportView.as_view(), name='whatsapp_import'),
    path('import-number/', views.import_whatsapp_number, name='whatsapp_import_number'),
    
    # Embedded Signup - Connect Numbers (for future use with third-party clients)
    path('connect/', views.WhatsAppConnectView.as_view(), name='whatsapp_connect'),
    path('save-connection/', views.save_whatsapp_connection, name='whatsapp_save_connection'),
    path('disconnect/<uuid:number_id>/', views.disconnect_whatsapp_number, name='whatsapp_disconnect'),
]
