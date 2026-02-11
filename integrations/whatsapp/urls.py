from django.urls import path
from . import views

urlpatterns = [
    # Webhook endpoint (public - no auth required)
    path('webhook/', views.whatsapp_webhook, name='whatsapp_webhook'),
    
    # UI Views (auth required)
    path('', views.WhatsAppDashboardView.as_view(), name='whatsapp_dashboard'),
    path('leads/', views.WhatsAppCustomerListView.as_view(), name='whatsapp_customer_list'),
    path('lead/<uuid:pk>/', views.WhatsAppCustomerDetailView.as_view(), name='whatsapp_customer_detail'),
    
    # Embedded Signup - Connect Numbers
    path('connect/', views.WhatsAppConnectView.as_view(), name='whatsapp_connect'),
    path('save-connection/', views.save_whatsapp_connection, name='whatsapp_save_connection'),
    path('disconnect/<uuid:number_id>/', views.disconnect_whatsapp_number, name='whatsapp_disconnect'),
]
