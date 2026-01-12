from django import forms
from .models import DynamicChannel, ChannelFormField


class DynamicChannelForm(forms.ModelForm):
    class Meta:
        model = DynamicChannel
        fields = ['name', 'code', 'prefix', 'description', 'icon', 'color', 
                  'is_cod_channel', 'requires_utr', 'requires_payment_capture', 'sort_order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., whatsapp, shopify'}),
            'prefix': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., WA, SH'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., fa-whatsapp'}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class ChannelFormFieldForm(forms.ModelForm):
    class Meta:
        model = ChannelFormField
        fields = ['channel', 'field_name', 'label', 'field_type', 'is_required', 
                  'is_visible', 'placeholder', 'help_text', 'default_value', 
                  'validation_regex', 'choices', 'sort_order']
        widgets = {
            'channel': forms.Select(attrs={'class': 'form-control'}),
            'field_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., customer_notes'}),
            'label': forms.TextInput(attrs={'class': 'form-control'}),
            'field_type': forms.Select(attrs={'class': 'form-control'}),
            'placeholder': forms.TextInput(attrs={'class': 'form-control'}),
            'help_text': forms.TextInput(attrs={'class': 'form-control'}),
            'default_value': forms.TextInput(attrs={'class': 'form-control'}),
            'validation_regex': forms.TextInput(attrs={'class': 'form-control'}),
            'choices': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '[{"value": "opt1", "label": "Option 1"}]'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control'}),
        }
