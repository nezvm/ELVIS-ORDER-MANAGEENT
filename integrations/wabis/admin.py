from django.contrib import admin
from .models import (
    WabisConfig,
    WabisNumber,
    WabisCustomer,
    WabisCustomerChannel,
    WabisMessage,
    WabisWebhookLog,
    DailyLeadMetrics,
    CampaignMetrics,
)


@admin.register(WabisConfig)
class WabisConfigAdmin(admin.ModelAdmin):
    list_display = ['name', 'connection_status', 'is_active', 'last_webhook_at', 'total_messages_received']
    list_filter = ['connection_status', 'is_active']
    readonly_fields = ['id', 'created', 'updated', 'last_webhook_at', 'total_messages_received', 'total_messages_sent']
    
    fieldsets = (
        ('Configuration', {
            'fields': ('name', 'is_active')
        }),
        ('API Credentials', {
            'fields': ('api_key', 'api_secret', 'webhook_secret', 'verify_token', 'api_base_url'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('connection_status', 'last_webhook_at', 'last_error')
        }),
        ('Stats', {
            'fields': ('total_messages_received', 'total_messages_sent')
        }),
    )


@admin.register(WabisNumber)
class WabisNumberAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'display_phone_number', 'phone_number_id', 'status', 'total_messages_received', 'last_message_at']
    list_filter = ['status', 'webhook_verified']
    search_fields = ['display_name', 'display_phone_number', 'phone_number_id']
    readonly_fields = ['id', 'created', 'updated', 'last_message_at', 'total_messages_received', 'total_customers']


@admin.register(WabisCustomer)
class WabisCustomerAdmin(admin.ModelAdmin):
    list_display = ['wa_id', 'profile_name', 'source_type', 'conversion_status', 'total_messages', 'last_message_at']
    list_filter = ['source_type', 'conversion_status', 'is_from_ad']
    search_fields = ['wa_id', 'profile_name', 'meta_campaign_id']
    readonly_fields = ['id', 'created', 'updated', 'first_seen', 'last_seen']
    raw_id_fields = ['linked_lead', 'linked_customer', 'converted_order', 'assigned_to']


@admin.register(WabisCustomerChannel)
class WabisCustomerChannelAdmin(admin.ModelAdmin):
    list_display = ['customer', 'number', 'message_count', 'first_contact_at', 'last_contact_at']
    list_filter = ['number']
    raw_id_fields = ['customer', 'number']


@admin.register(WabisMessage)
class WabisMessageAdmin(admin.ModelAdmin):
    list_display = ['customer', 'number', 'direction', 'msg_type', 'timestamp_utc', 'body_preview']
    list_filter = ['direction', 'msg_type', 'number']
    search_fields = ['customer__wa_id', 'body', 'message_id']
    readonly_fields = ['id', 'created', 'updated', 'message_id', 'timestamp_utc']
    raw_id_fields = ['customer', 'number']
    
    def body_preview(self, obj):
        if obj.body:
            return obj.body[:50] + '...' if len(obj.body) > 50 else obj.body
        return '-'
    body_preview.short_description = 'Message'


@admin.register(WabisWebhookLog)
class WabisWebhookLogAdmin(admin.ModelAdmin):
    list_display = ['created', 'phone_number_id', 'event_type', 'processed', 'messages_processed', 'error_message']
    list_filter = ['processed', 'event_type', 'phone_number_id']
    readonly_fields = ['id', 'created', 'updated', 'payload', 'headers']
    
    def has_add_permission(self, request):
        return False


@admin.register(DailyLeadMetrics)
class DailyLeadMetricsAdmin(admin.ModelAdmin):
    list_display = ['date', 'number', 'source_type', 'total_leads', 'conversions', 'conversion_rate', 'conversion_value', 'roas']
    list_filter = ['date', 'source_type', 'number']
    date_hierarchy = 'date'
    readonly_fields = ['id', 'created', 'updated']


@admin.register(CampaignMetrics)
class CampaignMetricsAdmin(admin.ModelAdmin):
    list_display = ['date', 'campaign_name', 'spend', 'leads_generated', 'conversions', 'roas']
    list_filter = ['date']
    search_fields = ['campaign_id', 'campaign_name']
    date_hierarchy = 'date'
    readonly_fields = ['id', 'created', 'updated']
