import json
from datetime import datetime, timedelta
from decimal import Decimal
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Sum, Count
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views import View
from django.utils.decorators import method_decorator
from core import mixins
from master.forms import CustomerForm, DateFilter, OrderItemFormSet
from master.models import Account, Channel, Customer, Order, OrderItem, Product, ProductPrice
from master import tables
from accounts.models import User

today = datetime.now().date()
yesterday = today - timedelta(days=1) 
week_start = today - timedelta(days=today.weekday())  # Start of the week (Monday)
week_end = week_start + timedelta(days=6)  # End of the week (Sunday)
current_year = today.year
month = today.month
year = today.year

def get_item_details(request):
    item_id = request.GET.get("itemId")
    type = request.GET.get("type")
    item = get_object_or_404(Product, pk=item_id)
    quantity = Decimal(request.GET.get("quantity")) if request.GET.get("quantity") else Decimal("1")
    price = Decimal(request.GET.get("price")) if request.GET.get("price") else item.get_price(type)
    subtotal_after_tax = Decimal(price * quantity) 
    line_total = round(subtotal_after_tax, 2)
    response = {"price": price, "quantity": quantity,"line_total": line_total}
    return JsonResponse(response)

def get_customer_details(request):
    phone_number = request.GET.get("phone_number")
    customer = Customer.objects.filter(phone_no=phone_number).last()
    if customer:
        response = {'is_true':True,"customer_name": customer.customer_name, "alternate_phone_no": customer.alternate_phone_no, "pincode": customer.pincode, "address": customer.address, "city": customer.city, "state": customer.state, "country": customer.country}
    else:
        response = {'is_true':False,"customer_name": "", "alternate_phone_no": "", "pincode": "", "address": "", "city": "", "state": "", "country": ""}
    return JsonResponse(response)


class AccountListView(mixins.HybridListView):
    model = Account
    table_class = tables.AccountTable
    filterset_fields = {"name": ["contains", "startswith"], "code": ["contains", "startswith"]}
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Accounts"
        context["can_add"] = True
        context["new_link"] = reverse_lazy(f"master:account_create")
        context['is_account'] = True
        return context


class AccountDetailView(mixins.HybridDetailView):
    model = Account
    template_name = "master/account_view.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get filter parameters
        date = self.request.GET.get("date")
        date__lte = self.request.GET.get("date__lte")
        date__gte = self.request.GET.get("date__gte")
        order_by = self.request.GET.get("order_by")
        channel = self.request.GET.get("channel")
        
        # Parse date fields
        def parse_date(date_str):
            try:
                return datetime.strptime(date_str, '%d/%m/%Y').strftime('%Y-%m-%d')
            except (ValueError, TypeError):
                return None
        
        date__lte = parse_date(date__lte)
        date__gte = parse_date(date__gte)
        
        # Initialize form
        form = DateFilter(initial={
            'date': date,
            'date__lte': date__lte,
            'date__gte': date__gte
        })
        
        # Fetch and filter orders
        orders = self.object.get_orders().order_by("-created")
        
        if date:
            if date == 'today':
                orders = orders.filter(created__date=today)
            elif date == 'yesterday':
                orders = orders.filter(created__date=yesterday)
            elif date == 'this_week':
                orders = orders.filter(created__date__range=[week_start, week_end])
            elif date == 'this_month':
                orders = orders.filter(created__month=month)
            elif date == 'this_year':
                orders = orders.filter(created__year=year)
            elif date == 'custom':
                filters = {}
                if date__lte:
                    filters['created__date__lte'] = date__lte
                if date__gte:
                    filters['created__date__gte'] = date__gte
                orders = orders.filter(**filters)
        
        if order_by:
            orders = orders.filter(order_by__id=order_by)
        
        if channel:
            orders = orders.filter(channel__id=channel)
        
        # Add context data
        context["form"] = form
        context["title"] = "Account"
        context['is_account'] = True
        context['orders'] = orders
        return context

class AccountCreateView(mixins.HybridCreateView):
    model = Account
    exclude = ("creator",)
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "New Account"
        context['is_account'] = True
        context['is_master'] = True
        return context


class AccountUpdateView(mixins.HybridUpdateView):
    model = Account
    exclude = ("creator",)
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Update {self.object} Account"
        context['is_account'] = True
        context['is_master'] = True
        return context


class AccountDeleteView(mixins.HybridDeleteView):
    model = Account

#Channel
class ChannelListView(mixins.HybridListView):
    model = Channel
    table_class = tables.ChannelTable
    filterset_fields = {"channel_type": ["exact"], "prefix": ["contains", "startswith"]}
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Channels"
        context["can_add"] = True
        context["new_link"] = reverse_lazy(f"master:channel_create")
        context['is_channel'] = True
        context['is_master'] = True
        return context


class ChannelDetailView(mixins.HybridDetailView):
    model = Channel
    template_name = "master/channel_view.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Channel"
        context['is_channel'] = True
        context['is_master'] = True
        return context


class ChannelCreateView(mixins.HybridCreateView):
    model = Channel
    exclude = ("creator",)
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "New Channel"
        context['is_channel'] = True
        context['is_master'] = True
        return context


class ChannelUpdateView(mixins.HybridUpdateView):
    model = Channel
    exclude = ("creator",)
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Update {self.object} Channel"
        context['is_channel'] = True
        context['is_master'] = True
        return context


class ChannelDeleteView(mixins.HybridDeleteView):
    model = Channel


class ProductListView(mixins.HybridListView):
    model = Product
    table_class = tables.ProductTable
    filterset_fields = {"product_name": ["contains", "startswith"], "product_code": ["contains", "startswith"]}
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Products"
        context["can_add"] = True
        context["new_link"] = reverse_lazy(f"master:product_create")
        context['is_product'] = True
        return context

class ProductDetailView(mixins.HybridDetailView):
    model = Product
    template_name = "master/product_detail.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Product"
        context['is_product'] = True
        return context
    

class ProductCreateView(mixins.HybridCreateView):
    model = Product
    exclude = ("creator",)
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "New Product"
        context['is_product'] = True
        return context


class ProductUpdateView(mixins.HybridUpdateView):
    model = Product
    exclude = ("creator",)
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Update {self.object} Product"
        context['is_product'] = True
        return context


class ProductDeleteView(mixins.HybridDeleteView):
    model = Product


class ProductPriceListView(mixins.HybridListView):
    model = ProductPrice
    table_class = tables.ProductPriceTable
    filterset_fields = {"product": ["exact"], "channel": ["exact"]}
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Product Prices"
        context["can_add"] = True
        context["new_link"] = reverse_lazy(f"master:productprice_create")
        context['is_productprice'] = True
        return context

class ProductPriceDetailView(mixins.HybridDetailView):
    model = ProductPrice
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "ProductPrice"
        context['is_productprice'] = True
        return context

class ProductPriceCreateView(mixins.HybridCreateView):
    model = ProductPrice
    exclude = ("creator",)
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "New ProductPrice"
        context['is_productprice'] = True
        return context


class ProductPriceUpdateView(mixins.HybridUpdateView):
    model = ProductPrice
    exclude = ("creator",)
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Update {self.object} ProductPrice"
        context['is_productprice'] = True
        return context


class ProductPriceDeleteView(mixins.HybridDeleteView):
    model = ProductPrice



class CustomerListView(mixins.HybridListView):
    model = Customer
    table_class = tables.CustomerTable
    filterset_fields = {"phone_no": ["exact"], "pincode": ["exact"], "state": ["exact"], "city": ["exact"], "customer_name": ["contains", "startswith"]}
    search_fields = ('customer__pincode','customer__customer_name','customer__phone_no') 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Customers"
        # context["can_add"] = True
        # context["new_link"] = reverse_lazy(f"master:customer_create")
        context['is_customer'] = True
        return context



class CustomerDetailView(mixins.HybridDetailView):
    model = Customer
    template_name = "master/customer_view.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Customer"
        context['is_customer'] = True
        return context

class CustomerCreateView(mixins.HybridCreateView):
    model = Customer
    exclude = ("creator",)
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "New Customer"
        context['is_customer'] = True
        return context


class CustomerUpdateView(mixins.HybridUpdateView):
    model = Customer
    exclude = ("creator",)
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Update {self.object} Customer"
        context['is_customer'] = True
        return context


class CustomerDeleteView(mixins.HybridDeleteView):
    model = Customer



class OrderListView(mixins.HybridListView):
    model = Order
    table_class = tables.OrderTable
    filterset_fields = { "channel__channel_type": ["exact"],'order_by':['exact'], "account": ["exact",]}
    template_name = "order/order_list.html"
    search_fields = ("order_no",'customer__pincode','utr','customer__customer_name','customer__phone_no') 

    def get_queryset(self):
        queryset = super().get_queryset()
        type = self.request.GET.get("type")
        account = self.request.GET.get("account")
        order_by = self.request.GET.get("order_by")
        channel = self.request.GET.get("channel")
        date__lte = self.request.GET.get("date__lte")
        date__gte = self.request.GET.get("date__gte")
        time__gte = self.request.GET.get("time__gte")
        time__lte = self.request.GET.get("time__lte")
        date = self.request.GET.get("date")
        def parse_date(date_str):
            try:
                return datetime.strptime(date_str, '%d/%m/%Y').strftime('%Y-%m-%d')
            except (ValueError, TypeError):
                return None
        date__lte = parse_date(date__lte)
        date__gte = parse_date(date__gte)
        if date:
            if date == 'today':
                queryset = queryset.filter(created__date=today)
            elif date == 'yesterday':
                queryset = queryset.filter(created__date=yesterday)
            elif date == 'this_week':
                queryset = queryset.filter(created__date__range=[week_start, week_end])
            elif date == 'this_month':
                queryset = queryset.filter(created__month=month)
            elif date == 'this_year':
                queryset = queryset.filter(created__year=year)

            
            if date == 'custom':
                date_gte = self.request.GET.get('date__gte')
                date_lte = self.request.GET.get('date__lte')
                time_gte = self.request.GET.get('time__gte')
                time_lte = self.request.GET.get('time__lte')

                if date_gte and date_lte and time_gte and time_lte:
                    # Convert strings to datetime objects
                    date_gte = parse_date(date_gte)
                    date_lte = parse_date(date_lte)
                    start_datetime = datetime.strptime(f"{date_gte} {time_gte}",  "%Y-%m-%d %H:%M")
                    end_datetime = datetime.strptime(f"{date_lte} {time_lte}",  "%Y-%m-%d %H:%M")

                    # Apply filter
                    queryset = queryset.filter(created__range=[start_datetime, end_datetime]).order_by('created')


        if account:
            return queryset.filter(account=account)
        if order_by:
            return queryset.filter(order_by=order_by)
        if channel:
            return queryset.filter(channel=channel)
        if type:
            return queryset.filter(channel__channel_type=type)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        type = self.request.GET.get("type")
        date = self.request.GET.get("date")
        date__lte = self.request.GET.get("date__lte")
        date__gte = self.request.GET.get("date__gte")
        time__gte = self.request.GET.get("time__gte")
        time__lte = self.request.GET.get("time__lte")
        form = DateFilter(initial={
            'date': date,
            'date__lte': date__lte,
            'date__gte': date__gte,
            'time__gte': time__gte,
            'time__lte': time__lte,
        })
        account = self.request.GET.get("account")
        order_by = self.request.GET.get("order_by")
        channel = self.request.GET.get("channel")
        qs = super().get_queryset()
        if type == "WhatsApp":
            context["is_whatsapp"] = True
        if type == "WhatsApp_COD":
            context["is_cod"] = True
        elif type == "Swiggy":
            context["is_swiggy"] = True
        elif type == "Kumar":
            context["is_kumar"] = True
        elif type == "Wholesale":
            context["is_wholesale"] = True
        elif type == "Promo":
            context["is_promo"] = True
        elif type == "Counter":
            context["is_counter"] = True
        elif type == "Return":
            context["is_return"] = True
        
        if type :
            context['can_add'] = True
            context['new_link'] = reverse_lazy("master:order_create")
            context['type'] = type
            context["is_order"] = True
        else:
            context["is_orders"] = True
        WhatsApp = qs.filter(channel__channel_type="WhatsApp")
        cod = qs.filter(channel__channel_type="WhatsApp_COD")
        swigy = qs.filter(channel__channel_type="Swiggy")
        kumar = qs.filter(channel__channel_type="Kumar")
        wholesale = qs.filter(channel__channel_type="Wholesale")
        promo = qs.filter(channel__channel_type="Promo")
        counter = qs.filter(channel__channel_type="Counter")
        replacement = qs.filter(channel__channel_type="Return_or_Replace")
        context["whatsapp_count"] = WhatsApp.count()
        context['whatsapp_count_today'] = WhatsApp.filter(created__date=today).count()
        context["whatsapp_cod_count"] = cod.count()
        context["whatsapp_cod_count_today"] = cod.filter(created__date=today).count()
        context["swiggy_count"] = swigy.count()
        context["swiggy_count_today"] = swigy.filter(created__date=today).count()
        context["kumar_count"] = kumar.count()
        context["kumar_count_today"] = kumar.filter(created__date=today).count()
        context["wholesale_count"] = wholesale.count()
        context["wholesale_count_today"] = wholesale.filter(created__date=today).count()
        context["promo_count"] = promo.count()
        context["promo_count_today"] = promo.filter(created__date=today).count()
        context["counter_count"] = counter.count()
        context["counter_count_today"] = counter.filter(created__date=today).count()
        context["return_or_replace_count"] = replacement.count()
        context["return_or_replace_count_today"] = replacement.filter(created__date=today).count()
        context["form"] = form
        context["date"] = date
        context["date__lte"] = date__lte
        context["date__gte"] = date__gte
        context["time__lte"] = time__lte
        context["time__gte"] = time__gte
        context["account"] = account
        context["order_by"] = order_by
        context["channel"] = channel
        context["title"] = " Orders"
        
        
        return context


class OrderDetailView(mixins.HybridDetailView):
    model = Order
    template_name = "order/order_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_order'] = True
        context['type'] = self.request.GET.get("type")
        return context


class OrderCreateView(mixins.HybridCreateView):
    model = Order
    form_class = CustomerForm
    template_name = "order/order_form.html"

    def get_initial(self):
        self.initial['order_by'] = self.request.user
        self.initial['cod_charge'] = 0
        return super().get_initial()


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        type = self.request.GET.get("type")
        
        qs = Order.objects.filter(is_active=True).order_by("-created")
        
        type_map = {
            "WhatsApp": "is_whatsapp",
            "Swiggy": "is_swiggy",
            "Kumar": "is_kumar",
            "Wholesale": "is_wholesale",
            "WhatsApp_COD": "is_cod",
            "Promo": "is_promo",
            "Counter": "is_counter",
            "Return_or_Replace": "is_return"
        }
        context.update({type_map.get(type, "is_promo"): True})
        context['is_order'] = True
        context['type'] =type
        context["title"] =f"New {type} Order"
       # Initialize formset
        prefix = "order_item_formset"
        context["order_item_formset"] = (
            OrderItemFormSet(self.request.POST, prefix=prefix)
            if self.request.POST else
            OrderItemFormSet(prefix=prefix)
        )
        # Channel-specific counts
        WhatsApp = qs.filter(channel__channel_type="WhatsApp")
        cod = qs.filter(channel__channel_type="WhatsApp_COD")
        swigy = qs.filter(channel__channel_type="Swiggy")
        kumar = qs.filter(channel__channel_type="Kumar")
        wholesale = qs.filter(channel__channel_type="Wholesale")
        promo = qs.filter(channel__channel_type="Promo")
        counter = qs.filter(channel__channel_type="Counter")
        replacement = qs.filter(channel__channel_type="Return_or_Replace")
        context["whatsapp_count"] = WhatsApp.count()
        context['whatsapp_count_today'] = WhatsApp.filter(created__date=today).count()
        context["whatsapp_cod_count"] = cod.count()
        context["whatsapp_cod_count_today"] = cod.filter(created__date=today).count()
        context["swiggy_count"] = swigy.count()
        context["swiggy_count_today"] = swigy.filter(created__date=today).count()
        context["kumar_count"] = kumar.count()
        context["kumar_count_today"] = kumar.filter(created__date=today).count()
        context["wholesale_count"] = wholesale.count()
        context["wholesale_count_today"] = wholesale.filter(created__date=today).count()
        context["promo_count"] = promo.count()
        context["promo_count_today"] = promo.filter(created__date=today).count()
        context["counter_count"] = counter.count()
        context["counter_count_today"] = counter.filter(created__date=today).count()
        context["return_or_replace_count"] = replacement.count()
        context["return_or_replace_count_today"] = replacement.filter(created__date=today).count()
        return context
      

    def form_valid(self, form):
        context = self.get_context_data()
        order_item_formset = context["order_item_formset"]

        if order_item_formset.is_valid():
            try:
                with transaction.atomic():

                    if Customer.objects.filter(phone_no=self.request.POST.get("phone_no")).exists():
                        customer = Customer.objects.filter(phone_no=self.request.POST.get("phone_no")).last()
                        customer.name_2 = self.request.POST.get("name_2")
                        customer.pincode_2 = self.request.POST.get("pincode_2")
                        customer.address_2 = self.request.POST.get("address_2")
                        customer.city_2 = self.request.POST.get("city_2")
                        customer.state_2 = self.request.POST.get("state_2")
                        customer.country_2 = self.request.POST.get("country_2")
                        customer.creator = self.request.user
                        customer.save()
                    else:
                        customer = Customer.objects.create(
                            phone_no=self.request.POST.get("phone_no"),
                            customer_name=self.request.POST.get("customer_name"),
                            pincode=self.request.POST.get("pincode"),
                            address=self.request.POST.get("address"),
                            city=self.request.POST.get("city"),
                            state=self.request.POST.get("state"),
                            country=self.request.POST.get("country"),
                            alternate_phone_no=self.request.POST.get("alternate_phone_no"),
                            name_2=self.request.POST.get("name_2"),
                            pincode_2=self.request.POST.get("pincode_2"),
                            address_2=self.request.POST.get("address_2"),
                            city_2=self.request.POST.get("city_2"),
                            state_2=self.request.POST.get("state_2"),
                            country_2=self.request.POST.get("country_2"),
                        )
                    print(customer) 
                    # Fetch the channel
                    channel_type = self.request.GET.get("type")
                    channel = Channel.objects.get(channel_type=channel_type)
                    # Create the order
                    order = form.save(commit=False)
                    order.channel = channel
                    order.customer = customer
                    order.save()
                    # Save the order items
                    order_item_formset.instance = order
                    order_item_formset.save()
                return super().form_valid(form)
            except Exception as e:
                form.add_error(None, f"An error occurred: {e}")
                return self.form_invalid(form)

        # If formset is invalid, re-render the response with errors
        return self.render_to_response(self.get_context_data(form=form))

    def form_invalid(self, form):
        context = self.get_context_data(form=form)
        return self.render_to_response(context)
    
    def get_success_url(self):
        type = self.request.GET.get("type")
        url = reverse_lazy("master:order_create")
        if type:
            return f"{url}?type={type}"
        return url

class OrderUpdateView(mixins.HybridUpdateView):
    model = Order
    form_class = CustomerForm
    template_name = "order/order_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Update {self.object} Order"
        if self.request.POST:
            context["order_item_formset"] = OrderItemFormSet(self.request.POST, instance=self.object, prefix="Ordersubjects")
        else:
            context["order_item_formset"] = OrderItemFormSet(instance=self.object, prefix="Ordersubjects")
        context['is_order'] = True
        context['type'] = self.request.GET.get("type")
        context['is_update'] = True
        return context
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        customer = self.object.customer
        form.fields['phone_no'].initial = customer.phone_no
        form.fields['customer_name'].initial = customer.customer_name
        form.fields['pincode'].initial = customer.pincode
        form.fields['address'].initial = customer.address
        form.fields['city'].initial = customer.city
        form.fields['state'].initial = customer.state
        form.fields['country'].initial = customer.country
        form.fields['pincode_2'].initial = customer.pincode_2
        form.fields['address_2'].initial = customer.address_2
        form.fields['city_2'].initial = customer.city_2
        form.fields['state_2'].initial = customer.state_2
        form.fields['country_2'].initial = customer.country_2
        form.fields['alternate_phone_no'].initial = customer.alternate_phone_no

        return form

    def form_valid(self, form):
        order_item_formset = OrderItemFormSet(self.request.POST, instance=self.object, prefix="Ordersubjects")

        if order_item_formset.is_valid():
            customer = self.object.customer
            for field, value in form.cleaned_data.items():
                setattr(customer, field, value)
            customer.save()
            customer.save()
            self.object = form.save()
            order_item_formset.instance = self.object
            order_item_formset.save()
            return super().form_valid(form)

        return self.render_to_response(self.get_context_data(form=form, order_item_formset=order_item_formset))


    def get_success_url(self):
        url = reverse_lazy("master:order_list")
        type_param = self.object.channel.channel_type
        return f"{url}?type={type_param}" if type_param else url

    
class OrderDeleteView(mixins.HybridDeleteView):
    model = Order

    def get_success_url(self):
        type = self.request.GET.get("type")
        url = reverse_lazy("master:order_list")
        if type:
            return f"{url}?type={type}"
        return url


# =============================================
# QUICK ORDER ENTRY
# =============================================

@method_decorator(login_required, name='dispatch')
class QuickOrderEntryView(View):
    """Fast order entry page with channel cards and keyboard-optimized workflow."""
    template_name = 'order/quick_entry.html'
    
    def get_business_day_range(self):
        """Get the current business day range (IST 8PM - 8PM)."""
        from datetime import timezone as tz
        import pytz
        
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)
        
        # Business day cutoff is 8 PM IST
        cutoff_hour = 20
        
        if now.hour >= cutoff_hour:
            # After 8 PM - business day is tomorrow
            business_date = now.date() + timedelta(days=1)
            start = now.replace(hour=cutoff_hour, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
        else:
            # Before 8 PM - business day is today
            business_date = now.date()
            start = (now - timedelta(days=1)).replace(hour=cutoff_hour, minute=0, second=0, microsecond=0)
            end = now.replace(hour=cutoff_hour, minute=0, second=0, microsecond=0)
        
        return business_date, start, end
    
    def get(self, request):
        channels = Channel.objects.filter(is_active=True).order_by('id')
        accounts = Account.objects.filter(is_active=True)
        users = User.objects.filter(is_active=True)
        products = Product.objects.filter(is_active=True)
        
        # Get today's stats for each channel
        business_date, start, end = self.get_business_day_range()
        
        channel_data = []
        for channel in channels:
            orders = Order.objects.filter(
                channel=channel,
                is_active=True,
                created__date=today
            )
            channel_data.append({
                'id': channel.id,
                'channel_type': channel.channel_type,
                'prefix': channel.prefix,
                'today_count': orders.count(),
                'today_amount': orders.aggregate(total=Sum('total_amount'))['total'] or 0
            })
        
        # Products JSON for frontend search
        products_json = json.dumps([{
            'id': p.id,
            'name': str(p),
            'code': p.product_code or '',
            'price': float(p.price),
            'size': p.size
        } for p in products])
        
        # Get carriers if logistics app exists
        carriers = []
        try:
            from logistics.models import Carrier
            carriers = Carrier.objects.filter(is_active=True)
        except:
            pass
        
        active_channel = channels.first() if channels.exists() else None
        
        context = {
            'channels': channel_data,
            'accounts': accounts,
            'users': users,
            'carriers': carriers,
            'products_json': products_json,
            'active_channel': active_channel,
            'business_date': business_date,
        }
        
        return render(request, self.template_name, context)


@login_required
@require_http_methods(["POST"])
def quick_order_save(request):
    """Save order from quick entry form."""
    try:
        with transaction.atomic():
            # Parse form data
            channel_id = request.POST.get('channel_id')
            phone_no = request.POST.get('phone_no')
            customer_name = request.POST.get('customer_name')
            alternate_phone_no = request.POST.get('alternate_phone_no', '')
            pincode = request.POST.get('pincode')
            city = request.POST.get('city')
            state = request.POST.get('state')
            address = request.POST.get('address')
            country = request.POST.get('country', 'India')
            account_id = request.POST.get('account')
            order_by_id = request.POST.get('order_by')
            utr = request.POST.get('utr', '').strip()
            cod_charge = Decimal(request.POST.get('cod_charge', '0') or '0')
            items_json = request.POST.get('items_json', '[]')
            
            # Validate channel
            channel = get_object_or_404(Channel, id=channel_id)
            
            # Validate UTR uniqueness for WhatsApp channel
            if channel.channel_type == 'WhatsApp' and utr:
                if Order.objects.filter(utr=utr, is_active=True).exists():
                    return JsonResponse({'success': False, 'error': 'UTR already exists'})
            
            # Get or create customer
            customer, created = Customer.objects.get_or_create(
                phone_no=phone_no,
                defaults={
                    'customer_name': customer_name,
                    'alternate_phone_no': alternate_phone_no,
                    'pincode': pincode,
                    'city': city,
                    'state': state,
                    'address': address,
                    'country': country,
                    'creator': request.user,
                }
            )
            
            if not created:
                # Update secondary address fields
                customer.name_2 = customer_name
                customer.pincode_2 = pincode
                customer.city_2 = city
                customer.state_2 = state
                customer.address_2 = address
                customer.country_2 = country
                customer.save()
            
            # Parse items
            items = json.loads(items_json)
            if not items:
                return JsonResponse({'success': False, 'error': 'At least one item is required'})
            
            # Calculate total
            total_amount = Decimal('0')
            for item in items:
                total_amount += Decimal(item['price']) * int(item['qty'])
            total_amount += cod_charge
            
            # Create order
            order = Order.objects.create(
                channel=channel,
                customer=customer,
                account_id=account_id,
                order_by_id=order_by_id,
                utr=utr or None,
                cod_charge=cod_charge,
                total_amount=total_amount,
                creator=request.user,
            )
            
            # Create order items
            for item in items:
                product = get_object_or_404(Product, id=item['product_id'])
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    price=Decimal(item['price']),
                    quantity=int(item['qty']),
                    amount=Decimal(item['price']) * int(item['qty']),
                    creator=request.user,
                )
            
            return JsonResponse({
                'success': True,
                'order_id': order.id,
                'order_no': order.order_no,
            })
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def check_utr(request):
    """Check if UTR already exists."""
    utr = request.GET.get('utr', '').strip()
    if not utr:
        return JsonResponse({'exists': False})
    
    exists = Order.objects.filter(utr=utr, is_active=True).exists()
    return JsonResponse({'exists': exists})


@login_required
def search_products(request):
    """Search products for autocomplete."""
    query = request.GET.get('q', '').strip()
    channel_type = request.GET.get('channel', '')
    
    products = Product.objects.filter(is_active=True)
    
    if query:
        products = products.filter(
            models.Q(product_name__icontains=query) |
            models.Q(product_code__icontains=query)
        )[:10]
    
    results = []
    for p in products:
        price = p.price
        if channel_type:
            price = p.get_price(channel_type)
        
        results.append({
            'id': p.id,
            'name': str(p),
            'code': p.product_code or '',
            'price': float(price),
            'size': p.size,
        })
    
    return JsonResponse({'products': results})


@login_required  
def lookup_pincode(request):
    """Lookup city/state from pincode using external API or local database."""
    pincode = request.GET.get('pincode', '').strip()
    
    if len(pincode) != 6:
        return JsonResponse({'success': False, 'error': 'Invalid pincode'})
    
    # Try local PincodeMaster first
    try:
        from marketing.models import PincodeMaster
        pm = PincodeMaster.objects.filter(pincode=pincode).first()
        if pm:
            return JsonResponse({
                'success': True,
                'city': pm.district,
                'state': pm.state,
            })
    except:
        pass
    
    # Fallback - let frontend handle external API call
    return JsonResponse({'success': False, 'error': 'Not found locally'})
