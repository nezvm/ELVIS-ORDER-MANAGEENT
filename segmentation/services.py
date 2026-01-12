from django.db.models import Sum, Count, Avg, F, Q, Max, Min
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from master.models import Customer, Order
from .models import CustomerProfile, CustomerSegment, CustomerSegmentMembership, CohortAnalysis


class SegmentationService:
    """Service for computing customer segments and metrics."""
    
    # City tier mapping (sample - should be configurable)
    TIER_1_CITIES = ['mumbai', 'delhi', 'bangalore', 'bengaluru', 'chennai', 'hyderabad', 'kolkata', 'pune']
    TIER_2_CITIES = ['ahmedabad', 'surat', 'jaipur', 'lucknow', 'kanpur', 'nagpur', 'indore', 'thane', 'bhopal', 'visakhapatnam', 'vadodara', 'ghaziabad', 'ludhiana', 'agra', 'nashik', 'faridabad', 'meerut', 'rajkot', 'varanasi', 'srinagar']
    
    @staticmethod
    def compute_customer_profile(customer):
        """Compute or update profile metrics for a single customer."""
        profile, created = CustomerProfile.objects.get_or_create(
            customer=customer,
            defaults={'is_active': True}
        )
        
        # Get all orders
        orders = Order.objects.filter(customer=customer, is_active=True)
        
        # Basic metrics
        profile.lifetime_order_count = orders.count()
        
        agg = orders.aggregate(
            total_revenue=Sum('total_amount'),
            avg_value=Avg('total_amount'),
            first_date=Min('created'),
            last_date=Max('created')
        )
        
        profile.lifetime_revenue = agg['total_revenue'] or Decimal('0.00')
        profile.average_order_value = agg['avg_value'] or Decimal('0.00')
        profile.first_order_date = agg['first_date'].date() if agg['first_date'] else None
        profile.last_order_date = agg['last_date'].date() if agg['last_date'] else None
        
        # Days since last order
        if profile.last_order_date:
            profile.days_since_last_order = (timezone.now().date() - profile.last_order_date).days
        
        # Channel analysis
        channel_counts = orders.values('channel__channel_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        if channel_counts:
            profile.primary_channel = channel_counts[0]['channel__channel_type']
            profile.channels_used = list(set([c['channel__channel_type'] for c in channel_counts]))
            profile.channel_order_counts = {c['channel__channel_type']: c['count'] for c in channel_counts}
        
        # Geographic tier
        city = customer.city.lower() if customer.city else ''
        if city in SegmentationService.TIER_1_CITIES:
            profile.tier_city = 'tier_1'
        elif city in SegmentationService.TIER_2_CITIES:
            profile.tier_city = 'tier_2'
        elif customer.state:
            profile.tier_city = 'tier_3'
        else:
            profile.tier_city = 'tier_4'
        
        # Compute segments
        profile.order_behavior_segment = SegmentationService._compute_order_behavior(profile)
        profile.lifecycle_stage = SegmentationService._compute_lifecycle_stage(profile)
        profile.channel_loyalty = SegmentationService._compute_channel_loyalty(profile)
        profile.value_tier = SegmentationService._compute_value_tier(profile)
        profile.loyalty_tier = SegmentationService._compute_loyalty_tier(profile)
        
        profile.last_computed_at = timezone.now()
        profile.save()
        
        return profile
    
    @staticmethod
    def _compute_order_behavior(profile):
        """Determine order behavior segment."""
        count = profile.lifetime_order_count
        
        if count == 0:
            return 'non_ordered'
        elif count == 1:
            return 'one_time'
        elif count == 2:
            return 'new_repeat'
        elif count <= 5:
            return 'repeat'
        elif count <= 10:
            return 'loyal'
        else:
            return 'super_loyal'
    
    @staticmethod
    def _compute_lifecycle_stage(profile):
        """Determine customer lifecycle stage."""
        days = profile.days_since_last_order
        order_count = profile.lifetime_order_count
        
        if order_count == 0:
            return 'new'
        
        # Check if reactivated (ordered after 90+ days gap)
        # This would need more complex logic with order history
        
        if days <= 30:
            if order_count >= 3:
                return 'engaged'
            return 'active'
        elif days <= 60:
            return 'at_risk'
        elif days <= 90:
            return 'dropped'
        else:
            return 'churned'
    
    @staticmethod
    def _compute_channel_loyalty(profile):
        """Determine channel loyalty segment."""
        channels = profile.channels_used or []
        primary = profile.primary_channel or ''
        channel_counts = profile.channel_order_counts or {}
        
        if len(channels) >= 3:
            return 'multi_channel'
        
        if 'WhatsApp' in primary:
            # Check COD vs prepaid ratio
            whatsapp_count = channel_counts.get('WhatsApp', 0)
            cod_count = channel_counts.get('WhatsApp_COD', 0)
            
            if cod_count > whatsapp_count:
                return 'cod_preferred'
            elif whatsapp_count > cod_count:
                return 'prepaid_preferred'
            return 'whatsapp_loyal'
        
        if 'Shopify' in primary or 'WEB' in primary:
            return 'web_only'
        
        return 'multi_channel'
    
    @staticmethod
    def _compute_value_tier(profile):
        """Determine value tier based on lifetime revenue."""
        revenue = float(profile.lifetime_revenue)
        
        # These thresholds should be configurable
        if revenue >= 10000:
            return 'high'
        elif revenue >= 3000:
            return 'medium'
        else:
            return 'low'
    
    @staticmethod
    def _compute_loyalty_tier(profile):
        """Determine loyalty program tier."""
        revenue = float(profile.lifetime_revenue)
        order_count = profile.lifetime_order_count
        
        # Points calculation (simple model)
        profile.loyalty_points = int(revenue / 10) + (order_count * 50)
        
        if profile.loyalty_points >= 5000:
            return 'platinum'
        elif profile.loyalty_points >= 2000:
            return 'gold'
        elif profile.loyalty_points >= 500:
            return 'silver'
        else:
            return 'bronze'
    
    @staticmethod
    def compute_all_profiles():
        """Compute profiles for all customers."""
        customers = Customer.objects.filter(is_active=True)
        count = 0
        
        for customer in customers:
            SegmentationService.compute_customer_profile(customer)
            count += 1
        
        return count
    
    @staticmethod
    def update_segment_stats(segment):
        """Update statistics for a segment."""
        members = CustomerSegmentMembership.objects.filter(
            segment=segment, is_active=True
        ).select_related('profile')
        
        profiles = [m.profile for m in members]
        
        segment.customer_count = len(profiles)
        segment.total_revenue = sum(p.lifetime_revenue for p in profiles)
        segment.avg_order_value = (
            sum(p.average_order_value for p in profiles) / len(profiles)
            if profiles else Decimal('0.00')
        )
        segment.last_computed_at = timezone.now()
        segment.save()
    
    @staticmethod
    def assign_profiles_to_segment(segment):
        """Assign customer profiles to a segment based on filter criteria."""
        criteria = segment.filter_criteria
        
        if not criteria:
            return 0
        
        # Build queryset based on criteria
        qs = CustomerProfile.objects.filter(is_active=True)
        
        # Apply filters
        for field, value in criteria.items():
            if isinstance(value, dict):
                # Complex filter (e.g., {"gte": 10})
                for op, val in value.items():
                    if op == 'gte':
                        qs = qs.filter(**{f"{field}__gte": val})
                    elif op == 'lte':
                        qs = qs.filter(**{f"{field}__lte": val})
                    elif op == 'in':
                        qs = qs.filter(**{f"{field}__in": val})
            else:
                qs = qs.filter(**{field: value})
        
        # Clear existing memberships
        CustomerSegmentMembership.objects.filter(segment=segment).delete()
        
        # Create new memberships
        memberships = [
            CustomerSegmentMembership(profile=profile, segment=segment)
            for profile in qs
        ]
        CustomerSegmentMembership.objects.bulk_create(memberships)
        
        # Update stats
        SegmentationService.update_segment_stats(segment)
        
        return len(memberships)
    
    @staticmethod
    def get_segment_data_for_export(segment):
        """Get customer data for segment export."""
        members = CustomerSegmentMembership.objects.filter(
            segment=segment, is_active=True
        ).select_related('profile', 'profile__customer')
        
        data = []
        for member in members:
            profile = member.profile
            customer = profile.customer
            
            data.append({
                'customer_name': customer.customer_name,
                'phone_no': customer.phone_no,
                'email': customer.alternate_phone_no,  # Using alt phone as email placeholder
                'city': customer.city,
                'state': customer.state,
                'pincode': customer.pincode,
                'lifetime_orders': profile.lifetime_order_count,
                'lifetime_revenue': float(profile.lifetime_revenue),
                'avg_order_value': float(profile.average_order_value),
                'last_order_date': str(profile.last_order_date) if profile.last_order_date else '',
                'primary_channel': profile.primary_channel,
                'value_tier': profile.value_tier,
                'loyalty_tier': profile.loyalty_tier,
            })
        
        return data
    
    @staticmethod
    def compute_cohort_analysis():
        """Compute cohort analysis data."""
        from django.db.models.functions import TruncMonth
        
        # Get all customers with their first order month
        customer_cohorts = Order.objects.filter(
            is_active=True
        ).values('customer').annotate(
            first_order_month=TruncMonth(Min('created'))
        )
        
        # Group by cohort month
        cohorts = {}
        for item in customer_cohorts:
            month = item['first_order_month']
            if month:
                month_key = month.replace(day=1).date()
                if month_key not in cohorts:
                    cohorts[month_key] = []
                cohorts[month_key].append(item['customer'])
        
        # Calculate retention for each cohort
        today = timezone.now().date()
        
        for cohort_month, customer_ids in cohorts.items():
            cohort, created = CohortAnalysis.objects.get_or_create(
                cohort_month=cohort_month,
                defaults={'total_customers': len(customer_ids)}
            )
            
            cohort.total_customers = len(customer_ids)
            retention = {}
            revenue = {}
            aov = {}
            
            # Calculate for each subsequent month
            for month_offset in range(12):  # Up to 12 months
                check_month = cohort_month + timedelta(days=30 * month_offset)
                if check_month > today:
                    break
                
                month_orders = Order.objects.filter(
                    customer_id__in=customer_ids,
                    is_active=True,
                    created__year=check_month.year,
                    created__month=check_month.month
                )
                
                active_customers = month_orders.values('customer').distinct().count()
                month_revenue = month_orders.aggregate(total=Sum('total_amount'))['total'] or 0
                month_aov = month_orders.aggregate(avg=Avg('total_amount'))['avg'] or 0
                
                retention[f"month_{month_offset}"] = active_customers
                revenue[f"month_{month_offset}"] = float(month_revenue)
                aov[f"month_{month_offset}"] = float(month_aov)
            
            cohort.retention_data = retention
            cohort.revenue_data = revenue
            cohort.aov_data = aov
            cohort.save()
        
        return len(cohorts)
