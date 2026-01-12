from django.contrib import admin
from .models import (
    Lead, LeadActivity, WhatsAppProvider, WhatsAppTemplate,
    NotificationEvent, Campaign, CampaignRecipient, MessageLog,
    DoNotMessage, GeoMarketStats
)


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone_no', 'match_status', 'lead_status', 'state', 'city', 'assigned_to', 'created']
    list_filter = ['match_status', 'lead_status', 'state', 'whatsapp_opt_in']
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
