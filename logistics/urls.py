from django.urls import path
from . import views

app_name = 'logistics'

urlpatterns = [
    # Logistics Panel
    path('panel/', views.LogisticsPanelView.as_view(), name='panel'),
    
    # Carriers
    path('carriers/', views.CarrierListView.as_view(), name='carrier_list'),
    path('carrier/<uuid:pk>/', views.CarrierDetailView.as_view(), name='carrier_detail'),
    path('carrier/new/', views.CarrierCreateView.as_view(), name='carrier_create'),
    path('carrier/<uuid:pk>/update/', views.CarrierUpdateView.as_view(), name='carrier_update'),
    path('carrier/<uuid:pk>/delete/', views.CarrierDeleteView.as_view(), name='carrier_delete'),
    
    # Shipping Rules
    path('rules/', views.ShippingRuleListView.as_view(), name='rule_list'),
    path('rule/<uuid:pk>/', views.ShippingRuleDetailView.as_view(), name='rule_detail'),
    path('rule/new/', views.ShippingRuleCreateView.as_view(), name='rule_create'),
    path('rule/<uuid:pk>/update/', views.ShippingRuleUpdateView.as_view(), name='rule_update'),
    path('rule/<uuid:pk>/delete/', views.ShippingRuleDeleteView.as_view(), name='rule_delete'),
    
    # Shipments
    path('shipments/', views.ShipmentListView.as_view(), name='shipment_list'),
    path('shipment/<uuid:pk>/', views.ShipmentDetailView.as_view(), name='shipment_detail'),
    path('shipment/<uuid:pk>/update/', views.ShipmentUpdateView.as_view(), name='shipment_update'),
    
    # NDR Management
    path('ndr/', views.NDRListView.as_view(), name='ndr_list'),
    path('ndr/<uuid:pk>/', views.NDRDetailView.as_view(), name='ndr_detail'),
    
    # API Endpoints
    path('api/assign-carrier/', views.assign_carrier, name='assign_carrier'),
    path('api/ndr/<uuid:pk>/action/', views.update_ndr_action, name='update_ndr_action'),
    path('api/carrier-recommendation/', views.get_carrier_recommendation, name='carrier_recommendation'),
    path('api/dashboard-data/', views.logistics_dashboard_data, name='dashboard_data'),
]
