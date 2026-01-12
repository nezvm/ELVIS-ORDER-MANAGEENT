from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from .views import (
    CustomerViewSet, ProductViewSet, OrderViewSet,
    DynamicChannelViewSet,
    CarrierViewSet, ShipmentViewSet, ShippingRuleViewSet,
    WarehouseViewSet, StockLevelViewSet,
    CustomerProfileViewSet, CustomerSegmentViewSet
)

router = DefaultRouter()

# Master endpoints
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'orders', OrderViewSet, basename='order')

# Channel Config endpoints
router.register(r'channels', DynamicChannelViewSet, basename='channel')

# Logistics endpoints
router.register(r'carriers', CarrierViewSet, basename='carrier')
router.register(r'shipments', ShipmentViewSet, basename='shipment')
router.register(r'shipping-rules', ShippingRuleViewSet, basename='shipping-rule')

# Inventory endpoints
router.register(r'warehouses', WarehouseViewSet, basename='warehouse')
router.register(r'stock-levels', StockLevelViewSet, basename='stock-level')

# Segmentation endpoints
router.register(r'customer-profiles', CustomerProfileViewSet, basename='customer-profile')
router.register(r'segments', CustomerSegmentViewSet, basename='segment')

app_name = 'api'

urlpatterns = [
    # API Schema/Documentation
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='api:schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='api:schema'), name='redoc'),
    
    # API endpoints
    path('', include(router.urls)),
]
