from django.contrib import admin
from core.base import BaseAdmin
from .models import CustomerProfile, CustomerSegment, CustomerSegmentMembership, SegmentExport, CohortAnalysis


@admin.register(CustomerProfile)
class CustomerProfileAdmin(BaseAdmin):
    list_display = ['customer', 'lifetime_order_count', 'lifetime_revenue', 'order_behavior_segment', 
                    'lifecycle_stage', 'value_tier', 'loyalty_tier']
    list_filter = ['order_behavior_segment', 'lifecycle_stage', 'value_tier', 'loyalty_tier', 'tier_city']
    search_fields = ['customer__customer_name', 'customer__phone_no']
    readonly_fields = ['lifetime_order_count', 'lifetime_revenue', 'average_order_value', 
                       'first_order_date', 'last_order_date', 'last_computed_at']


class SegmentMembershipInline(admin.TabularInline):
    model = CustomerSegmentMembership
    extra = 0
    readonly_fields = ['added_at']


@admin.register(CustomerSegment)
class CustomerSegmentAdmin(BaseAdmin):
    list_display = ['name', 'code', 'segment_type', 'customer_count', 'total_revenue', 'is_active']
    list_filter = ['segment_type', 'is_active']
    search_fields = ['name', 'code', 'description']
    readonly_fields = ['customer_count', 'total_revenue', 'avg_order_value', 'last_computed_at']


@admin.register(SegmentExport)
class SegmentExportAdmin(BaseAdmin):
    list_display = ['segment', 'export_type', 'customer_count', 'exported_by', 'created']
    list_filter = ['export_type', 'segment']


@admin.register(CohortAnalysis)
class CohortAnalysisAdmin(BaseAdmin):
    list_display = ['cohort_month', 'total_customers', 'created']
    readonly_fields = ['retention_data', 'revenue_data', 'aov_data']
