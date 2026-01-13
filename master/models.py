import datetime
from decimal import Decimal
from django.db import models
from django.db.models import Sum
from django.urls import reverse_lazy
from core.base import BaseModel
from accounts.models import User
from core.choices import MONTH_CHOICES, YEAR_CHOICES

# Create your models here.

today = datetime.date.today()


# =============================================================================
# COURIER PARTNER MODEL (from original ZIP)
# =============================================================================
class CourierPartner(BaseModel):
    """Legacy courier partner model - for backward compatibility."""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=50, unique=True)
    tracking_slug = models.CharField(max_length=50, unique=True, null=True, blank=True)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Courier Partner"
        verbose_name_plural = "Courier Partners"
    
    @staticmethod
    def get_list_url():
        return reverse_lazy("master:courierpartner_list")
    
    def get_absolute_url(self):
        return reverse_lazy("master:courierpartner_detail", kwargs={"pk": self.pk})

    def get_update_url(self):
        return reverse_lazy("master:courierpartner_update", kwargs={"pk": self.pk})

    def get_delete_url(self):
        return reverse_lazy("master:courierpartner_delete", kwargs={"pk": self.pk})
class Account(BaseModel):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=100, unique=True)
    opening_balance = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.name
    
    @staticmethod
    def get_list_url():
        return reverse_lazy("master:account_list")

    def get_absolute_url(self):
        return reverse_lazy("master:account_detail", kwargs={"pk": self.pk})

    def get_update_url(self):
        return reverse_lazy("master:account_update", kwargs={"pk": self.pk})

    def get_delete_url(self):
        return reverse_lazy("master:account_delete", kwargs={"pk": self.pk})
    
    def get_total_incomes(self):
        data = Order.objects.filter(account=self).aggregate(total=models.Sum('total_amount'))['total'] or 0
        return Decimal(data)
    
    def get_orders(self):
        return Order.objects.filter(account=self,is_active=True)
    
    def get_balance(self):
        return Decimal(self.opening_balance + self.get_total_incomes())
    
    def get_today_orders(self):
        data = (Order.objects.filter(account=self,is_active=True,created__date=today).aggregate(total=models.Sum('total_amount'))['total'] or 0)
        return Decimal(data)
    
    def get_opening(self):
        return self.get_balance()-self.get_today_orders()


class Channel(BaseModel):
    channel_type = models.CharField(max_length=100,choices=[("WhatsApp","WhatsApp"),("WhatsApp_COD","WhatsApp COD"),("Swiggy","Swiggy"),("Kumar","Kumar"),("Wholesale","Wholesale"),("Promo","Promo"),("Return_or_Replace","RETURN/REPLACE"),("Counter","Counter")],default="WhatsApp")
    prefix = models.CharField(max_length=100,unique = True)

    def __str__(self):
        return self.channel_type
    
    class Meta:
        verbose_name = "Channel"
        verbose_name_plural = "Channels"
        unique_together = ("channel_type", "prefix")
    
    @staticmethod
    def get_list_url():
        return reverse_lazy("master:channel_list")

    def get_absolute_url(self):
        return reverse_lazy("master:channel_detail", kwargs={"pk": self.pk})

    def get_update_url(self):
        return reverse_lazy("master:channel_update", kwargs={"pk": self.pk})

    def get_delete_url(self):
        return reverse_lazy("master:channel_delete", kwargs={"pk": self.pk})
    
    def get_orders(self):
        return Order.objects.filter(channel=self)
    
class Product(BaseModel):
    product_name = models.CharField(max_length=100)
    product_code = models.CharField(max_length=100, unique=True, null=True, blank=True)
    size = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to="product", null=True, blank=True)

    def __str__(self):
        return f'{self.product_name.upper()}-{self.size.upper()}'
    
    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"

    @staticmethod
    def get_list_url():
        return reverse_lazy("master:product_list")
    
    def get_absolute_url(self):
        return reverse_lazy("master:product_detail", kwargs={"pk": self.pk})

    def get_update_url(self):
        return reverse_lazy("master:product_update", kwargs={"pk": self.pk})

    def get_delete_url(self):
        return reverse_lazy("master:product_delete", kwargs={"pk": self.pk})
    
    def get_price(self,channel):
        try:
            return ProductPrice.objects.get(product=self,channel__channel_type=channel).price
        except ProductPrice.DoesNotExist:
            return self.price
        
    def get_orders(self):
        return OrderItem.objects.filter(product=self)

class ProductPrice(BaseModel):
    product = models.ForeignKey(Product,on_delete=models.CASCADE)
    channel = models.ForeignKey(Channel,on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)


    def __str__(self):
        return f"{self.channel.prefix}-{self.product} - {self.price}"
    
    @staticmethod
    def get_list_url():
        return reverse_lazy("master:productprice_list")

    def get_absolute_url(self):
        return reverse_lazy("master:productprice_detail", kwargs={"pk": self.pk})

    def get_update_url(self):
        return reverse_lazy("master:productprice_update", kwargs={"pk": self.pk})

    def get_delete_url(self):
        return reverse_lazy("master:productprice_delete", kwargs={"pk": self.pk})



class Customer(BaseModel):
    phone_no = models.CharField(max_length=20)
    customer_name = models.CharField(max_length=100)
    pincode = models.CharField(max_length=6)
    address = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    alternate_phone_no = models.CharField(max_length=20,null=True,blank=True)
    name_2 = models.CharField("Name",max_length=100,null=True,blank=True)
    pincode_2 = models.CharField('Pincode',max_length=6,null=True,blank=True)
    address_2 = models.CharField('Address ',max_length=200,null=True,blank=True)
    city_2 = models.CharField('City',max_length=100,null=True,blank=True)
    state_2 = models.CharField('State',max_length=100,null=True,blank=True)
    country_2 = models.CharField('Country',max_length=100,null=True,blank=True)
    # name_3 = models.CharField("Name",max_length=100,null=True,blank=True)
    # pincode_3 = models.CharField('Pincode',max_length=6,null=True,blank=True)
    # address_3 = models.CharField('Address ',max_length=200,null=True,blank=True)
    # city_3 = models.CharField('City',max_length=100,null=True,blank=True)
    # state_3 = models.CharField('State',max_length=100,null=True,blank=True)
    # country_3 = models.CharField('Country',max_length=100,null=True,blank=True)
    
    def __str__(self):
        return self.customer_name.upper()
    
    class Meta:
        verbose_name = "Customer"
        verbose_name_plural = "Customers"

    @property
    def capitalized_city(self):
        if self.city_2 :
           return f"{self.city_2.upper()}"
        else:
            if self.city:
               return f"{self.city.upper()}"
        return ""
        

    @property
    def capitalized_state(self):
        if self.state_2 :
           return f"{self.state_2.upper()}"
        else:
            if self.state:
               return f"{self.state.upper()}"
        return ""
    
    @property
    def capitalized_country(self):
        if self.country_2 :
           return f"{self.country_2.upper()}"
        else:
            if self.country:
               return f"{self.country.upper()}"
        return ""
    
    
    @staticmethod
    def get_list_url():
        return reverse_lazy("master:customer_list")

    def get_absolute_url(self):
        return reverse_lazy("master:customer_detail", kwargs={"pk": self.pk})

    def get_update_url(self):
        return reverse_lazy("master:customer_update", kwargs={"pk": self.pk})

    def get_delete_url(self):
        return reverse_lazy("master:customer_delete", kwargs={"pk": self.pk})
    
    def get_address(self):
       if self.address_2 :
           return f"{self.address_2.upper()}"
       else:
           if self.address:
               return f"{self.address.upper()}"
           return ""
    def get_address_name(self):
        if self.name_2:
            return f"{self.name_2.upper()}"
        else:
            return f"{self.customer_name.upper()}"

    def get_address_pincode(self):
        if self.pincode_2:
            return f"{self.pincode_2}"
        else:
            return f"{self.pincode}"


    def get_orders(self):
        return Order.objects.filter(customer=self)


# =============================================================================
# ORDER STATUS CHOICES
# =============================================================================
ORDER_STATUS = (
    ("Pending", "Pending"),
    ("Booked", "Booked"),
    ("Packed", "Packed"),
    ("Shipped", "Shipped"),
    ("In_transit", "IN TRANSIT"),
    ("Delivered", "Delivered"),
    ("Cancelled", "Cancelled"),
    ("Returned", "Returned"),
)


class Order(BaseModel):
    channel = models.ForeignKey(Channel,on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    utr = models.CharField(max_length=20, null=True, blank=True)
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    cod_charge = models.DecimalField(max_digits=10, decimal_places=2,default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    order_no = models.CharField(max_length=20, null=True, blank=True,unique=True)
    order_by = models.ForeignKey(User, on_delete=models.CASCADE,related_name="order_by")
    
    # Stage and shipping fields (from original ZIP)
    stage = models.CharField(max_length=100, default="Pending", choices=ORDER_STATUS)
    name = models.CharField(max_length=100, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    mobile = models.CharField(max_length=20, null=True, blank=True)
    pincode = models.CharField(max_length=6, null=True, blank=True)
    address = models.CharField(max_length=250, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    
    # Courier/tracking fields
    courier_partner = models.ForeignKey(CourierPartner, null=True, blank=True, on_delete=models.SET_NULL)
    tracking_id = models.CharField(max_length=100, null=True, blank=True)
    last_tracking_status = models.CharField(max_length=100, null=True, blank=True)
    tracking_last_checked = models.DateTimeField(null=True, blank=True)
    destination_code = models.CharField(max_length=100, null=True, blank=True)
    
    # Date tracking
    booked_date = models.DateTimeField(null=True, blank=True)
    cancelled_date = models.DateTimeField(null=True, blank=True)
    packed_date = models.DateTimeField(null=True, blank=True)
    shipped_date = models.DateTimeField(null=True, blank=True)
    delivered_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        if self.utr:
            return f'{self.customer.customer_name}-{self.utr}'
        return self.customer.customer_name


    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ["-created"]


    @staticmethod
    def get_list_url():
        return reverse_lazy("master:order_list")

    def get_absolute_url(self):
        return reverse_lazy("master:order_detail", kwargs={"pk": self.pk})

    def get_update_url(self):
        return reverse_lazy("master:order_update", kwargs={"pk": self.pk})
    
    def get_courier_update_url(self):
        return reverse_lazy("master:order_courier_update", kwargs={"pk": self.pk})

    def get_delete_url(self):
        return reverse_lazy("master:order_delete", kwargs={"pk": self.pk})
    
    def get_items(self):
        return self.orderitem_set.all()
    
    def alternate_phone_no(self):
        if self.mobile:
            return self.mobile
        else:
            return self.customer.alternate_phone_no or ''
    
    def get_total_amount(self):
        return sum([item.amount for item in self.orderitem_set.all()])
    
    def get_total_actual_amount(self):
        total = 0
        for item in self.orderitem_set.select_related("product"):
            try:
                total += item.product.price * item.quantity
            except Exception:
                total += 0
        return total
    
    def get_shipping_amount(self):
        return sum([item.product.price * item.quantity for item in self.orderitem_set.all()])
    
    def get_shipping_cod_amount(self):
        return self.get_shipping_amount() + self.cod_charge
    
    def save(self, *args, **kwargs):
        if not self.order_no :
            print('not created')
            if Order.objects.filter(is_active=True).exists():
                max_order_number = Order.objects.first().order_no
                print(max_order_number)
                current_number = int(max_order_number.split("-EB")[1])
                print(current_number)
                order_no = f"{self.channel.prefix}-EB{str(current_number + 1).zfill(4)}"
            else:
                order_no = f"{self.channel.prefix}-EB{str(1).zfill(4)}"
            print(order_no)
            self.order_no = order_no
        super().save(*args, **kwargs)
    

class OrderItem(BaseModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.product.product_name

    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"


