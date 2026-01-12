import re
import uuid
from django.utils import timezone
from django.db.models import Sum, Count, Avg, F, Q
from datetime import timedelta
from decimal import Decimal

from master.models import Customer, Order
from .models import (
    Lead, LeadActivity, WhatsAppProvider, WhatsAppTemplate,
    Campaign, CampaignRecipient, MessageLog, DoNotMessage, GeoMarketStats
)


class LeadService:
    """Service for lead management and Google Contacts sync."""
    
    @staticmethod
    def normalize_phone(phone):
        """Normalize phone to E.164 format."""
        if not phone:
            return None
        # Remove all non-digits
        digits = re.sub(r'\D', '', phone)
        # Handle Indian numbers
        if len(digits) == 10:
            return f'+91{digits}'
        elif len(digits) == 12 and digits.startswith('91'):
            return f'+{digits}'
        elif len(digits) == 11 and digits.startswith('0'):
            return f'+91{digits[1:]}'
        elif digits.startswith('+'):
            return phone
        return f'+{digits}' if len(digits) > 10 else None
    
    @staticmethod
    def sync_google_contact(contact_data, config):
        """Sync a Google contact to Lead (not Customer)."""
        phone = contact_data.get('phone')
        if not phone:
            return None, 'no_phone'
        
        normalized_phone = LeadService.normalize_phone(phone)
        
        # Check if lead exists
        lead = Lead.objects.filter(
            Q(phone_no=phone) | Q(phone_normalized=normalized_phone)
        ).first()
        
        if lead:
            # Update existing lead
            lead.last_synced_at = timezone.now()
            if contact_data.get('name') and not lead.original_google_name:
                lead.original_google_name = contact_data.get('name')
            lead.google_resource_name = contact_data.get('resource_name')
            lead.save()
            
            LeadActivity.objects.create(
                lead=lead,
                activity_type='synced',
                description='Contact re-synced from Google',
                metadata=contact_data
            )
            
            return lead, 'updated'
        
        # Create new lead
        lead = Lead.objects.create(
            phone_no=phone,
            phone_normalized=normalized_phone,
            name=contact_data.get('name'),
            original_google_name=contact_data.get('name'),
            email=contact_data.get('email'),
            address=contact_data.get('address'),
            city=contact_data.get('city'),
            state=contact_data.get('state'),
            pincode=contact_data.get('pincode'),
            google_resource_name=contact_data.get('resource_name'),
            google_sync_config=config,
            source_device=contact_data.get('source_device'),
            source_user=contact_data.get('source_user'),
        )
        
        LeadActivity.objects.create(
            lead=lead,
            activity_type='synced',
            description='New contact synced from Google',
            metadata=contact_data
        )
        
        # Match lead
        LeadService.match_lead(lead)
        
        return lead, 'created'
    
    @staticmethod
    def match_lead(lead):
        """Match lead against existing Customers and Orders."""
        phone = lead.phone_normalized or lead.phone_no
        
        # Try to match with Customer
        customer = Customer.objects.filter(
            Q(phone_no=phone) | Q(phone_no=lead.phone_no)
        ).first()
        
        # Try to match with Order
        order = Order.objects.filter(
            Q(customer__phone_no=phone) | Q(customer__phone_no=lead.phone_no)
        ).first()
        
        if customer or order:
            lead.match_status = 'win'
            lead.matched_customer = customer
            lead.matched_order = order
            
            # Update lead name from ERP if better
            if customer and customer.customer_name and customer.customer_name != lead.name:
                old_name = lead.name
                lead.name = customer.customer_name
                
                LeadActivity.objects.create(
                    lead=lead,
                    activity_type='name_updated',
                    description=f'Name updated from "{old_name}" to "{customer.customer_name}" based on customer match',
                    metadata={'old_name': old_name, 'new_name': customer.customer_name}
                )
            
            # Compute metrics from matched customer
            if customer:
                LeadService.compute_lead_metrics(lead, customer)
        else:
            lead.match_status = 'loss'
        
        lead.save()
        return lead
    
    @staticmethod
    def compute_lead_metrics(lead, customer=None):
        """Compute metrics for a lead based on order history."""
        phone = lead.phone_normalized or lead.phone_no
        
        orders = Order.objects.filter(
            Q(customer__phone_no=phone) | Q(customer__phone_no=lead.phone_no),
            is_active=True
        )
        
        agg = orders.aggregate(
            count=Count('id'),
            revenue=Sum('total_amount'),
            first_date=models.Min('created'),
            last_date=models.Max('created')
        )
        
        lead.lifetime_order_count = agg['count'] or 0
        lead.lifetime_revenue = agg['revenue'] or Decimal('0')
        lead.first_order_date = agg['first_date'].date() if agg['first_date'] else None
        lead.last_order_date = agg['last_date'].date() if agg['last_date'] else None
        
        # Channel analysis
        channels = orders.values('channel__channel_type').annotate(count=Count('id')).order_by('-count')
        if channels:
            lead.primary_channel = channels[0]['channel__channel_type']
            lead.channels_used = list(set([c['channel__channel_type'] for c in channels]))
        
        # Compute segments
        lead.order_behavior_segment = LeadService._compute_order_behavior(lead)
        lead.lifecycle_stage = LeadService._compute_lifecycle(lead)
        lead.value_tier = LeadService._compute_value_tier(lead)
        lead.risk_status = LeadService._compute_risk_status(lead)
        
        lead.save()
    
    @staticmethod
    def _compute_order_behavior(lead):
        count = lead.lifetime_order_count
        if count == 0:
            return 'non_ordered'
        elif count == 1:
            # Check if old buyer
            if lead.last_order_date and (timezone.now().date() - lead.last_order_date).days > 180:
                return 'one_time_old'
            return 'new_buyer'
        elif count <= 3:
            return 'repeat_buyer'
        elif count <= 6:
            return 'loyal_bronze'
        elif count <= 10:
            return 'loyal_silver'
        else:
            return 'loyal_gold'
    
    @staticmethod
    def _compute_lifecycle(lead):
        if lead.lifetime_order_count == 0:
            return 'prospect'
        
        if not lead.last_order_date:
            return 'unknown'
        
        days = (timezone.now().date() - lead.last_order_date).days
        
        if days <= 30:
            return 'active' if lead.lifetime_order_count >= 2 else 'new'
        elif days <= 60:
            return 'engaged'
        elif days <= 90:
            return 'at_risk'
        elif days <= 180:
            return 'dropped'
        else:
            return 'churned'
    
    @staticmethod
    def _compute_value_tier(lead):
        revenue = float(lead.lifetime_revenue)
        if revenue >= 10000:
            return 'high'
        elif revenue >= 3000:
            return 'medium'
        elif revenue > 0:
            return 'low'
        return 'none'
    
    @staticmethod
    def _compute_risk_status(lead):
        if lead.lifecycle_stage in ['at_risk', 'dropped']:
            return 'high_risk'
        elif lead.lifecycle_stage == 'churned':
            return 'churned'
        return 'healthy'
    
    @staticmethod
    def convert_lead_to_customer(lead, user=None):
        """Convert a lead to customer when they place first order."""
        lead.lead_status = 'converted'
        lead.conversion_date = timezone.now().date()
        lead.save()
        
        LeadActivity.objects.create(
            lead=lead,
            activity_type='converted',
            description='Lead converted to customer (first order placed)',
            performed_by=user
        )
        
        return lead


class WhatsAppService:
    """Service for WhatsApp messaging (mock implementation)."""
    
    @staticmethod
    def send_message(provider, phone_no, template, variables=None):
        """Send a WhatsApp message (mock)."""
        # Check do-not-message list
        if DoNotMessage.objects.filter(phone_no=phone_no).exists():
            return {'success': False, 'error': 'Phone is in do-not-message list'}
        
        # Create message log
        log = MessageLog.objects.create(
            provider=provider,
            template=template,
            message_type='notification',
            phone_no=phone_no,
            variables_used=variables or {},
            status='sent',
            message_id=f"wamid.{uuid.uuid4().hex}",
            sent_at=timezone.now()
        )
        
        # Mock: Update provider counter
        provider.messages_sent_today = F('messages_sent_today') + 1
        provider.save()
        
        return {
            'success': True,
            'message_id': log.message_id,
            'log_id': str(log.id)
        }
    
    @staticmethod
    def send_campaign_message(campaign, recipient):
        """Send a campaign message to a recipient."""
        result = WhatsAppService.send_message(
            campaign.provider,
            recipient.phone_no,
            campaign.template,
            campaign.audience_filters.get('variables', {})
        )
        
        if result['success']:
            recipient.status = 'sent'
            recipient.message_id = result['message_id']
            recipient.sent_at = timezone.now()
        else:
            recipient.status = 'failed'
            recipient.error_message = result.get('error')
        
        recipient.save()
        return result
    
    @staticmethod
    def test_provider_connection(provider):
        """Test WhatsApp provider connection (mock)."""
        provider.last_test_at = timezone.now()
        provider.last_test_result = 'Connection successful (MOCK)'
        provider.status = 'connected'
        provider.save()
        
        return {
            'success': True,
            'message': 'Connection test passed (MOCK)',
            'provider_type': provider.provider_type
        }


class CampaignService:
    """Service for campaign management."""
    
    @staticmethod
    def build_audience(filters):
        """Build audience queryset based on filters."""
        qs = Lead.objects.filter(is_active=True, whatsapp_opt_in=True)
        
        # Exclude do-not-message
        dnm_phones = DoNotMessage.objects.values_list('phone_no', flat=True)
        qs = qs.exclude(phone_no__in=dnm_phones)
        
        # Apply filters
        if filters.get('match_status'):
            qs = qs.filter(match_status=filters['match_status'])
        
        if filters.get('lead_status'):
            qs = qs.filter(lead_status__in=filters['lead_status'])
        
        if filters.get('lifecycle_stage'):
            qs = qs.filter(lifecycle_stage__in=filters['lifecycle_stage'])
        
        if filters.get('value_tier'):
            qs = qs.filter(value_tier__in=filters['value_tier'])
        
        if filters.get('order_behavior'):
            qs = qs.filter(order_behavior_segment__in=filters['order_behavior'])
        
        if filters.get('states'):
            qs = qs.filter(state__in=filters['states'])
        
        if filters.get('pincodes'):
            qs = qs.filter(pincode__in=filters['pincodes'])
        
        return qs
    
    @staticmethod
    def create_campaign_recipients(campaign):
        """Create recipients for a campaign based on audience filters."""
        leads = CampaignService.build_audience(campaign.audience_filters)
        
        recipients = []
        for lead in leads:
            recipients.append(CampaignRecipient(
                campaign=campaign,
                lead=lead,
                phone_no=lead.phone_no
            ))
        
        CampaignRecipient.objects.bulk_create(recipients, ignore_conflicts=True)
        
        campaign.total_recipients = len(recipients)
        campaign.audience_count = len(recipients)
        campaign.save()
        
        return len(recipients)
    
    @staticmethod
    def track_conversion(campaign, order):
        """Track if an order is attributed to a campaign."""
        if not campaign.completed_at:
            return False
        
        # Check if within attribution window
        days_since = (timezone.now() - campaign.completed_at).days
        if days_since > campaign.attribution_window_days:
            return False
        
        # Check if recipient exists
        recipient = CampaignRecipient.objects.filter(
            campaign=campaign,
            phone_no=order.customer.phone_no
        ).first()
        
        if recipient and not recipient.converted:
            recipient.converted = True
            recipient.conversion_order = order
            recipient.save()
            
            campaign.conversions = F('conversions') + 1
            campaign.conversion_revenue = F('conversion_revenue') + order.total_amount
            campaign.save()
            
            return True
        
        return False


class MarketInsightsService:
    """Service for geo market analytics."""
    
    @staticmethod
    def compute_geo_stats(period_type='all_time', period_date=None):
        """Compute geographic market statistics."""
        from django.db.models import Min, Max
        
        if period_date is None:
            period_date = timezone.now().date()
        
        # Get unique states
        states = Lead.objects.filter(is_active=True, state__isnull=False).values_list('state', flat=True).distinct()
        
        for state in states:
            leads = Lead.objects.filter(state=state, is_active=True)
            orders = Order.objects.filter(customer__state=state, is_active=True)
            
            stats, created = GeoMarketStats.objects.update_or_create(
                state=state,
                district=None,
                pincode=None,
                period_type=period_type,
                period_date=period_date,
                defaults={
                    'leads_count': leads.count(),
                    'win_count': leads.filter(match_status='win').count(),
                    'loss_count': leads.filter(match_status='loss').count(),
                    'orders_count': orders.count(),
                    'revenue': orders.aggregate(total=Sum('total_amount'))['total'] or 0,
                    'cod_orders': orders.filter(cod_charge__gt=0).count(),
                    'prepaid_orders': orders.filter(cod_charge=0).count(),
                    'first_order_date': orders.aggregate(first=Min('created'))['first'],
                }
            )
            
            # Calculate derived metrics
            if stats.leads_count > 0:
                stats.conversion_rate = (stats.win_count / stats.leads_count) * 100
            if stats.orders_count > 0:
                stats.cod_share = (stats.cod_orders / stats.orders_count) * 100
            
            # Categorize market
            stats.market_category = MarketInsightsService._categorize_market(stats)
            stats.save()
        
        return GeoMarketStats.objects.filter(period_type=period_type, period_date=period_date)
    
    @staticmethod
    def _categorize_market(stats):
        """Categorize a market based on metrics."""
        # Hot market: High orders and revenue
        if stats.orders_count >= 50 and float(stats.revenue) >= 50000:
            return 'hot'
        
        # Cold/Loss market: High leads but low conversion
        if stats.leads_count >= 50 and stats.conversion_rate < 10:
            return 'cold'
        
        # New market: First order within last 30 days
        if stats.first_order_date:
            days_since_first = (timezone.now().date() - stats.first_order_date.date() if hasattr(stats.first_order_date, 'date') else timezone.now().date() - stats.first_order_date).days
            if days_since_first <= 30:
                return 'new'
        
        # High RTO market
        if stats.rto_rate >= 20:
            return 'high_rto'
        
        return None
    
    @staticmethod
    def get_hotspot_markets(limit=10):
        """Get top performing markets."""
        return GeoMarketStats.objects.filter(
            period_type='all_time',
            market_category='hot'
        ).order_by('-revenue')[:limit]
    
    @staticmethod
    def get_cold_markets(limit=10):
        """Get underperforming markets with high leads."""
        return GeoMarketStats.objects.filter(
            period_type='all_time',
            market_category='cold'
        ).order_by('-leads_count')[:limit]
    
    @staticmethod
    def get_new_markets(days=30, limit=10):
        """Get newly opened markets."""
        cutoff_date = timezone.now().date() - timedelta(days=days)
        return GeoMarketStats.objects.filter(
            period_type='all_time',
            first_order_date__gte=cutoff_date
        ).order_by('-first_order_date')[:limit]


# Import models for type hints
from django.db import models
