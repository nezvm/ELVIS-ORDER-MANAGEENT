from django.contrib import admin
from .models import (
    WhatsAppCustomer, 
    WhatsAppNumberConfig, 
    WhatsAppCustomerChannel, 
    WhatsAppMessage,
    WhatsAppWebhookLog
)


@admin.register(WhatsAppCustomer)
class WhatsAppCustomerAdmin(admin.ModelAdmin):
    list_display = [
        'wa_id', 'profile_name', 'total_messages', 
        'total_channels_contacted', 'last_seen', 'assigned_sales_user'
    ]
    list_filter = ['assigned_sales_user', 'created']
    search_fields = ['wa_id', 'profile_name']
    readonly_fields = ['id', 'created', 'modified', 'first_seen', 'last_seen']
    raw_id_fields = ['linked_customer', 'linked_lead', 'assigned_sales_user']
    
    fieldsets = (
        ('Customer Info', {
            'fields': ('wa_id', 'profile_name')
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
            'fields': ('id', 'created', 'modified', 'is_active'),
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
    readonly_fields = ['id', 'created', 'modified', 'last_webhook_at', 'webhook_count']


@admin.register(WhatsAppCustomerChannel)
class WhatsAppCustomerChannelAdmin(admin.ModelAdmin):
    list_display = [
        'customer', 'phone_number_id', 'message_count', 
        'first_contact_at', 'last_contact_at'
    ]
    list_filter = ['phone_number_id']
    search_fields = ['customer__wa_id', 'customer__profile_name']
    readonly_fields = ['id', 'created', 'modified', 'first_contact_at', 'last_contact_at']
    raw_id_fields = ['customer', 'number_config']


@admin.register(WhatsAppMessage)
class WhatsAppMessageAdmin(admin.ModelAdmin):
    list_display = [
        'customer', 'direction', 'msg_type', 'phone_number_id', 
        'timestamp_utc', 'body_preview'
    ]
    list_filter = ['direction', 'msg_type', 'phone_number_id']
    search_fields = ['customer__wa_id', 'body', 'message_id']
    readonly_fields = ['id', 'created', 'modified', 'message_id', 'timestamp_utc']
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
    readonly_fields = ['id', 'created', 'modified', 'payload']
    
    def has_add_permission(self, request):
        return False
