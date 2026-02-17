from django.urls import path
from . import views

app_name = 'wabis'

urlpatterns = [
    # Webhook endpoint (public - no auth)
    path('webhook/', views.wabis_webhook, name='webhook'),
    
    # Dashboard & Config (auth required)
    path('', views.WabisDashboardView.as_view(), name='dashboard'),
    path('config/', views.WabisConfigView.as_view(), name='config'),
    path('numbers/', views.WabisNumberListView.as_view(), name='number_list'),
    path('numbers/add/', views.add_wabis_number, name='number_add'),
    path('numbers/<uuid:pk>/delete/', views.delete_wabis_number, name='number_delete'),
    path('numbers/<uuid:pk>/update-bot-id/', views.update_wabis_number_bot_id, name='number_update_bot_id'),
    
    # Customers/Leads
    path('customers/', views.WabisCustomerListView.as_view(), name='customer_list'),
    path('customers/<uuid:pk>/', views.WabisCustomerDetailView.as_view(), name='customer_detail'),
    
    # Webhook logs
    path('logs/', views.WabisWebhookLogListView.as_view(), name='webhook_logs'),
    
    # API
    path('api/sync-status/', views.sync_status, name='sync_status'),
    path('api/trigger-sync/', views.trigger_api_sync, name='trigger_sync'),
    path('api/save-config/', views.save_wabis_config, name='save_config'),
    path('api/test-connection/', views.test_wabis_connection, name='test_connection'),
]
