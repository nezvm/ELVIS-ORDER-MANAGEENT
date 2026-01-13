from django.contrib import admin

from core.base import BaseAdmin
from .models import (
    Account, Channel, Customer, Order, Product, ProductPrice, 
    CourierPartner, Vendor, Purchase, PurchaseItem, PostOrder,
    OrderItem, OrderTrackingHistory, PincodeRuleLegacy
)
# Register your models here.

@admin.register(Customer)
class CustomerAdmin(BaseAdmin):
    list_filter = ("phone_no",'customer_name','pincode','state','city')
    search_fields =("customer_name",'phone_no',)
    list_display = ("id", "phone_no",'customer_name','pincode','state','city')


@admin.register(Product)
class ProductAdmin(BaseAdmin):
    list_filter = ('size','price', 'is_hide')
    search_fields =("product_name",'product_code')
    list_display = ("id", "__str__", 'price', 'opning_stock', 'get_stock', 'is_hide')


@admin.register(Order)
class OrderAdmin(BaseAdmin):
    list_filter = ("channel",'customer','is_active', 'stage', 'courier_partner')
    autocomplete_fields =("customer", "courier_partner")
    search_fields = ('order_no', 'tracking_id', 'name', 'phone')
    list_display = ("id", "__str__", 'order_no', 'stage', 'tracking_id', 'utr','total_amount','is_active')


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'product', 'quantity', 'amount')
    autocomplete_fields = ('order', 'product')
    search_fields = ('order__order_no', 'product__product_name')


@admin.register(Channel)
class ChannelAdmin(BaseAdmin):
    list_filter = ('is_active',)
    search_fields = ('prefix','channel_type')
    list_display = ("id", "__str__", 'prefix','channel_type','is_active')


@admin.register(ProductPrice)
class ProductPriceAdmin(BaseAdmin):
    list_filter = ("product",'channel','is_active')
    autocomplete_fields =("product",'channel')
    list_display = ("id", "__str__","product",'channel','is_active')


@admin.register(Account)
class AccountAdmin(BaseAdmin):
    list_filter = ('is_active',)
    search_fields = ('name','code')
    list_display = ("id", "__str__", 'name','code','is_active')


# =============================================================================
# NEW MODELS FROM ORIGINAL ZIP
# =============================================================================

@admin.register(CourierPartner)
class CourierPartnerAdmin(BaseAdmin):
    list_display = ('id', 'name', 'code', 'tracking_slug', 'is_active')
    search_fields = ('name', 'code')
    list_filter = ('is_active',)


@admin.register(Vendor)
class VendorAdmin(BaseAdmin):
    list_display = ('id', 'name', 'contact_details', 'is_active')
    search_fields = ('name', 'contact_details')


@admin.register(Purchase)
class PurchaseAdmin(BaseAdmin):
    list_display = ('id', 'invoice_number', 'invoice_date', 'vendor', 'grand_total', 'net_amount')
    list_filter = ('invoice_date', 'vendor')
    search_fields = ('invoice_number',)
    autocomplete_fields = ('vendor',)


@admin.register(PurchaseItem)
class PurchaseItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'purchase', 'item', 'quantity', 'price', 'line_total')
    autocomplete_fields = ('purchase', 'item')


@admin.register(PostOrder)
class PostOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'barcode', 'order', 'is_complete')
    search_fields = ('barcode', 'order__order_no')
    list_filter = ('is_complete',)


@admin.register(OrderTrackingHistory)
class OrderTrackingHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'status', 'timestamp')
    list_filter = ('status',)
    search_fields = ('order__order_no',)


@admin.register(PincodeRuleLegacy)
class PincodeRuleLegacyAdmin(admin.ModelAdmin):
    list_display = ('id', 'courier', 'pincode', 'cscrcd', 'priority')
    list_filter = ('courier',)
    search_fields = ('pincode',)
