from django import forms
from .models import Carrier, CarrierCredential, ShippingRule, Shipment, NDRRecord


class CarrierForm(forms.ModelForm):
    class Meta:
        model = Carrier
        fields = ['name', 'code', 'logo', 'website', 'tracking_url_template',
                  'supports_cod', 'supports_prepaid', 'supports_reverse',
                  'status', 'priority']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., delhivery'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
            'tracking_url_template': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'https://carrier.com/track/{tracking_number}'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'priority': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class CarrierCredentialForm(forms.ModelForm):
    class Meta:
        model = CarrierCredential
        fields = ['carrier', 'environment', 'api_key', 'api_secret', 'client_id',
                  'client_secret', 'base_url', 'webhook_secret', 'additional_config']
        widgets = {
            'carrier': forms.Select(attrs={'class': 'form-control'}),
            'environment': forms.Select(attrs={'class': 'form-control'}),
            'api_key': forms.TextInput(attrs={'class': 'form-control'}),
            'api_secret': forms.PasswordInput(attrs={'class': 'form-control'}),
            'client_id': forms.TextInput(attrs={'class': 'form-control'}),
            'client_secret': forms.PasswordInput(attrs={'class': 'form-control'}),
            'base_url': forms.URLInput(attrs={'class': 'form-control'}),
            'webhook_secret': forms.TextInput(attrs={'class': 'form-control'}),
            'additional_config': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ShippingRuleForm(forms.ModelForm):
    condition_value = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Value or JSON array'}),
        help_text='Enter a single value or JSON array for in_list conditions'
    )
    
    class Meta:
        model = ShippingRule
        fields = ['name', 'description', 'rule_type', 'priority', 'condition_field',
                  'condition_operator', 'condition_value', 'assigned_carrier', 'fallback_carrier']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'rule_type': forms.Select(attrs={'class': 'form-control'}),
            'priority': forms.NumberInput(attrs={'class': 'form-control'}),
            'condition_field': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., state, weight, total_amount'}),
            'condition_operator': forms.Select(attrs={'class': 'form-control'}),
            'assigned_carrier': forms.Select(attrs={'class': 'form-control'}),
            'fallback_carrier': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def clean_condition_value(self):
        import json
        value = self.cleaned_data['condition_value']
        try:
            # Try to parse as JSON
            return json.loads(value)
        except json.JSONDecodeError:
            # Return as string
            return value


class ShipmentForm(forms.ModelForm):
    class Meta:
        model = Shipment
        fields = ['carrier', 'status', 'weight', 'length', 'width', 'height',
                  'shipping_cost', 'is_cod', 'cod_amount', 'expected_delivery_date']
        widgets = {
            'carrier': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'length': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'width': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'height': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'shipping_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'cod_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'expected_delivery_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class NDRActionForm(forms.ModelForm):
    class Meta:
        model = NDRRecord
        fields = ['action', 'action_notes', 'customer_contacted', 'customer_response',
                  'new_delivery_date', 'is_resolved']
        widgets = {
            'action': forms.Select(attrs={'class': 'form-control'}),
            'action_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'customer_response': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'new_delivery_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
