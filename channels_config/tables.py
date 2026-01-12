from django_tables2 import columns
from core.base import BaseTable
from .models import DynamicChannel, ChannelFormField


class DynamicChannelTable(BaseTable):
    name = columns.Column(linkify=True)
    code = columns.Column()
    prefix = columns.Column()
    is_cod_channel = columns.BooleanColumn(verbose_name="COD")
    requires_utr = columns.BooleanColumn(verbose_name="UTR Required")
    sort_order = columns.Column(verbose_name="Order")
    
    class Meta:
        model = DynamicChannel
        fields = ['name', 'code', 'prefix', 'is_cod_channel', 'requires_utr', 'sort_order', 'created']
        attrs = {'class': 'table table-striped table-bordered'}


class ChannelFormFieldTable(BaseTable):
    channel = columns.Column(linkify=lambda record: record.channel.get_absolute_url())
    field_name = columns.Column()
    label = columns.Column()
    field_type = columns.Column()
    is_required = columns.BooleanColumn()
    is_visible = columns.BooleanColumn()
    sort_order = columns.Column(verbose_name="Order")
    
    class Meta:
        model = ChannelFormField
        fields = ['channel', 'field_name', 'label', 'field_type', 'is_required', 'is_visible', 'sort_order']
        attrs = {'class': 'table table-striped table-bordered'}
