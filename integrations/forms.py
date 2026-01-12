from django import forms
from .models import GoogleWorkspaceConfig, ShopifyStore, IntegrationConfig, WebhookEndpoint


class GoogleWorkspaceConfigForm(forms.ModelForm):
    class Meta:
        model = GoogleWorkspaceConfig
        fields = ['name', 'client_id', 'client_secret', 'service_account_json',
                  'sync_enabled', 'sync_interval_minutes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'client_id': forms.TextInput(attrs={'class': 'form-control'}),
            'client_secret': forms.PasswordInput(attrs={'class': 'form-control'}),
            'service_account_json': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'sync_interval_minutes': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class ShopifyStoreForm(forms.ModelForm):
    class Meta:
        model = ShopifyStore
        fields = ['name', 'shop_domain', 'api_key', 'api_secret', 'access_token',
                  'web_paid_channel', 'web_cod_channel', 'sync_enabled', 
                  'sync_orders', 'sync_products', 'sync_inventory', 'auto_fulfill']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'shop_domain': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'mystore.myshopify.com'}),
            'api_key': forms.TextInput(attrs={'class': 'form-control'}),
            'api_secret': forms.PasswordInput(attrs={'class': 'form-control'}),
            'access_token': forms.PasswordInput(attrs={'class': 'form-control'}),
            'web_paid_channel': forms.Select(attrs={'class': 'form-control'}),
            'web_cod_channel': forms.Select(attrs={'class': 'form-control'}),
        }


class IntegrationConfigForm(forms.ModelForm):
    config = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 
                                     'placeholder': '{"key": "value"}'}),
        required=False,
        help_text='Additional JSON configuration'
    )
    
    class Meta:
        model = IntegrationConfig
        fields = ['name', 'integration_type', 'provider', 'api_key', 'api_secret',
                  'base_url', 'config', 'is_enabled']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'integration_type': forms.Select(attrs={'class': 'form-control'}),
            'provider': forms.TextInput(attrs={'class': 'form-control'}),
            'api_key': forms.TextInput(attrs={'class': 'form-control'}),
            'api_secret': forms.PasswordInput(attrs={'class': 'form-control'}),
            'base_url': forms.URLInput(attrs={'class': 'form-control'}),
        }
    
    def clean_config(self):
        import json
        value = self.cleaned_data['config']
        if not value:
            return {}
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            raise forms.ValidationError('Invalid JSON format')


class WebhookEndpointForm(forms.ModelForm):
    headers = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2,
                                     'placeholder': '{"Authorization": "Bearer token"}'}),
        required=False,
        help_text='Custom headers as JSON'
    )
    
    class Meta:
        model = WebhookEndpoint
        fields = ['name', 'event_type', 'url', 'secret', 'headers', 'is_enabled']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'event_type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'order.created'}),
            'url': forms.URLInput(attrs={'class': 'form-control'}),
            'secret': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def clean_headers(self):
        import json
        value = self.cleaned_data['headers']
        if not value:
            return {}
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            raise forms.ValidationError('Invalid JSON format')
