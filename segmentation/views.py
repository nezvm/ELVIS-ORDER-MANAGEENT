from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Avg, F
from django.utils import timezone
import json
import csv

from core import mixins
from .models import CustomerProfile, CustomerSegment, CustomerSegmentMembership, SegmentExport, CohortAnalysis
from .tables import CustomerProfileTable, CustomerSegmentTable
from .forms import CustomerSegmentForm
from .services import SegmentationService


class SegmentationDashboardView(mixins.HybridTemplateView):
    template_name = 'segmentation/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Customer Segmentation'
        context['is_segmentation'] = True
        context['is_dashboard'] = True
        
        # Summary stats
        profiles = CustomerProfile.objects.filter(is_active=True)
        context['total_customers'] = profiles.count()
        context['total_revenue'] = profiles.aggregate(total=Sum('lifetime_revenue'))['total'] or 0
        context['avg_lifetime_value'] = profiles.aggregate(avg=Avg('lifetime_revenue'))['avg'] or 0
        
        # Segment counts
        segments = CustomerSegment.objects.filter(is_active=True)
        context['segments'] = segments
        
        # Value tier distribution
        value_dist = profiles.values('value_tier').annotate(count=Count('id'))
        context['value_distribution'] = {v['value_tier']: v['count'] for v in value_dist}
        
        # Lifecycle distribution
        lifecycle_dist = profiles.values('lifecycle_stage').annotate(count=Count('id'))
        context['lifecycle_distribution'] = {l['lifecycle_stage']: l['count'] for l in lifecycle_dist}
        
        # Order behavior distribution
        behavior_dist = profiles.values('order_behavior_segment').annotate(count=Count('id'))
        context['behavior_distribution'] = {b['order_behavior_segment']: b['count'] for b in behavior_dist}
        
        return context


class CustomerProfileListView(mixins.HybridListView):
    model = CustomerProfile
    table_class = CustomerProfileTable
    template_name = 'segmentation/profile_list.html'
    filterset_fields = {
        'order_behavior_segment': ['exact'],
        'lifecycle_stage': ['exact'],
        'value_tier': ['exact'],
        'loyalty_tier': ['exact'],
        'tier_city': ['exact'],
    }
    search_fields = ['customer__customer_name', 'customer__phone_no']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Customer Profiles'
        context['is_segmentation'] = True
        context['is_profile'] = True
        return context


class CustomerProfileDetailView(mixins.HybridDetailView):
    model = CustomerProfile
    template_name = 'segmentation/profile_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Profile: {self.object.customer.customer_name}'
        context['is_segmentation'] = True
        context['is_profile'] = True
        
        # Get customer orders
        from master.models import Order
        context['orders'] = Order.objects.filter(
            customer=self.object.customer, is_active=True
        ).order_by('-created')[:20]
        
        # Get segment memberships
        context['segments'] = CustomerSegmentMembership.objects.filter(
            profile=self.object, is_active=True
        ).select_related('segment')
        
        return context


class CustomerSegmentListView(mixins.HybridListView):
    model = CustomerSegment
    table_class = CustomerSegmentTable
    template_name = 'segmentation/segment_list.html'
    filterset_fields = {'segment_type': ['exact']}
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Customer Segments'
        context['can_add'] = True
        context['new_link'] = reverse_lazy('segmentation:segment_create')
        context['is_segmentation'] = True
        context['is_segment'] = True
        return context


class CustomerSegmentDetailView(mixins.HybridDetailView):
    model = CustomerSegment
    template_name = 'segmentation/segment_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Segment: {self.object.name}'
        context['is_segmentation'] = True
        context['is_segment'] = True
        
        # Get members
        context['members'] = CustomerSegmentMembership.objects.filter(
            segment=self.object, is_active=True
        ).select_related('profile', 'profile__customer')[:100]
        
        # Get exports
        context['exports'] = SegmentExport.objects.filter(
            segment=self.object, is_active=True
        )[:10]
        
        return context


class CustomerSegmentCreateView(mixins.HybridCreateView):
    model = CustomerSegment
    form_class = CustomerSegmentForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'New Segment'
        context['is_segmentation'] = True
        context['is_segment'] = True
        return context


class CustomerSegmentUpdateView(mixins.HybridUpdateView):
    model = CustomerSegment
    form_class = CustomerSegmentForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Update Segment: {self.object.name}'
        context['is_segmentation'] = True
        context['is_segment'] = True
        return context


class CustomerSegmentDeleteView(mixins.HybridDeleteView):
    model = CustomerSegment


class CohortAnalysisView(mixins.HybridTemplateView):
    template_name = 'segmentation/cohort_analysis.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Cohort Analysis'
        context['is_segmentation'] = True
        context['is_cohort'] = True
        
        # Get cohort data
        context['cohorts'] = CohortAnalysis.objects.filter(is_active=True)[:12]
        
        return context


# API Endpoints
@login_required
@require_POST
def compute_profiles(request):
    """Compute all customer profiles."""
    try:
        count = SegmentationService.compute_all_profiles()
        return JsonResponse({'success': True, 'count': count, 'message': f'Computed {count} profiles'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def refresh_segment(request, pk):
    """Refresh segment membership based on criteria."""
    try:
        segment = CustomerSegment.objects.get(pk=pk)
        count = SegmentationService.assign_profiles_to_segment(segment)
        return JsonResponse({'success': True, 'count': count, 'message': f'Assigned {count} customers to segment'})
    except CustomerSegment.DoesNotExist:
        return JsonResponse({'error': 'Segment not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def export_segment(request, pk):
    """Export segment data as CSV."""
    try:
        segment = CustomerSegment.objects.get(pk=pk)
        data = SegmentationService.get_segment_data_for_export(segment)
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="segment_{segment.code}_{timezone.now().strftime("%Y%m%d")}.csv"'
        
        if data:
            writer = csv.DictWriter(response, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        
        # Record export
        SegmentExport.objects.create(
            segment=segment,
            export_type='csv',
            customer_count=len(data),
            exported_by=request.user
        )
        
        return response
        
    except CustomerSegment.DoesNotExist:
        return JsonResponse({'error': 'Segment not found'}, status=404)


@login_required
@require_POST  
def compute_cohorts(request):
    """Compute cohort analysis."""
    try:
        count = SegmentationService.compute_cohort_analysis()
        return JsonResponse({'success': True, 'count': count, 'message': f'Computed {count} cohorts'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def segmentation_dashboard_data(request):
    """API endpoint for segmentation dashboard charts."""
    profiles = CustomerProfile.objects.filter(is_active=True)
    
    # Value tier distribution
    value_dist = profiles.values('value_tier').annotate(
        count=Count('id'),
        revenue=Sum('lifetime_revenue')
    )
    
    # Lifecycle distribution
    lifecycle_dist = profiles.values('lifecycle_stage').annotate(count=Count('id'))
    
    # Channel loyalty distribution
    channel_dist = profiles.values('channel_loyalty').annotate(count=Count('id'))
    
    # Order behavior distribution
    behavior_dist = profiles.values('order_behavior_segment').annotate(count=Count('id'))
    
    return JsonResponse({
        'value_tiers': {
            'labels': [v['value_tier'] or 'Unknown' for v in value_dist],
            'counts': [v['count'] for v in value_dist],
            'revenue': [float(v['revenue'] or 0) for v in value_dist]
        },
        'lifecycle': {
            'labels': [l['lifecycle_stage'] or 'Unknown' for l in lifecycle_dist],
            'data': [l['count'] for l in lifecycle_dist]
        },
        'channels': {
            'labels': [c['channel_loyalty'] or 'Unknown' for c in channel_dist],
            'data': [c['count'] for c in channel_dist]
        },
        'behavior': {
            'labels': [b['order_behavior_segment'] or 'Unknown' for b in behavior_dist],
            'data': [b['count'] for b in behavior_dist]
        }
    })
