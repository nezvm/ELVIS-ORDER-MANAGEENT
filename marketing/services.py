import re
import uuid
from django.utils import timezone
from django.db.models import Sum, Count, Avg, F, Q, Min, Max
from datetime import timedelta
from decimal import Decimal

from master.models import Customer, Order
from .models import (
    Lead, LeadActivity, WhatsAppProvider, WhatsAppTemplate,
    Campaign, CampaignRecipient, MessageLog, DoNotMessage, GeoMarketStats,
    PincodeMaster, OrderMarketStats, LeadMarketStats, AbandonedMetrics
)


class LeadService:
    """Service for lead management, Google Contacts sync, and Shopify abandoned checkout."""
    
    @staticmethod
    def normalize_phone(phone):
        """Normalize phone to E.164 format."""
        if not phone:
            return None
        # Remove all non-digits except leading +
        phone_clean = phone.strip()
        if phone_clean.startswith('+'):
            digits = '+' + re.sub(r'\D', '', phone_clean[1:])
        else:
            digits = re.sub(r'\D', '', phone_clean)
        
        # Handle Indian numbers
        if len(digits) == 10 and digits.isdigit():
            return f'+91{digits}'
        elif len(digits) == 12 and digits.startswith('91'):
            return f'+{digits}'
        elif len(digits) == 11 and digits.startswith('0'):
            return f'+91{digits[1:]}'
        elif digits.startswith('+') and len(digits) > 10:
            return digits
        elif len(digits) > 10:
            return f'+{digits}'
        return None
    
    @staticmethod
    def normalize_email(email):
        """Normalize email to lowercase trimmed."""
        if not email:
            return None
        return email.strip().lower()
    
    @staticmethod
    def enrich_location_from_pincode(lead):
        """Auto-fill state + district from pincode using PincodeMaster."""
        if not lead.pincode:
            lead.location_status = 'unknown'
            return lead
        
        pincode_data = PincodeMaster.objects.filter(pincode=lead.pincode).first()
        if pincode_data:
            lead.state = pincode_data.state
            lead.district = pincode_data.district
            lead.city = pincode_data.city or lead.city
            lead.location_status = 'enriched'
        else:
            # If we have pincode but no mapping, still consider it enriched if state is set
            if lead.state:
                lead.location_status = 'enriched'
            else:
                lead.location_status = 'unknown'
        
        return lead
    
    @staticmethod
    def find_existing_lead(phone=None, email=None, source_ref_id=None, lead_source=None):
        """Find existing lead by phone, email, or source reference."""
        # Priority 1: Exact source_ref_id match for same lead_source
        if source_ref_id and lead_source:
            lead = Lead.objects.filter(
                source_ref_id=source_ref_id,
                lead_source=lead_source
            ).first()
            if lead:
                return lead
        
        # Priority 2: Phone match
        if phone:
            normalized_phone = LeadService.normalize_phone(phone)
            lead = Lead.objects.filter(
                Q(phone_no=phone) | Q(phone_normalized=normalized_phone)
            ).first()
            if lead:
                return lead
        
        # Priority 3: Email match
        if email:
            normalized_email = LeadService.normalize_email(email)
            lead = Lead.objects.filter(
                Q(email=email) | Q(email_normalized=normalized_email)
            ).first()
            if lead:
                return lead
        
        return None
    
    @staticmethod
    def match_with_customer_or_order(phone=None, email=None):
        """Check if phone/email matches existing Customer or Order. Returns (customer, order, is_match)"""
        customer = None
        order = None
        
        # Match by phone
        if phone:
            normalized_phone = LeadService.normalize_phone(phone)
            customer = Customer.objects.filter(
                Q(phone_no=phone) | Q(phone_no=normalized_phone)
            ).first()
            if not customer:
                order = Order.objects.filter(
                    Q(customer__phone_no=phone) | Q(customer__phone_no=normalized_phone)
                ).first()
        
        # Match by email (if no phone match)
        if not customer and not order and email:
            normalized_email = LeadService.normalize_email(email)
            # Customer model doesn't have email in the given schema, so skip
            pass
        
        return customer, order, bool(customer or order)
    
    @staticmethod
    def sync_google_contact(contact_data, config):
        """Sync a Google contact to Lead (not Customer)."""
        phone = contact_data.get('phone')
        email = contact_data.get('email')
        
        if not phone and not email:
            return None, 'no_identity'
        
        normalized_phone = LeadService.normalize_phone(phone)
        normalized_email = LeadService.normalize_email(email)
        
        # Find existing lead
        lead = LeadService.find_existing_lead(phone=phone, email=email)
        
        if lead:
            # Update existing lead
            lead.last_synced_at = timezone.now()
            if contact_data.get('name') and not lead.original_google_name:
                lead.original_google_name = contact_data.get('name')
            lead.google_resource_name = contact_data.get('resource_name')
            lead.lead_source = 'google_contacts_sync'
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
            email=email,
            email_normalized=normalized_email,
            name=contact_data.get('name'),
            original_google_name=contact_data.get('name'),
            address=contact_data.get('address'),
            city=contact_data.get('city'),
            state=contact_data.get('state'),
            pincode=contact_data.get('pincode'),
            google_resource_name=contact_data.get('resource_name'),
            google_sync_config=config,
            source_device=contact_data.get('source_device'),
            source_user=contact_data.get('source_user'),
            lead_source='google_contacts_sync',
            captured_at=timezone.now(),
            needs_phone=not bool(phone),
        )
        
        # Enrich location
        lead = LeadService.enrich_location_from_pincode(lead)
        lead.save()
        
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
    def sync_shopify_abandoned_checkout(checkout_data, store):
        """Sync a Shopify abandoned checkout to Lead."""
        from integrations.models import ShopifyStore
        
        checkout_id = checkout_data.get('id') or checkout_data.get('checkout_id')
        customer_data = checkout_data.get('customer', {})
        shipping_address = checkout_data.get('shipping_address', {})
        
        phone = customer_data.get('phone') or shipping_address.get('phone')
        email = customer_data.get('email')
        name = customer_data.get('name') or f"{shipping_address.get('first_name', '')} {shipping_address.get('last_name', '')}".strip()
        
        if not phone and not email:
            return None, 'no_identity'
        
        normalized_phone = LeadService.normalize_phone(phone)
        normalized_email = LeadService.normalize_email(email)
        
        # Find existing lead
        lead = LeadService.find_existing_lead(
            phone=phone,
            email=email,
            source_ref_id=str(checkout_id),
            lead_source='shopify_abandoned_checkout'
        )
        
        # Extract cart items
        cart_items = []
        cart_value = Decimal('0')
        line_items = checkout_data.get('line_items', [])
        for item in line_items:
            cart_items.append({
                'title': item.get('title'),
                'quantity': item.get('quantity'),
                'price': item.get('price')
            })
        
        total_price = checkout_data.get('total_price') or checkout_data.get('subtotal_price')
        if total_price:
            cart_value = Decimal(str(total_price))
        
        # Location data
        pincode = shipping_address.get('zip') or shipping_address.get('postal_code')
        city = shipping_address.get('city')
        state = shipping_address.get('province') or shipping_address.get('state')
        address = shipping_address.get('address1', '')
        
        if lead:
            # Update existing lead
            lead.cart_value = cart_value
            lead.cart_items_summary = cart_items
            lead.recover_url = checkout_data.get('abandoned_checkout_url') or checkout_data.get('recovery_url')
            lead.abandoned_at = checkout_data.get('created_at') or checkout_data.get('abandoned_at')
            lead.source_payload = checkout_data
            lead.last_synced_at = timezone.now()
            
            # Update location if better data
            if pincode and not lead.pincode:
                lead.pincode = pincode
                lead = LeadService.enrich_location_from_pincode(lead)
            
            lead.save()
            
            LeadActivity.objects.create(
                lead=lead,
                activity_type='synced',
                description='Abandoned checkout updated from Shopify',
                metadata={'checkout_id': checkout_id, 'cart_value': str(cart_value)}
            )
            
            return lead, 'updated'
        
        # Create new lead
        lead = Lead.objects.create(
            phone_no=phone,
            phone_normalized=normalized_phone,
            email=email,
            email_normalized=normalized_email,
            name=name,
            address=address,
            city=city,
            state=state,
            pincode=pincode,
            lead_source='shopify_abandoned_checkout',
            source_ref_id=str(checkout_id),
            source_payload=checkout_data,
            captured_at=timezone.now(),
            needs_phone=not bool(phone),
            recover_url=checkout_data.get('abandoned_checkout_url') or checkout_data.get('recovery_url'),
            cart_value=cart_value,
            cart_items_summary=cart_items,
            abandoned_at=checkout_data.get('created_at'),
            shopify_store=store,
        )
        
        # Enrich location
        lead = LeadService.enrich_location_from_pincode(lead)
        lead.save()
        
        LeadActivity.objects.create(
            lead=lead,
            activity_type='synced',
            description='New abandoned checkout synced from Shopify',
            metadata={'checkout_id': checkout_id, 'cart_value': str(cart_value)}
        )
        
        # Match lead with WIN/LOSS
        LeadService.match_lead(lead)
        
        return lead, 'created'
    
    @staticmethod
    def match_lead(lead):
        """Match lead against existing Customers and Orders. Sets WIN/LOSS status."""
        phone = lead.phone_normalized or lead.phone_no
        email = lead.email_normalized or lead.email
        
        customer, order, is_match = LeadService.match_with_customer_or_order(phone, email)
        
        if is_match:
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
    def track_conversion(lead, order):
        """Track when an abandoned lead converts to an order."""
        if lead.match_status == 'converted':
            return False  # Already converted
        
        lead.match_status = 'converted'
        lead.converted_order = order
        
        # Calculate conversion days
        base_date = lead.abandoned_at or lead.captured_at or lead.created
        if base_date:
            if hasattr(base_date, 'date'):
                base_date = base_date.date() if hasattr(base_date, 'date') else base_date
            order_date = order.created.date() if hasattr(order.created, 'date') else order.created
            lead.conversion_days = (order_date - base_date).days if isinstance(base_date, type(order_date)) else None
        
        lead.lead_status = 'converted'
        lead.save()
        
        LeadActivity.objects.create(
            lead=lead,
            activity_type='converted',
            description=f'Lead converted - Order placed (#{order.order_no})',
            metadata={'order_id': str(order.id), 'order_no': order.order_no}
        )
        
        return True
    
    @staticmethod
    def check_order_for_lead_conversion(order):
        """Check if a new order matches any abandoned leads and track conversion."""
        phone = order.customer.phone_no
        normalized_phone = LeadService.normalize_phone(phone)
        
        # Find matching abandoned leads
        leads = Lead.objects.filter(
            Q(phone_no=phone) | Q(phone_normalized=normalized_phone),
            lead_source__in=['shopify_abandoned_checkout', 'shopify_abandoned_cart'],
            match_status__in=['loss', 'pending', 'win']  # Not already converted
        )
        
        converted_count = 0
        for lead in leads:
            if LeadService.track_conversion(lead, order):
                converted_count += 1
        
        return converted_count
    
    @staticmethod
    def compute_lead_metrics(lead, customer=None):
        """Compute metrics for a lead based on order history."""
        phone = lead.phone_normalized or lead.phone_no
        
        orders = Order.objects.filter(
            Q(customer__phone_no=phone) | Q(customer__phone_no=lead.phone_no),
            is_active=True
        )
        
        from django.db import models as db_models
        agg = orders.aggregate(
            count=Count('id'),
            revenue=Sum('total_amount'),
            first_date=Min('created'),
            last_date=Max('created')
        )
        
        lead.lifetime_order_count = agg['count'] or 0
        lead.lifetime_revenue = agg['revenue'] or Decimal('0')
        lead.first_order_date = agg['first_date'].date() if agg['first_date'] else None
        lead.last_order_date = agg['last_date'].date() if agg['last_date'] else None
        
        # Channel analysis
        channels = orders.values('channel__channel_type').annotate(count=Count('id')).order_by('-count')
        if channels:
            lead.primary_channel = channels[0]['channel__channel_type']
            lead.channels_used = list(set([c['channel__channel_type'] for c in channels if c['channel__channel_type']]))
        
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
    
    @staticmethod
    def get_unknown_location_stats():
        """Get stats about leads with unknown location."""
        total_leads = Lead.objects.filter(is_active=True).count()
        unknown_leads = Lead.objects.filter(
            Q(location_status='unknown') | Q(pincode__isnull=True) | Q(pincode=''),
            is_active=True
        ).count()
        
        percentage = (unknown_leads / total_leads * 100) if total_leads > 0 else 0
        
        return {
            'total_leads': total_leads,
            'unknown_leads': unknown_leads,
            'unknown_percentage': round(percentage, 1)
        }


class WhatsAppService:
    """Service for WhatsApp messaging (mock implementation)."""
    
    @staticmethod
    def send_message(provider, phone_no, template, variables=None, lead=None):
        """Send a WhatsApp message (mock)."""
        # Check do-not-message list
        if DoNotMessage.objects.filter(phone_no=phone_no).exists():
            return {'success': False, 'error': 'Phone is in do-not-message list'}
        
        # Check if lead has recover_url for abandoned recovery
        message_content = template.body
        if variables and '{{recover_url}}' in message_content and lead:
            if not lead.recover_url:
                return {'success': False, 'error': 'Missing recover link', 'skip_reason': 'missing_recover_link'}
        
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
        # Build variables with lead data
        variables = campaign.audience_filters.get('variables', {})
        
        # For abandoned recovery, include recover_url
        if campaign.campaign_type == 'abandoned_recovery' and recipient.lead:
            variables['recover_url'] = recipient.lead.recover_url or ''
            variables['cart_value'] = str(recipient.lead.cart_value)
        
        result = WhatsAppService.send_message(
            campaign.provider,
            recipient.phone_no,
            campaign.template,
            variables,
            lead=recipient.lead
        )
        
        if result['success']:
            recipient.status = 'sent'
            recipient.message_id = result['message_id']
            recipient.sent_at = timezone.now()
        else:
            recipient.status = 'failed'
            recipient.error_message = result.get('error')
            recipient.error_code = result.get('skip_reason')
        
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
    def build_audience(filters, campaign_type='broadcast'):
        """Build audience queryset based on filters and campaign type."""
        qs = Lead.objects.filter(is_active=True, whatsapp_opt_in=True)
        
        # Exclude do-not-message
        dnm_phones = DoNotMessage.objects.values_list('phone_no', flat=True)
        qs = qs.exclude(phone_no__in=dnm_phones)
        
        # Exclude leads without phone
        qs = qs.exclude(Q(phone_no__isnull=True) | Q(phone_no=''))
        
        # Campaign type specific filters
        if campaign_type == 'abandoned_recovery':
            qs = qs.filter(
                lead_source__in=['shopify_abandoned_checkout', 'shopify_abandoned_cart'],
                match_status__in=['loss', 'pending']  # Not converted
            )
        
        # Apply custom filters
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
        
        if filters.get('lead_source'):
            qs = qs.filter(lead_source__in=filters['lead_source'])
        
        return qs
    
    @staticmethod
    def create_campaign_recipients(campaign):
        """Create recipients for a campaign based on audience filters."""
        leads = CampaignService.build_audience(
            campaign.audience_filters,
            campaign.campaign_type
        )
        
        # For abandoned recovery, only include leads with recover_url
        if campaign.campaign_type == 'abandoned_recovery':
            leads = leads.exclude(Q(recover_url__isnull=True) | Q(recover_url=''))
        
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
    def stop_followups_for_converted_lead(lead):
        """Stop pending campaign messages for a converted lead."""
        # Find pending messages in abandoned recovery campaigns
        CampaignRecipient.objects.filter(
            lead=lead,
            campaign__campaign_type='abandoned_recovery',
            campaign__stop_on_conversion=True,
            status='queued'
        ).update(status='opted_out', error_message='Lead converted - followups stopped')
    
    @staticmethod
    def track_conversion(campaign, order):
        """Track if an order is attributed to a campaign."""
        if not campaign.completed_at:
            return False
        
        days_since = (timezone.now() - campaign.completed_at).days
        if days_since > campaign.attribution_window_days:
            return False
        
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
    """Service for geo market analytics with separate Order vs Lead tabs."""
    
    @staticmethod
    def compute_order_market_stats(period_type='all_time', period_date=None):
        """Compute Order-based market stats from shipping address pincode."""
        if period_date is None:
            period_date = timezone.now().date()
        
        # Group orders by customer state (from shipping address)
        orders = Order.objects.filter(is_active=True).select_related('customer')
        
        state_data = {}
        for order in orders:
            state = order.customer.state
            if not state:
                continue
            
            state = state.strip().upper()
            if state not in state_data:
                state_data[state] = {
                    'orders': [],
                    'customers': set()
                }
            state_data[state]['orders'].append(order)
            state_data[state]['customers'].add(order.customer.id)
        
        for state, data in state_data.items():
            orders_list = data['orders']
            total_orders = len(orders_list)
            revenue = sum(o.total_amount for o in orders_list)
            cod_orders = len([o for o in orders_list if o.cod_charge > 0])
            prepaid_orders = total_orders - cod_orders
            unique_customers = len(data['customers'])
            
            # Find first order date
            first_order = min(orders_list, key=lambda o: o.created, default=None)
            first_order_date = first_order.created.date() if first_order else None
            
            stats, _ = OrderMarketStats.objects.update_or_create(
                state=state,
                district=None,
                pincode=None,
                period_type=period_type,
                period_date=period_date,
                defaults={
                    'orders_count': total_orders,
                    'revenue': revenue,
                    'cod_orders': cod_orders,
                    'prepaid_orders': prepaid_orders,
                    'cod_share': (cod_orders / total_orders * 100) if total_orders > 0 else 0,
                    'unique_customers': unique_customers,
                    'first_order_date': first_order_date,
                }
            )
            
            # Categorize
            stats.market_category = MarketInsightsService._categorize_order_market(stats)
            stats.save()
        
        return OrderMarketStats.objects.filter(period_type=period_type, period_date=period_date)
    
    @staticmethod
    def compute_lead_market_stats(period_type='all_time', period_date=None):
        """Compute Lead-based market stats (enriched locations only)."""
        if period_date is None:
            period_date = timezone.now().date()
        
        # Only use leads with enriched location
        leads = Lead.objects.filter(
            is_active=True,
            state__isnull=False
        ).exclude(
            location_status='unknown'
        ).exclude(
            Q(state='') | Q(state__isnull=True)
        )
        
        state_data = {}
        for lead in leads:
            state = lead.state.strip().upper()
            if state not in state_data:
                state_data[state] = {'leads': []}
            state_data[state]['leads'].append(lead)
        
        for state, data in state_data.items():
            leads_list = data['leads']
            total_leads = len(leads_list)
            win_count = len([l for l in leads_list if l.match_status == 'win'])
            loss_count = len([l for l in leads_list if l.match_status == 'loss'])
            converted_count = len([l for l in leads_list if l.match_status == 'converted'])
            
            stats, _ = LeadMarketStats.objects.update_or_create(
                state=state,
                district=None,
                pincode=None,
                period_type=period_type,
                period_date=period_date,
                defaults={
                    'leads_count': total_leads,
                    'win_count': win_count,
                    'loss_count': loss_count,
                    'converted_count': converted_count,
                    'conversion_rate': (win_count / total_leads * 100) if total_leads > 0 else 0,
                }
            )
            
            # Categorize
            stats.market_category = MarketInsightsService._categorize_lead_market(stats)
            stats.save()
        
        return LeadMarketStats.objects.filter(period_type=period_type, period_date=period_date)
    
    @staticmethod
    def compute_abandoned_metrics(period_type='all_time', period_date=None):
        """Compute abandoned checkout metrics."""
        if period_date is None:
            period_date = timezone.now().date()
        
        abandoned_leads = Lead.objects.filter(
            is_active=True,
            lead_source__in=['shopify_abandoned_checkout', 'shopify_abandoned_cart']
        )
        
        total_abandoned = abandoned_leads.count()
        total_value = abandoned_leads.aggregate(total=Sum('cart_value'))['total'] or 0
        converted = abandoned_leads.filter(match_status='converted')
        converted_count = converted.count()
        
        # Conversion revenue from converted orders
        conversion_revenue = Decimal('0')
        avg_days = 0
        if converted_count > 0:
            days_list = [l.conversion_days for l in converted if l.conversion_days is not None]
            avg_days = sum(days_list) / len(days_list) if days_list else 0
            
            for lead in converted:
                if lead.converted_order:
                    conversion_revenue += lead.converted_order.total_amount
        
        # Top abandoned products
        product_counts = {}
        for lead in abandoned_leads:
            for item in lead.cart_items_summary or []:
                title = item.get('title', 'Unknown')
                qty = item.get('quantity', 1)
                if title not in product_counts:
                    product_counts[title] = {'count': 0, 'value': Decimal('0')}
                product_counts[title]['count'] += qty
                price = Decimal(str(item.get('price', 0))) * qty
                product_counts[title]['value'] += price
        
        top_products = sorted(
            [{'product': k, 'count': v['count'], 'value': float(v['value'])} for k, v in product_counts.items()],
            key=lambda x: x['count'],
            reverse=True
        )[:10]
        
        metrics, _ = AbandonedMetrics.objects.update_or_create(
            period_type=period_type,
            period_date=period_date,
            state=None,
            defaults={
                'abandoned_count': total_abandoned,
                'abandoned_value': total_value,
                'converted_count': converted_count,
                'conversion_rate': (converted_count / total_abandoned * 100) if total_abandoned > 0 else 0,
                'conversion_revenue': conversion_revenue,
                'avg_conversion_days': avg_days,
                'top_abandoned_products': top_products,
            }
        )
        
        return metrics
    
    @staticmethod
    def _categorize_order_market(stats):
        """Categorize order market based on metrics."""
        if stats.orders_count >= 50 and float(stats.revenue) >= 50000:
            return 'hot'
        
        if stats.first_order_date:
            days_since = (timezone.now().date() - stats.first_order_date).days
            if days_since <= 30:
                return 'new'
        
        if stats.rto_rate >= 20:
            return 'high_rto'
        
        return None
    
    @staticmethod
    def _categorize_lead_market(stats):
        """Categorize lead market based on metrics."""
        if stats.leads_count >= 50 and stats.conversion_rate < 10:
            return 'cold'
        
        if stats.leads_count >= 20 and stats.conversion_rate >= 30:
            return 'hot'
        
        return None
    
    @staticmethod
    def compute_geo_stats(period_type='all_time', period_date=None):
        """Compute all geo stats (legacy method for compatibility)."""
        MarketInsightsService.compute_order_market_stats(period_type, period_date)
        MarketInsightsService.compute_lead_market_stats(period_type, period_date)
        MarketInsightsService.compute_abandoned_metrics(period_type, period_date)
        
        return GeoMarketStats.objects.filter(period_type=period_type)
    
    @staticmethod
    def get_hotspot_markets(limit=10):
        """Get top performing order markets."""
        return OrderMarketStats.objects.filter(
            period_type='all_time',
            market_category='hot'
        ).order_by('-revenue')[:limit]
    
    @staticmethod
    def get_cold_markets(limit=10):
        """Get underperforming lead markets (high leads, low conversion)."""
        return LeadMarketStats.objects.filter(
            period_type='all_time',
            market_category='cold'
        ).order_by('-leads_count')[:limit]
    
    @staticmethod
    def get_new_markets(days=30, limit=10):
        """Get newly opened order markets."""
        cutoff_date = timezone.now().date() - timedelta(days=days)
        return OrderMarketStats.objects.filter(
            period_type='all_time',
            first_order_date__gte=cutoff_date
        ).order_by('-first_order_date')[:limit]
    
    @staticmethod
    def get_loss_markets_by_state(limit=20):
        """Get states with highest abandoned LOSS leads (enriched only)."""
        return LeadMarketStats.objects.filter(
            period_type='all_time',
            loss_count__gt=0
        ).order_by('-loss_count')[:limit]
