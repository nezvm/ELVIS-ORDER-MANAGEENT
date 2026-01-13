from django.urls import path
from . import views

app_name = 'logistics'

urlpatterns = [
    # Dashboard
    path('panel/', views.LogisticsPanelView.as_view(), name='panel'),
    path('api/dashboard-data/', views.logistics_dashboard_data, name='dashboard_data'),
    
    # Shipping Dashboard
    path('shipping/', views.ShippingDashboardView.as_view(), name='shipping_dashboard'),
    path('shipping/allocate/', views.allocate_orders, name='allocate_orders'),
    path('shipping/bulk-allocate/', views.bulk_allocate, name='bulk_allocate'),
    path('shipping/force-book/<uuid:order_pk>/', views.force_book_awb, name='force_book_awb'),
    
    # Carriers
    path('carriers/', views.CarrierListView.as_view(), name='carrier_list'),
    path('carriers/create/', views.CarrierCreateView.as_view(), name='carrier_create'),
    path('carriers/<uuid:pk>/', views.CarrierDetailView.as_view(), name='carrier_detail'),
    path('carriers/<uuid:pk>/update/', views.CarrierUpdateView.as_view(), name='carrier_update'),
    path('carriers/<uuid:pk>/delete/', views.CarrierDeleteView.as_view(), name='carrier_delete'),
    path('carriers/<uuid:pk>/test/', views.test_carrier_connection, name='test_carrier'),
    path('carriers/<uuid:pk>/logs/', views.carrier_api_logs, name='carrier_logs'),
    
    # Shipments
    path('shipments/', views.ShipmentListView.as_view(), name='shipment_list'),
    path('shipments/<uuid:pk>/', views.ShipmentDetailView.as_view(), name='shipment_detail'),
    path('shipments/<uuid:pk>/track/', views.track_shipment, name='track_shipment'),
    path('shipments/<uuid:pk>/cancel/', views.cancel_shipment, name='cancel_shipment'),
    path('shipments/<uuid:pk>/label/', views.download_label, name='download_label'),
    
    # Shipping Rules
    path('rules/', views.ShippingRuleListView.as_view(), name='rule_list'),
    path('rules/create/', views.ShippingRuleCreateView.as_view(), name='rule_create'),
    path('rules/<uuid:pk>/', views.ShippingRuleDetailView.as_view(), name='rule_detail'),
    path('rules/<uuid:pk>/update/', views.ShippingRuleUpdateView.as_view(), name='rule_update'),
    path('rules/<uuid:pk>/delete/', views.ShippingRuleDeleteView.as_view(), name='rule_delete'),
    
    # Pincode Rules
    path('pincode-rules/', views.PincodeRuleListView.as_view(), name='pincode_rule_list'),
    path('pincode-rules/create/', views.PincodeRuleCreateView.as_view(), name='pincode_rule_create'),
    path('pincode-rules/<uuid:pk>/update/', views.PincodeRuleUpdateView.as_view(), name='pincode_rule_update'),
    path('pincode-rules/<uuid:pk>/delete/', views.PincodeRuleDeleteView.as_view(), name='pincode_rule_delete'),
    path('pincode-rules/bulk-upload/', views.bulk_upload_pincodes, name='bulk_upload_pincodes'),
    
    # Channel Rules
    path('channel-rules/', views.ChannelRuleListView.as_view(), name='channel_rule_list'),
    path('channel-rules/create/', views.ChannelRuleCreateView.as_view(), name='channel_rule_create'),
    path('channel-rules/<uuid:pk>/update/', views.ChannelRuleUpdateView.as_view(), name='channel_rule_update'),
    path('channel-rules/<uuid:pk>/delete/', views.ChannelRuleDeleteView.as_view(), name='channel_rule_delete'),
    
    # NDR Management
    path('ndr/', views.NDRListView.as_view(), name='ndr_list'),
    path('ndr/<uuid:pk>/', views.NDRDetailView.as_view(), name='ndr_detail'),
    path('ndr/<uuid:pk>/action/', views.ndr_action, name='ndr_action'),
    
    # Settings
    path('settings/', views.ShippingSettingsView.as_view(), name='shipping_settings'),
    
    # API Logs
    path('api-logs/', views.APILogListView.as_view(), name='api_log_list'),
]
