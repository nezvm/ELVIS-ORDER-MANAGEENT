
from core.base import BaseTable
from django_tables2 import columns
from .models import Account, Channel, Customer, Order, Product, ProductPrice

class OrderTable(BaseTable):
    action = columns.TemplateColumn(
        """
        <div class="btn-group">
        <a class="btn btn-default mx-1 btn-sm" title='View' href="{{record.get_absolute_url}}?type={{record.channel.channel_type}}"> <i class="fa fa-eye"></i></a>
        <a class="btn btn-default mx-1 btn-sm" title='Edit' href="{{record.get_update_url}}?type={{record.channel.channel_type}}"><i class="fa fa-edit"></i> </a>
        <a class="btn btn-default mx-1 btn-sm" title='Delete' href="{{record.get_delete_url}}?type={{record.channel.channel_type}}"><i class="fa fa-trash"></i></a>
        </div>
        """,
        orderable=False,
    )
    city = columns.TemplateColumn("""{{ record.customer.capitalized_city }}""", orderable=True,verbose_name="City")
    state = columns.TemplateColumn("""{{ record.customer.capitalized_state }}""", orderable=True,verbose_name="State")
    pincode = columns.TemplateColumn("""{{ record.customer.get_address_pincode }}""", orderable=True,verbose_name="Pincode")
    country = columns.TemplateColumn("""{{ record.customer.capitalized_country }}""", orderable=True,verbose_name="Country",visible=False)
    address = columns.TemplateColumn("""{{ record.customer.get_address }}""", orderable=True,verbose_name="Address",visible=False)
    phone_no = columns.TemplateColumn("""{{ record.customer.phone_no }}""", orderable=True,verbose_name="Phone")
    mobile = columns.TemplateColumn("""{{ record.customer.alternate_phone_no }}""", orderable=True,verbose_name="Mobile",visible=False)
    product = columns.TemplateColumn("""{% for i in record.get_items %}{{ i.product }}{% if not forloop.last %},{% endif %} {% endfor %}""", orderable=True,verbose_name="Product",visible=False)
    weight = columns.TemplateColumn("""{{100}}""", orderable=True,verbose_name="Weight",visible=False)
    length = columns.TemplateColumn("""{{ 10 }}""", orderable=True,verbose_name="Shipment Length",visible=False)
    breadth = columns.TemplateColumn("""{{ 10 }}""", orderable=True,verbose_name="Shipment Breadth",visible=False)
    height = columns.TemplateColumn("""{{ 2 }}""", orderable=True,verbose_name="Shipment Height",visible=False)
    customer = columns.TemplateColumn("""{{ record.customer.get_address_name }}""", orderable=True,verbose_name="Name")
    
    class Meta:
        model = Order
        fields = ('created','channel','order_no',"customer",'city','state','country','address','pincode','phone_no','mobile','weight','length','breadth','height','product','utr','order_by','account','cod_charge','total_amount')
        attrs = {"class": "table border-0 table-hover table-striped  datatable-custom"}

class ProductTable(BaseTable):
    created = None
    class Meta:
        model = Product
        fields = ("product_name", "product_code",'size','price')
        attrs = {"class": "table border-0 table-hover table-striped "}

class ChannelTable(BaseTable):
    created = None
    class Meta:
        model = Channel
        fields = ("prefix", "channel_type")
        attrs = {"class": "table border-0 table-hover table-striped "}


class ProductPriceTable(BaseTable):
    created = None
    class Meta:
        model = ProductPrice
        fields = ("product", "channel",'price')
        attrs = {"class": "table border-0 table-hover table-striped "}


class CustomerTable(BaseTable):
    created = None
    class Meta:
        model = Customer
        fields = ("phone_no", "customer_name",'pincode','address','city','state','country','alternate_phone_no')
        attrs = {"class": "table border-0 table-hover table-striped "}


class AccountTable(BaseTable):
    created = None
    balance = columns.TemplateColumn("""{{ record.get_balance }}""", orderable=True,verbose_name="Total")
    get_today_orders = columns.TemplateColumn("""{{ record.get_today_orders }}""", orderable=True,verbose_name="Today Orders")
    class Meta:
        model = Account
        fields = ("name", "code",'balance','get_today_orders')
        attrs = {"class": "table border-0 table-hover table-striped "}

