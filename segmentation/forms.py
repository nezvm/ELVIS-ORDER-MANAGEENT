from django import forms
from .models import CustomerSegment


class CustomerSegmentForm(forms.ModelForm):
    filter_criteria = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 
                                     'placeholder': '{"value_tier": "high", "lifecycle_stage": "active"}'}),
        required=False,
        help_text='JSON filter criteria for dynamic segmentation'
    )
    
    class Meta:
        model = CustomerSegment
        fields = ['name', 'code', 'segment_type', 'description', 'color', 'icon', 'filter_criteria']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'segment_type': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'fa-users'}),
        }
    
    def clean_filter_criteria(self):
        import json
        value = self.cleaned_data['filter_criteria']
        if not value:
            return {}
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            raise forms.ValidationError('Invalid JSON format')
