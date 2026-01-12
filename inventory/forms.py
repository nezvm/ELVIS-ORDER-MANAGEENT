from django import forms
from .models import Warehouse, StockLevel, StockMovement, StockTransfer


class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ['name', 'code', 'address', 'city', 'state', 'pincode', 'country',
                  'contact_person', 'contact_phone', 'contact_email', 'is_primary']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'pincode': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
        }


class StockLevelForm(forms.ModelForm):
    class Meta:
        model = StockLevel
        fields = ['product', 'warehouse', 'quantity', 'safety_stock', 'reorder_point',
                  'reorder_quantity', 'bin_location']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'warehouse': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'safety_stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'reorder_point': forms.NumberInput(attrs={'class': 'form-control'}),
            'reorder_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'bin_location': forms.TextInput(attrs={'class': 'form-control'}),
        }


class StockMovementForm(forms.ModelForm):
    class Meta:
        model = StockMovement
        fields = ['product', 'warehouse', 'movement_type', 'quantity', 'reference_type',
                  'reference_id', 'unit_cost', 'notes']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control select2'}),
            'warehouse': forms.Select(attrs={'class': 'form-control'}),
            'movement_type': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'reference_type': forms.TextInput(attrs={'class': 'form-control'}),
            'reference_id': forms.TextInput(attrs={'class': 'form-control'}),
            'unit_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class StockTransferForm(forms.ModelForm):
    class Meta:
        model = StockTransfer
        fields = ['source_warehouse', 'destination_warehouse', 'notes']
        widgets = {
            'source_warehouse': forms.Select(attrs={'class': 'form-control'}),
            'destination_warehouse': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class StockAdjustmentForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    new_quantity = forms.IntegerField(
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from master.models import Product
        self.fields['product'].queryset = Product.objects.filter(is_active=True)
