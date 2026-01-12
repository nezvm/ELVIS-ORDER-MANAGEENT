from django.contrib import admin

from core.base import BaseAdmin
from .models import Account, Channel, Customer, Order, Product, ProductPrice
# Register your models here.

@admin.register(Customer)
class CustomerAdmin(BaseAdmin):
    list_filter = ("phone_no",'customer_name','pincode','state','city')
    search_fields =("customer_name",'phone_no',)
    list_display = ("id", "phone_no",'customer_name','pincode','state','city')


@admin.register(Product)
class ProductAdmin(BaseAdmin):
    list_filter = ('size','price')
    search_fields =("product_name",'product_code')
    list_display = ("id", "__str__",)


@admin.register(Order)
class OrderAdmin(BaseAdmin):
    list_filter = ("channel",'customer','is_active')
    autocomplete_fields =("customer",)
    list_display = ("id", "__str__", 'utr','total_amount','is_active')


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
