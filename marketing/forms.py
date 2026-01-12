from django import forms
from .models import (
    Lead, WhatsAppProvider, WhatsAppTemplate,
    Campaign, NotificationEvent
)


class LeadForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = ['name', 'phone_no', 'email', 'address', 'city', 'district', 
                  'state', 'pincode', 'lead_status', 'assigned_to', 'follow_up_date',
                  'whatsapp_opt_in', 'sms_opt_in', 'notes', 'tags']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500'}),
            'phone_no': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500'}),
            'email': forms.EmailInput(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500'}),
            'address': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500', 'rows': 2}),
            'city': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500'}),
            'district': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500'}),
            'state': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500'}),
            'pincode': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500'}),
            'lead_status': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500'}),
            'assigned_to': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500'}),
            'follow_up_date': forms.DateInput(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500', 'rows': 3}),
        }


class WhatsAppProviderForm(forms.ModelForm):
    class Meta:
        model = WhatsAppProvider
        fields = ['name', 'provider_type', 'is_default', 'api_key', 'api_secret',
                  'access_token', 'phone_number_id', 'waba_id', 'webhook_url',
                  'webhook_secret', 'rate_limit_per_second', 'daily_limit']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500'}),
            'provider_type': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500'}),
            'api_key': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500'}),
            'api_secret': forms.PasswordInput(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500'}),
            'access_token': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500', 'rows': 2}),
            'phone_number_id': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500'}),
            'waba_id': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500'}),
            'webhook_url': forms.URLInput(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500'}),
            'webhook_secret': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500'}),
            'rate_limit_per_second': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500'}),
            'daily_limit': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500'}),
        }


class WhatsAppTemplateForm(forms.ModelForm):
    class Meta:
        model = WhatsAppTemplate
        fields = ['provider', 'name', 'template_id', 'category', 'language',
                  'header_type', 'header_content', 'body', 'footer']
        widgets = {
            'provider': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500'}),
            'name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500'}),
            'template_id': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500'}),
            'category': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500'}),
            'language': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500'}),
            'header_type': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500'}),
            'header_content': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500'}),
            'body': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500', 'rows': 4, 'placeholder': 'Use {{1}}, {{2}} for variables'}),
            'footer': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500'}),
        }


class CampaignForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = ['name', 'description', 'provider', 'template', 'scheduled_at',
                  'throttle_rate', 'attribution_window_days']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500'}),
            'description': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500', 'rows': 2}),
            'provider': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500'}),
            'template': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500'}),
            'scheduled_at': forms.DateTimeInput(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500', 'type': 'datetime-local'}),
            'throttle_rate': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500'}),
            'attribution_window_days': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500'}),
        }


class NotificationEventForm(forms.ModelForm):
    class Meta:
        model = NotificationEvent
        fields = ['is_enabled', 'template', 'provider', 'audience', 'retry_count',
                  'retry_delay_seconds', 'quiet_hours_start', 'quiet_hours_end']
        widgets = {
            'template': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500'}),
            'provider': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500'}),
            'audience': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500'}),
            'retry_count': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500'}),
            'retry_delay_seconds': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500'}),
            'quiet_hours_start': forms.TimeInput(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500', 'type': 'time'}),
            'quiet_hours_end': forms.TimeInput(attrs={'class': 'w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500', 'type': 'time'}),
        }
