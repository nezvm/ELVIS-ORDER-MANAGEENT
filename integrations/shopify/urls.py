from django.urls import path
from . import views

app_name = 'shopify'

urlpatterns = [
    # Universal webhook endpoint
    path('webhook/', views.shopify_webhook, name='webhook'),
    
    # Topic-specific webhook endpoints
    path('orders/', views.shopify_orders_webhook, name='orders_webhook'),
    path('checkouts/', views.shopify_checkouts_webhook, name='checkouts_webhook'),
    path('fulfillments/', views.shopify_fulfillments_webhook, name='fulfillments_webhook'),
]
