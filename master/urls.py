from django.urls import path

from . import views

app_name = "master"

urlpatterns = [
    path("get_item_details/", views.get_item_details, name="get_item_details"),
    path('get_customer_details/', views.get_customer_details, name='get_customer_details'),
    
    # Quick Order Entry
    path("orders/quick-entry/", views.QuickOrderEntryView.as_view(), name="quick_order_entry"),
    path("orders/quick-entry/save/", views.quick_order_save, name="quick_order_save"),
    path("api/check-utr/", views.check_utr, name="check_utr"),
    path("api/search-products/", views.search_products, name="search_products"),
    path("api/lookup-pincode/", views.lookup_pincode, name="lookup_pincode"),
    
    #account
    path("accounts/", views.AccountListView.as_view(), name="account_list"),
    path("account/<str:pk>/", views.AccountDetailView.as_view(), name="account_detail"),
    path("new/account/", views.AccountCreateView.as_view(), name="account_create"),
    path("account/<str:pk>/update/", views.AccountUpdateView.as_view(), name="account_update"),
    path("account/<str:pk>/delete/", views.AccountDeleteView.as_view(), name="account_delete"),
    #channel
    path("channels/", views.ChannelListView.as_view(), name="channel_list"),
    path("channel/<str:pk>/", views.ChannelDetailView.as_view(), name="channel_detail"),
    path("new/Channel/", views.ChannelCreateView.as_view(), name="channel_create"),
    path("channel/<str:pk>/update/", views.ChannelUpdateView.as_view(), name="channel_update"),
    path("channel/<str:pk>/delete/", views.ChannelDeleteView.as_view(), name="channel_delete"),
    #product
    path("products/", views.ProductListView.as_view(), name="product_list"),
    path("product/<str:pk>/", views.ProductDetailView.as_view(), name="product_detail"),
    path("new/product/", views.ProductCreateView.as_view(), name="product_create"),
    path("product/<str:pk>/update/", views.ProductUpdateView.as_view(), name="product_update"),
    path("product/<str:pk>/delete/", views.ProductDeleteView.as_view(), name="product_delete"),
    #productprice
    path("productprices/", views.ProductPriceListView.as_view(), name="productprice_list"),
    path("productprice/<str:pk>/", views.ProductPriceDetailView.as_view(), name="productprice_detail"),
    path("new/productprice/", views.ProductPriceCreateView.as_view(), name="productprice_create"),
    path("productprice/<str:pk>/update/", views.ProductPriceUpdateView.as_view(), name="productprice_update"),
    path("productprice/<str:pk>/delete/", views.ProductPriceDeleteView.as_view(), name="productprice_delete"),
    #Customer
    path("customers/", views.CustomerListView.as_view(), name="customer_list"),
    path("customer/<str:pk>/", views.CustomerDetailView.as_view(), name="customer_detail"),
    path("new/customer/", views.CustomerCreateView.as_view(), name="customer_create"),
    path("customer/<str:pk>/update/", views.CustomerUpdateView.as_view(), name="customer_update"),
    path("customer/<str:pk>/delete/", views.CustomerDeleteView.as_view(), name="customer_delete"),
    #order
    path("orders/", views.OrderListView.as_view(), name="order_list"),
    path("order/<str:pk>/", views.OrderDetailView.as_view(), name="order_detail"),
    path("new/order/", views.OrderCreateView.as_view(), name="order_create"),
    path("order/<str:pk>/update/", views.OrderUpdateView.as_view(), name="order_update"),
    path("order/<str:pk>/delete/", views.OrderDeleteView.as_view(), name="order_delete"),
]