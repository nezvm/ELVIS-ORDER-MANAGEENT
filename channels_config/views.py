from django.urls import reverse_lazy
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from core import mixins
from .models import DynamicChannel, ChannelFormField, UTRRecord
from .tables import DynamicChannelTable, ChannelFormFieldTable
from .forms import DynamicChannelForm, ChannelFormFieldForm


class ChannelListView(mixins.HybridListView):
    model = DynamicChannel
    table_class = DynamicChannelTable
    filterset_fields = {'name': ['contains'], 'code': ['exact'], 'is_cod_channel': ['exact']}
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Channel Configuration'
        context['can_add'] = True
        context['new_link'] = reverse_lazy('channels_config:channel_create')
        context['is_channel_config'] = True
        return context


class ChannelDetailView(mixins.HybridDetailView):
    model = DynamicChannel
    template_name = 'channels_config/channel_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Channel: {self.object.name}'
        context['form_fields'] = self.object.form_fields.filter(is_active=True).order_by('sort_order')
        context['is_channel_config'] = True
        return context


class ChannelCreateView(mixins.HybridCreateView):
    model = DynamicChannel
    form_class = DynamicChannelForm
    template_name = 'channels_config/channel_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'New Channel'
        context['is_channel_config'] = True
        return context


class ChannelUpdateView(mixins.HybridUpdateView):
    model = DynamicChannel
    form_class = DynamicChannelForm
    template_name = 'channels_config/channel_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Update Channel: {self.object.name}'
        context['is_channel_config'] = True
        return context


class ChannelDeleteView(mixins.HybridDeleteView):
    model = DynamicChannel


class FormFieldListView(mixins.HybridListView):
    model = ChannelFormField
    table_class = ChannelFormFieldTable
    filterset_fields = {'channel': ['exact'], 'field_type': ['exact']}
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Form Field Configuration'
        context['can_add'] = True
        context['new_link'] = reverse_lazy('channels_config:formfield_create')
        context['is_channel_config'] = True
        return context


class FormFieldCreateView(mixins.HybridCreateView):
    model = ChannelFormField
    form_class = ChannelFormFieldForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'New Form Field'
        context['is_channel_config'] = True
        return context


class FormFieldUpdateView(mixins.HybridUpdateView):
    model = ChannelFormField
    form_class = ChannelFormFieldForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Update Form Field: {self.object.label}'
        context['is_channel_config'] = True
        return context


class FormFieldDeleteView(mixins.HybridDeleteView):
    model = ChannelFormField


@login_required
@require_http_methods(["GET"])
def validate_utr(request):
    """API endpoint to validate UTR uniqueness."""
    utr = request.GET.get('utr', '').strip()
    channel_id = request.GET.get('channel_id')
    
    if not utr:
        return JsonResponse({'valid': False, 'message': 'UTR is required'})
    
    # Check if UTR already exists
    exists = UTRRecord.objects.filter(utr=utr).exists()
    
    if exists:
        return JsonResponse({'valid': False, 'message': 'This UTR already exists'})
    
    return JsonResponse({'valid': True, 'message': 'UTR is unique'})


@login_required
@require_http_methods(["GET"])
def get_channel_fields(request):
    """API endpoint to get form fields for a specific channel."""
    channel_id = request.GET.get('channel_id')
    
    if not channel_id:
        return JsonResponse({'error': 'Channel ID required'}, status=400)
    
    try:
        channel = DynamicChannel.objects.get(pk=channel_id, is_active=True)
        fields = channel.form_fields.filter(is_active=True, is_visible=True).order_by('sort_order')
        
        field_data = [{
            'id': str(f.id),
            'field_name': f.field_name,
            'label': f.label,
            'field_type': f.field_type,
            'is_required': f.is_required,
            'placeholder': f.placeholder,
            'help_text': f.help_text,
            'default_value': f.default_value,
            'choices': f.choices,
            'validation_regex': f.validation_regex,
        } for f in fields]
        
        return JsonResponse({
            'channel': {
                'id': str(channel.id),
                'name': channel.name,
                'requires_utr': channel.requires_utr,
                'is_cod_channel': channel.is_cod_channel,
            },
            'fields': field_data
        })
    except DynamicChannel.DoesNotExist:
        return JsonResponse({'error': 'Channel not found'}, status=404)
