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
    opning_stock = models.DecimalField('stock', max_digits=10, decimal_places=0, default=0)
    image = models.ImageField(upload_to="product", null=True, blank=True)
    order = models.PositiveIntegerField(default=10)
    is_hide = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.product_name.upper()}-{self.size.upper()}'
    
    def get_stock(self):
        """Calculate current stock from opening + purchases - sales."""
        opening = self.opning_stock or 0

        purchase_data = PurchaseItem.objects.filter(item=self).aggregate(total_purchased=Sum('quantity'))
        total_purchased = purchase_data['total_purchased'] or 0

        sale_data = OrderItem.objects.filter(product=self).aggregate(total_sold=Sum('quantity'))
        total_sold = sale_data['total_sold'] or 0

        stock = opening + total_purchased - total_sold
        return stock
    
    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ["order", 'id']

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
        return OrderItem.objects.filter(product=self).select_related('order')

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
            if Order.objects.filter(is_active=True).exists():
                max_order_number = Order.objects.first().order_no
                current_number = int(max_order_number.split("-EB")[1])
                order_no = f"{self.channel.prefix}-EB{str(current_number + 1).zfill(4)}"
            else:
                order_no = f"{self.channel.prefix}-EB{str(1).zfill(4)}"
            self.order_no = order_no
        super().save(*args, **kwargs)
    
    def get_stage_badge(self):
        stage_badge_colors = {
            "Confirm": "badge-primary",
            "Booked": "badge-secondary",
            "Delivered": "badge-success",
            "Cancelled": "badge-dark",
            "Pending": "badge-danger",
        }
        return stage_badge_colors.get(self.stage, "")
    
    def get_products_desc(self):
        """Example output: '2x T-Shirt (Rs500), 1x Jeans (Rs1200)'"""
        return ", ".join(
            f"{item.quantity}x {item.product.product_name} (Rs{item.product.price})"
            for item in self.get_items()
        )
    
    @property
    def capitalized_city(self):
        if self.city:
            return f"{self.city.upper()}"
        return ""

    @property
    def capitalized_state(self):
        if self.state:
            return f"{self.state.upper()}"
        return ""
    
    @property
    def capitalized_country(self):
        if self.country:
            return f"{self.country.upper()}"
        return ""

    def get_track_url(self):
        if self.tracking_id and self.courier_partner:
            if self.courier_partner.tracking_slug:
                base = 'https://trackcourier.io/track-and-trace/'
                courier = self.courier_partner.tracking_slug
                tracking_id = self.tracking_id
                return f"{base}{courier}/{tracking_id}"
        return None


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


class OrderTrackingHistory(models.Model):
    """Track status changes for orders."""
    order = models.ForeignKey('master.Order', on_delete=models.CASCADE)
    status = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.order.order_no} - {self.status} at {self.timestamp}"


# =============================================================================
# VENDOR & PURCHASE MODELS (from original ZIP)
# =============================================================================
class Vendor(BaseModel):
    """Vendor/supplier for purchase orders."""
    name = models.CharField("Name of Vendor", max_length=255)
    address = models.TextField()
    contact_details = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name}"
    
    class Meta:
        verbose_name = "Vendor"
        verbose_name_plural = "Vendors"

    def get_absolute_url(self):
        return reverse_lazy("master:vendor_detail", kwargs={"pk": self.pk})
    
    @staticmethod
    def get_list_url():
        return reverse_lazy("master:vendor_list")

    def get_update_url(self):
        return reverse_lazy("master:vendor_update", kwargs={"pk": self.pk})

    def get_delete_url(self):
        return reverse_lazy("master:vendor_delete", kwargs={"pk": self.pk})


class Purchase(BaseModel):
    """Purchase order from vendors."""
    invoice_number = models.CharField(max_length=50, unique=True)
    invoice_date = models.DateField()
    vendor = models.ForeignKey('master.Vendor', on_delete=models.SET_NULL, null=True)
    payment_due_date = models.DateField(blank=True, null=True)
    grand_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"BILL - {self.invoice_number}"
    
    class Meta:
        verbose_name = "Purchase"
        verbose_name_plural = "Purchases"
    
    @staticmethod
    def get_list_url():
        return reverse_lazy("master:purchase_list")

    def get_absolute_url(self):
        return reverse_lazy("master:purchase_detail", kwargs={"pk": self.pk})

    def get_update_url(self):
        return reverse_lazy("master:purchase_update", kwargs={"pk": self.pk})

    def get_delete_url(self):
        return reverse_lazy("master:purchase_delete", kwargs={"pk": self.pk})
    
    def get_items(self):
        return PurchaseItem.objects.filter(is_active=True, purchase=self)


class PurchaseItem(BaseModel):
    """Line items in a purchase order."""
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE)
    item = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    class Meta:
        verbose_name = "Purchase Item"
        verbose_name_plural = "Purchase Items"


class PostOrder(BaseModel):
    """Barcode tracking for shipped orders."""
    barcode = models.CharField(max_length=50, unique=True, blank=True, null=True)
    order = models.ForeignKey('master.Order', on_delete=models.CASCADE)
    is_complete = models.BooleanField(default=False)

    def __str__(self):
        return f"POST ORDER - {self.barcode}"
    
    class Meta:
        verbose_name = "Post Order"
        verbose_name_plural = "Post Orders"


# =============================================================================
# PINCODE RULE (Legacy - for backward compatibility)
# =============================================================================
class PincodeRuleLegacy(BaseModel):
    """Legacy pincode to courier mapping (see logistics.PincodeRule for new version)."""
    courier = models.ForeignKey(CourierPartner, on_delete=models.CASCADE)
    pincode = models.CharField(max_length=6)
    cscrcd = models.CharField(max_length=5, blank=True, null=True)
    priority = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "Pincode Rule (Legacy)"
        verbose_name_plural = "Pincode Rules (Legacy)"
        unique_together = ('courier', 'pincode')

    def __str__(self):
        return f"{self.pincode} -> {self.courier.name}"
