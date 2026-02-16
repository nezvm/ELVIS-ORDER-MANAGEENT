from django.contrib import admin
from .models import (
    WhatsAppCustomer, 
    WhatsAppNumberConfig, 
    WhatsAppCustomerChannel, 
    WhatsAppMessage,
    WhatsAppWebhookLog,
    WhatsAppConnectedNumber,
    MetaConversionConfig,
    MetaAdsConfig,
    DailyLeadReport,
    LeadConversionEvent,
)


@admin.register(WhatsAppCustomer)
class WhatsAppCustomerAdmin(admin.ModelAdmin):
    list_display = [
        'wa_id', 'profile_name', 'source_type', 'lead_status', 'conversion_value',
        'total_messages', 'last_seen', 'assigned_sales_user'
    ]
    list_filter = ['source_type', 'lead_status', 'is_from_ad', 'attribution_source', 'created']
    search_fields = ['wa_id', 'profile_name', 'meta_ad_headline', 'meta_campaign_id']
    readonly_fields = ['id', 'created', 'updated', 'first_seen', 'last_seen', 'lead_created_at']
    raw_id_fields = ['linked_customer', 'linked_lead', 'assigned_sales_user', 'converted_order']
    
    fieldsets = (
        ('Customer Info', {
            'fields': ('wa_id', 'profile_name')
        }),
        ('Lead Status & Conversion', {
            'fields': (
                'lead_status', 'lead_created_at', 'won_at', 'lost_at',
                'converted_order', 'conversion_value',
                'conversion_sent', 'conversion_sent_at', 'conversion_event_id'
            )
        }),
        ('Attribution & Ads', {
            'fields': (
                'source_type', 'is_from_ad', 'attribution_source', 'ad_platform', 'tags',
                'meta_campaign_id', 'meta_adset_id', 'meta_ad_id',
                'meta_ad_source_type', 'meta_ad_source_id', 'meta_ad_source_url',
                'meta_ad_headline', 'meta_ad_body', 'meta_ctwa_clid',
                'meta_fbclid', 'google_gclid'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('first_seen', 'last_seen', 'last_message_at', 'last_message_preview')
        }),
        ('Assignment', {
            'fields': ('assigned_sales_user',)
        }),
        ('Links', {
            'fields': ('linked_customer', 'linked_lead')
        }),
        ('Stats', {
            'fields': ('total_messages', 'total_channels_contacted')
        }),
        ('System', {
            'fields': ('id', 'created', 'updated', 'is_active'),
            'classes': ('collapse',)
        }),
    )


@admin.register(WhatsAppConnectedNumber)
class WhatsAppConnectedNumberAdmin(admin.ModelAdmin):
    list_display = [
        'display_name', 'display_phone_number', 'phone_number_id', 'waba_id',
        'status', 'webhook_verified', 'total_leads_captured', 'created'
    ]
    list_filter = ['status', 'webhook_verified', 'created']
    search_fields = ['display_name', 'display_phone_number', 'phone_number_id', 'waba_id']
    readonly_fields = ['id', 'created', 'updated', 'last_webhook_at', 'webhook_count']
    raw_id_fields = ['connected_by']
    
    fieldsets = (
        ('Number Info', {
            'fields': ('display_name', 'display_phone_number', 'phone_number_id', 'waba_id')
        }),
        ('Status', {
            'fields': ('status', 'webhook_verified', 'is_active')
        }),
        ('Auth', {
            'fields': ('access_token', 'token_expires_at'),
            'classes': ('collapse',)
        }),
        ('Stats', {
            'fields': ('last_webhook_at', 'webhook_count', 'total_messages_received', 'total_leads_captured')
        }),
        ('Meta', {
            'fields': ('connected_by', 'meta_data'),
            'classes': ('collapse',)
        }),
        ('System', {
            'fields': ('id', 'created', 'updated'),
            'classes': ('collapse',)
        }),
    )


@admin.register(WhatsAppNumberConfig)
class WhatsAppNumberConfigAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'phone_number_id', 'display_phone_number', 
        'last_webhook_at', 'total_messages_received', 'total_customers'
    ]
    search_fields = ['name', 'phone_number_id', 'display_phone_number']
    readonly_fields = ['id', 'created', 'updated', 'last_webhook_at', 'webhook_count']


@admin.register(WhatsAppCustomerChannel)
class WhatsAppCustomerChannelAdmin(admin.ModelAdmin):
    list_display = [
        'customer', 'phone_number_id', 'message_count', 
        'first_contact_at', 'last_contact_at'
    ]
    list_filter = ['phone_number_id']
    search_fields = ['customer__wa_id', 'customer__profile_name']
    readonly_fields = ['id', 'created', 'updated', 'first_contact_at', 'last_contact_at']
    raw_id_fields = ['customer', 'number_config']


@admin.register(WhatsAppMessage)
class WhatsAppMessageAdmin(admin.ModelAdmin):
    list_display = [
        'customer', 'direction', 'msg_type', 'phone_number_id', 
        'timestamp_utc', 'body_preview'
    ]
    list_filter = ['direction', 'msg_type', 'phone_number_id']
    search_fields = ['customer__wa_id', 'body', 'message_id']
    readonly_fields = ['id', 'created', 'updated', 'message_id', 'timestamp_utc']
    raw_id_fields = ['customer']
    
    def body_preview(self, obj):
        if obj.body:
            return obj.body[:50] + '...' if len(obj.body) > 50 else obj.body
        return '-'
    body_preview.short_description = 'Message'


@admin.register(WhatsAppWebhookLog)
class WhatsAppWebhookLogAdmin(admin.ModelAdmin):
    list_display = [
        'created', 'phone_number_id', 'event_type', 
        'processed', 'messages_processed', 'error_message'
    ]
    list_filter = ['processed', 'event_type', 'phone_number_id']
    readonly_fields = ['id', 'created', 'updated', 'payload']
    
    def has_add_permission(self, request):
        return False


# =============================================================================
# META INTEGRATION CONFIGS
# =============================================================================

@admin.register(MetaConversionConfig)
class MetaConversionConfigAdmin(admin.ModelAdmin):
    list_display = ['name', 'pixel_id', 'is_active', 'test_mode', 'events_sent', 'last_event_at']
    list_filter = ['is_active', 'test_mode']
    search_fields = ['name', 'pixel_id']
    readonly_fields = ['id', 'created', 'updated', 'events_sent', 'last_event_at']
    
    fieldsets = (
        ('Configuration', {
            'fields': ('name', 'pixel_id', 'access_token', 'is_active')
        }),
        ('Test Mode', {
            'fields': ('test_mode', 'test_event_code'),
            'description': 'Enable test mode to send events to Events Manager test area'
        }),
        ('Stats', {
            'fields': ('events_sent', 'last_event_at', 'last_error'),
            'classes': ('collapse',)
        }),
        ('System', {
            'fields': ('id', 'created', 'updated'),
            'classes': ('collapse',)
        }),
    )


@admin.register(MetaAdsConfig)
class MetaAdsConfigAdmin(admin.ModelAdmin):
    list_display = ['name', 'ad_account_id', 'business_id', 'is_active', 'last_sync_at']
    list_filter = ['is_active']
    search_fields = ['name', 'ad_account_id', 'business_id']
    readonly_fields = ['id', 'created', 'updated', 'last_sync_at']
    
    fieldsets = (
        ('Configuration', {
            'fields': ('name', 'ad_account_id', 'access_token', 'is_active')
        }),
        ('Embedded Signup', {
            'fields': ('business_id',),
            'description': 'Required for connecting numbers to existing portfolio'
        }),
        ('Stats', {
            'fields': ('last_sync_at', 'last_error'),
            'classes': ('collapse',)
        }),
        ('System', {
            'fields': ('id', 'created', 'updated'),
            'classes': ('collapse',)
        }),
    )


# =============================================================================
# REPORTING
# =============================================================================

@admin.register(DailyLeadReport)
class DailyLeadReportAdmin(admin.ModelAdmin):
    list_display = [
        'report_date', 'phone_number_id', 'total_leads', 'ad_leads', 
        'conversions', 'conversion_rate', 'revenue', 'ad_spend', 'roas'
    ]
    list_filter = ['report_date', 'phone_number_id']
    search_fields = ['phone_number_id', 'campaign_id']
    readonly_fields = ['id', 'created', 'updated']
    date_hierarchy = 'report_date'
    
    def has_add_permission(self, request):
        return False


@admin.register(LeadConversionEvent)
class LeadConversionEventAdmin(admin.ModelAdmin):
    list_display = [
        'customer', 'event_name', 'value', 'currency', 
        'sent', 'sent_at', 'response_code'
    ]
    list_filter = ['event_name', 'sent', 'event_time']
    search_fields = ['customer__wa_id', 'event_id', 'campaign_id']
    readonly_fields = ['id', 'created', 'updated', 'event_id', 'event_time', 'sent_at']
    raw_id_fields = ['customer', 'order']
    
    def has_add_permission(self, request):
        return False
