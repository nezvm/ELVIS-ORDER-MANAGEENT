from celery import shared_task
from django.utils import timezone


@shared_task
def compute_customer_profile_task(customer_id):
    """Compute profile for a single customer."""
    from master.models import Customer
    from segmentation.services import SegmentationService
    
    try:
        customer = Customer.objects.get(pk=customer_id)
        profile = SegmentationService.compute_customer_profile(customer)
        return f"Computed profile for {customer.customer_name}"
    except Customer.DoesNotExist:
        return "Customer not found"
    except Exception as e:
        return f"Error: {str(e)}"


@shared_task
def compute_all_profiles_task():
    """Compute profiles for all customers."""
    from segmentation.services import SegmentationService
    
    try:
        count = SegmentationService.compute_all_profiles()
        return f"Computed {count} profiles"
    except Exception as e:
        return f"Error: {str(e)}"


@shared_task
def refresh_segment_task(segment_id):
    """Refresh membership for a segment."""
    from segmentation.models import CustomerSegment
    from segmentation.services import SegmentationService
    
    try:
        segment = CustomerSegment.objects.get(pk=segment_id)
        count = SegmentationService.assign_profiles_to_segment(segment)
        return f"Assigned {count} customers to {segment.name}"
    except CustomerSegment.DoesNotExist:
        return "Segment not found"
    except Exception as e:
        return f"Error: {str(e)}"


@shared_task
def compute_cohort_analysis_task():
    """Compute cohort analysis."""
    from segmentation.services import SegmentationService
    
    try:
        count = SegmentationService.compute_cohort_analysis()
        return f"Computed {count} cohorts"
    except Exception as e:
        return f"Error: {str(e)}"


@shared_task
def refresh_all_segments_task():
    """Refresh all segment memberships."""
    from segmentation.models import CustomerSegment
    from segmentation.services import SegmentationService
    
    segments = CustomerSegment.objects.filter(is_active=True)
    total = 0
    
    for segment in segments:
        count = SegmentationService.assign_profiles_to_segment(segment)
        total += count
    
    return f"Assigned {total} customers across {segments.count()} segments"
