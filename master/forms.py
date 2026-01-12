from django import forms

from accounts.models import User
from .models import Account, Channel, Customer, Order, OrderItem


class CustomerForm(forms.ModelForm):
    
    phone_no = forms.CharField(max_length=100, required=True)
    customer_name = forms.CharField(max_length=100, required=True)
    pincode = forms.CharField(max_length=100, required=True)
    address = forms.CharField(max_length=100, required=True)
    city = forms.CharField(max_length=100, required=True)
    state = forms.CharField(max_length=100, required=True)
    country = forms.CharField(max_length=100, required=True)
    alternate_phone_no = forms.CharField(max_length=100, required=False)
    name_2 = forms.CharField(max_length=100, required=False)
    pincode_2 = forms.CharField(max_length=100, required=False)
    address_2 = forms.CharField(max_length=100, required=False)
    city_2 = forms.CharField(max_length=100, required=False)
    state_2 = forms.CharField(max_length=100, required=False)
    country_2 = forms.CharField(max_length=100, required=False)
    cod_charge = forms.DecimalField(max_digits=10, decimal_places=2, required=False)
    class Meta:
        model = Order
        exclude = ("channel", "customer",'order_no','is_active')

    def clean(self):
        cleaned_data = super().clean()
        utr = cleaned_data.get("utr")
        if not self.instance.pk and utr:
            if Order.objects.filter(utr=utr).exists():
                raise forms.ValidationError("UTR Already Exist.")
        return cleaned_data


class OrderItemForm(forms.ModelForm):
    image = forms.FileField(label='Image', required=False)
    class Meta:
        model = OrderItem
        exclude = ("creator", "is_active",'order')
        widgets = {
            "product": forms.Select(attrs={"class": "form-control item-select select"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control quantity-input"}),
            "price": forms.NumberInput(attrs={"class": "form-control unit-price-input"}),
            "amount": forms.NumberInput(attrs={"class": "form-control line_total-input", "readonly": "readonly"}),
        }

OrderItemFormSet = forms.inlineformset_factory(Order, OrderItem, form=OrderItemForm, extra=1, can_delete=True)


class DateFilter(forms.Form):
    DATE_choices = [
        ('', 'Select Date'),
        ('today', 'Today'),
        ('yesterday', 'Yesterday'),
        ('this_week', 'This Week'),
        ('this_month', 'This Month'),
        ('this_year', 'This Year'),
        ('custom', 'Custom'),
    ]
    date = forms.ChoiceField(
        choices=DATE_choices, 
        widget=forms.Select(attrs={"class": "form-control"}), 
        required=False
    )
    date__gte = forms.DateField(label="Start Date",widget=forms.DateInput(attrs={"class": "form-control date-input"}), required=False)
    date__lte = forms.DateField(label="End Date",widget=forms.DateInput(attrs={"class": "form-control date-input"}), required=False)
    time__gte = forms.TimeField(label="Start Time",widget=forms.TimeInput(attrs={"class": "form-control time-input"}), required=False)
    time__lte = forms.TimeField(label="End Time",widget=forms.TimeInput(attrs={"class": "form-control time-input"}), required=False)
    account = forms.ModelChoiceField(queryset=Account.objects.filter(is_active=True), required=False, widget=forms.Select(attrs={"class": "form-control"}))
    order_by = forms.ModelChoiceField(queryset=User.objects.filter(is_active=True), required=False, widget=forms.Select(attrs={"class": "form-control"}))
    channel = forms.ModelChoiceField(queryset=Channel.objects.all(), required=False, widget=forms.Select(attrs={"class": "form-control"}))