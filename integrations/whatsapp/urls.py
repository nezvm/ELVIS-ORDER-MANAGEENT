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
]
