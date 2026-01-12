from datetime import datetime, timedelta
from django.db.models import Sum,Count
from accounts.models import User
from master.models import Customer, Order, OrderItem, Product

from core import mixins
from master import tables
class HomeView(mixins.HybridListView):
    model = Order
    table_class = tables.OrderTable
    template_name = "core/home.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()
       
        today = datetime.now().date()
        date_range = [today - timedelta(days=i) for i in range(12)]
        today_sale_qs = qs.filter(created__date=today)
        yesterday_sale_qs = qs.filter(created__date=date_range[1])
        
        channels = ['WhatsApp', 'WhatsApp_COD', 'Swiggy', 'Kumar', 'Wholesale', 'Promo', 'Counter', 'Return_or_Replace']
        
        # Orders and revenue by channel
        order_counts = {channel: [] for channel in channels}
        revenue_by_channel = []
        today_order_by_channels = []
        
        for channel in channels:
            today_qs = today_sale_qs.filter(channel__channel_type=channel)
            revenue_by_channel.append(int(today_qs.aggregate(Sum("total_amount"))["total_amount__sum"] or 0))
            today_order_by_channels.append(today_qs.count())
        
        # Orders by channel for the last 7 days
        for date in date_range[::-1]:
            daily_qs = qs.filter(created__date=date)
            for channel in channels:
                order_counts[channel].append(daily_qs.filter(channel__channel_type=channel).count())
        
        context.update({f"{channel}_data": data for channel, data in order_counts.items()})
        
        # Total sales calculations
        total_sale = today_sale_qs.exclude(account=15).aggregate(Sum("total_amount"))["total_amount__sum"] or 0
        cod_charges = today_sale_qs.aggregate(Sum("cod_charge"))["cod_charge__sum"] or 0
        context["total_sale"] = total_sale + cod_charges
        
        context.update({
            "customers": today_sale_qs.values("customer").distinct().count(),
            "orders": today_sale_qs.count(),
            "revenue_by_channel": revenue_by_channel,
            "order_by_channels": today_order_by_channels,
            "is_dashboard": True
        })
        
        # Orders per time slot
        time_slots = [(1, 8)] + [(h, h+1) for h in range(8, 23)]
        context["yesterday_order_counts"], context["today_order_counts"] = [], []
        
        for start_hour, end_hour in time_slots:
            yesterday_start = datetime.combine(date_range[1], datetime.min.time()).replace(hour=start_hour)
            yesterday_end = datetime.combine(date_range[1], datetime.min.time()).replace(hour=end_hour)
            today_start = datetime.combine(today, datetime.min.time()).replace(hour=start_hour)
            today_end = datetime.combine(today, datetime.min.time()).replace(hour=end_hour)
            
            context["yesterday_order_counts"].append(yesterday_sale_qs.filter(created__gte=yesterday_start, created__lt=yesterday_end).count())
            context["today_order_counts"].append(today_sale_qs.filter(created__gte=today_start, created__lt=today_end).count())
        
        # Total order counts by channel
        for channel in channels:
            channel_qs = qs.filter(channel__channel_type=channel)
            context[f"{channel.lower()}_count"] = channel_qs.count()
            context[f"{channel.lower()}_count_today"] = channel_qs.filter(created__date=today).count()
        
        return context

class ReportView(mixins.HybridListView):
    model = Order
    template_name = "core/report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()
        channels = ['WhatsApp', 'WhatsApp_COD', 'Swiggy', 'Kumar', 'Wholesale', 'Promo', 'Counter', 'Return_or_Replace']

        aggregated_data = qs.exclude(account=15).aggregate(
            total_sale=Sum("total_amount"), cod_charges=Sum("cod_charge")
        )
        
        context.update({
            "total_order": qs.count(),
            "total_customer": qs.values("customer").distinct().count(),
            "total_channel": qs.values("channel").distinct().count(),
            "total_account": qs.values("account").distinct().count(),
            "total_order_by": qs.values("order_by").distinct().count(),
            "total_sale": (aggregated_data["total_sale"] or 0) + (aggregated_data["cod_charges"] or 0),
        })
        
        top_cities = Customer.objects.values("city").annotate(count=Count("id")).order_by("-count")[:10]
        context['city_names'] = [top_city["city"] for top_city in top_cities]
        context['city_counts'] = [top_city["count"] for top_city in top_cities]
        
        products = Product.objects.filter(is_active=True)
        product_quantities = OrderItem.objects.filter(product__in=products).values("product").annotate(quantity=Sum("quantity"))
        
        product_data = {p["product"]: p["quantity"] for p in product_quantities}
        context.update({
            "products": products.count(),
            "products_list": [str(product) for product in products],
            "product_data": [product_data.get(product.id, 0) for product in products],
        })
        
        for channel in channels:
            channel_qs = qs.filter(channel__channel_type=channel)
            context[f"{channel.lower()}_count"] = channel_qs.count()
        context['is_report'] = True
        context['title'] = "Report"

        users = User.objects.filter(is_active=True)
        user_list = []
        user_count = []
        for user in users:
            user_list.append(user.username)
            user_count.append(qs.filter(order_by=user).count())
        context['user_list'] = user_list
        context['user_count'] = user_count
        return context
    
class ChannelReportView(mixins.HybridListView):
    model = Order
    template_name = "core/channel_report.html"

    def get_queryset(self):
        return Order.objects.filter(is_active=True, channel__channel_type=self.request.GET.get("type")).order_by("-created")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()
        context['title'] = f"{self.request.GET.get('type')} Report"
        return context