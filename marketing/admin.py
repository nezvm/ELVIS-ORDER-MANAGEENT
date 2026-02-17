from django.contrib import admin
from .models import (
    Lead, LeadActivity, WhatsAppProvider, WhatsAppTemplate,
    NotificationEvent, Campaign, CampaignRecipient, MessageLog,
    DoNotMessage, GeoMarketStats
)
from .meta_models import (
    MetaIntegrationConfig, MetaDailyInsights, CapiEventLog, MarketingDailyRollup
)


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone_no', 'match_status', 'lead_status', 'attribution_model', 'attribution_confidence', 'conversion_status', 'state', 'city', 'assigned_to', 'created']
    list_filter = ['match_status', 'lead_status', 'attribution_model', 'conversion_status', 'source_type', 'state', 'whatsapp_opt_in']
    search_fields = ['name', 'phone_no', 'email']
    readonly_fields = ['first_synced_at', 'last_synced_at']


@admin.register(LeadActivity)
class LeadActivityAdmin(admin.ModelAdmin):
    list_display = ['lead', 'activity_type', 'created', 'performed_by']
    list_filter = ['activity_type']


@admin.register(WhatsAppProvider)
class WhatsAppProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'provider_type', 'status', 'is_default', 'messages_sent_today']
    list_filter = ['provider_type', 'status']


@admin.register(WhatsAppTemplate)
class WhatsAppTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'provider', 'category', 'language', 'status']
    list_filter = ['provider', 'category', 'language', 'status']


@admin.register(NotificationEvent)
class NotificationEventAdmin(admin.ModelAdmin):
    list_display = ['event_type', 'is_enabled', 'template', 'provider', 'audience']
    list_filter = ['is_enabled', 'audience']


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'template', 'total_recipients', 'sent_count', 'delivered_count', 'scheduled_at']
    list_filter = ['status', 'provider']
    search_fields = ['name']


@admin.register(MessageLog)
class MessageLogAdmin(admin.ModelAdmin):
    list_display = ['phone_no', 'message_type', 'status', 'template', 'created']
    list_filter = ['message_type', 'status', 'provider']
    search_fields = ['phone_no', 'message_id']


@admin.register(DoNotMessage)
class DoNotMessageAdmin(admin.ModelAdmin):
    list_display = ['phone_no', 'reason', 'source', 'opted_out_at']
    search_fields = ['phone_no']


@admin.register(GeoMarketStats)
class GeoMarketStatsAdmin(admin.ModelAdmin):
    list_display = ['state', 'district', 'pincode', 'period_type', 'leads_count', 'orders_count', 'revenue', 'market_category']
    list_filter = ['period_type', 'market_category', 'state']


# =============================================================================
# META INTEGRATION MODELS
# =============================================================================

@admin.register(MetaIntegrationConfig)
class MetaIntegrationConfigAdmin(admin.ModelAdmin):
    list_display = ['ad_account_id', 'pixel_id', 'dataset_id', 'is_active', 'last_insights_sync_at', 'capi_success_count']
    list_filter = ['is_active']
    readonly_fields = ['last_insights_sync_at', 'last_capi_send_at', 'last_attribution_run_at', 'capi_success_count', 'capi_failure_count']


@admin.register(MetaDailyInsights)
class MetaDailyInsightsAdmin(admin.ModelAdmin):
    list_display = ['insight_date', 'campaign_name', 'spend', 'impressions', 'clicks', 'messaging_conversations_started', 'meta_leads', 'meta_purchases']
    list_filter = ['insight_date', 'campaign_name']
    search_fields = ['campaign_name', 'campaign_id']
    date_hierarchy = 'insight_date'


@admin.register(CapiEventLog)
class CapiEventLogAdmin(admin.ModelAdmin):
    list_display = ['event_name', 'event_id_short', 'source', 'status', 'retries', 'value', 'created']
    list_filter = ['event_name', 'status', 'source']
    search_fields = ['event_id']
    readonly_fields = ['event_id', 'response_json']

    def event_id_short(self, obj):
        return obj.event_id[:20] + '...' if obj.event_id else '-'
    event_id_short.short_description = 'Event ID'


@admin.register(MarketingDailyRollup)
class MarketingDailyRollupAdmin(admin.ModelAdmin):
    list_display = ['rollup_date', 'leads_total', 'spend_total', 'revenue_total', 'estimated_roas', 'estimated_ads_leads', 'organic_leads']
    date_hierarchy = 'rollup_date'
