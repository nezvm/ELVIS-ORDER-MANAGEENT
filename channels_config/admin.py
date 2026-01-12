from django.contrib import admin
from core.base import BaseAdmin
from .models import DynamicChannel, ChannelFormField, UTRRecord


class ChannelFormFieldInline(admin.TabularInline):
    model = ChannelFormField
    extra = 1
    fields = ['field_name', 'label', 'field_type', 'is_required', 'is_visible', 'sort_order']


@admin.register(DynamicChannel)
class DynamicChannelAdmin(BaseAdmin):
    list_display = ['name', 'code', 'prefix', 'is_cod_channel', 'requires_utr', 'sort_order', 'is_active']
    list_filter = ['is_cod_channel', 'requires_utr', 'is_active']
    search_fields = ['name', 'code', 'prefix']
    inlines = [ChannelFormFieldInline]


@admin.register(ChannelFormField)
class ChannelFormFieldAdmin(BaseAdmin):
    list_display = ['channel', 'field_name', 'label', 'field_type', 'is_required', 'is_visible', 'sort_order']
    list_filter = ['channel', 'field_type', 'is_required', 'is_visible']
    search_fields = ['field_name', 'label']


@admin.register(UTRRecord)
class UTRRecordAdmin(BaseAdmin):
    list_display = ['utr', 'order', 'captured_by', 'captured_at', 'verified', 'verified_by']
    list_filter = ['verified', 'captured_at']
    search_fields = ['utr', 'order__order_no']
    readonly_fields = ['captured_at', 'verified_at']
