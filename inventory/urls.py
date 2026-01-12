from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # Dashboard
    path('', views.InventoryDashboardView.as_view(), name='dashboard'),
    
    # Warehouses
    path('warehouses/', views.WarehouseListView.as_view(), name='warehouse_list'),
    path('warehouse/<uuid:pk>/', views.WarehouseDetailView.as_view(), name='warehouse_detail'),
    path('warehouse/new/', views.WarehouseCreateView.as_view(), name='warehouse_create'),
    path('warehouse/<uuid:pk>/update/', views.WarehouseUpdateView.as_view(), name='warehouse_update'),
    path('warehouse/<uuid:pk>/delete/', views.WarehouseDeleteView.as_view(), name='warehouse_delete'),
    
    # Stock Levels
    path('stock/', views.StockLevelListView.as_view(), name='stock_list'),
    path('stock/<uuid:pk>/', views.StockLevelDetailView.as_view(), name='stock_detail'),
    
    # Stock Movements
    path('movements/', views.StockMovementListView.as_view(), name='movement_list'),
    path('movement/new/', views.StockMovementCreateView.as_view(), name='movement_create'),
    
    # Stock Transfers
    path('transfers/', views.StockTransferListView.as_view(), name='transfer_list'),
    path('transfer/<uuid:pk>/', views.StockTransferDetailView.as_view(), name='transfer_detail'),
    path('transfer/new/', views.StockTransferCreateView.as_view(), name='transfer_create'),
    
    # Alerts
    path('alerts/', views.InventoryAlertListView.as_view(), name='alert_list'),
    
    # API Endpoints
    path('api/adjust-stock/', views.adjust_stock, name='adjust_stock'),
    path('api/alert/<uuid:pk>/acknowledge/', views.acknowledge_alert, name='acknowledge_alert'),
    path('api/product/<int:product_id>/stock/', views.get_product_stock, name='product_stock'),
    path('api/dashboard-data/', views.inventory_dashboard_data, name='dashboard_data'),
]
