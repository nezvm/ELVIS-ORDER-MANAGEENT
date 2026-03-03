"""
Shopify Integration Portal Services

Comprehensive services for the Shopify Integration Portal including:
- Channel split (WEB_PAID / WEB_COD)
- Customer sync (Leads + Customers)
- Fulfillment outbound push
- Abandoned checkout sync
- Event inbox processing
- Real Shopify API calls
"""
import hashlib
import hmac
import base64
import json
import logging
import re
import requests as http_requests
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings

from integrations.models import (
    ShopifyStore, ShopifyOrder, ShopifyAbandonedCheckout,
    ShopifyWebhookLog, ShopifySyncLog, ShopifyExternalMap,
    ShopifyEventInbox, ShopifyOutbox
)
from marketing.models import Lead
from master.models import Customer, Order

logger = logging.getLogger(__name__)


def normalize_phone(phone):
    """Normalize phone number for matching."""
    if not phone:
        return None
    digits = re.sub(r'\D', '', str(phone))
    if len(digits) >= 10:
        return digits[-10:]
    return None


class ShopifyAPIClient:
    """Real Shopify API client using REST Admin API."""
    
    def __init__(self, store: ShopifyStore):
        self.store = store
        self.domain = store.shop_domain
        self.token = store.access_token
        self.version = store.api_version or '2024-01'
        self.base_url = f"https://{self.domain}/admin/api/{self.version}"
        self.headers = {
            'X-Shopify-Access-Token': self.token or '',
            'Content-Type': 'application/json',
        }
    
    def _get(self, endpoint, params=None):
        """Make GET request to Shopify API."""
        url = f"{self.base_url}/{endpoint}"
        try:
            resp = http_requests.get(url, headers=self.headers, params=params, timeout=15)
            return resp.status_code, resp.json() if resp.content else {}
        except Exception as e:
            logger.error(f"Shopify API GET error: {e}")
            return 0, {'error': str(e)}
    
    def _post(self, endpoint, data):
        """Make POST request to Shopify API."""
        url = f"{self.base_url}/{endpoint}"
        try:
            resp = http_requests.post(url, headers=self.headers, json=data, timeout=15)
            return resp.status_code, resp.json() if resp.content else {}
        except Exception as e:
            logger.error(f"Shopify API POST error: {e}")
            return 0, {'error': str(e)}
    
    def get_shop(self):
        """Get shop info."""
        return self._get('shop.json')
    
    def get_order(self, order_id):
        """Get single order."""
        return self._get(f'orders/{order_id}.json')
    
    def get_customer(self, customer_id):
        """Get single customer."""
        return self._get(f'customers/{customer_id}.json')
    
    def get_orders(self, params=None):
        """Get orders list."""
        return self._get('orders.json', params=params)
    
    def get_abandoned_checkouts(self, params=None):
        """Get abandoned checkouts."""
        return self._get('checkouts.json', params=params)
    
    def create_fulfillment(self, order_id, fulfillment_data):
        """Create fulfillment for an order."""
        return self._post(
            f'orders/{order_id}/fulfillments.json',
            {'fulfillment': fulfillment_data}
        )
    
    def update_fulfillment_tracking(self, order_id, fulfillment_id, tracking_data):
        """Update fulfillment tracking."""
        url = f"{self.base_url}/orders/{order_id}/fulfillments/{fulfillment_id}.json"
        try:
            resp = http_requests.put(url, headers=self.headers, json={'fulfillment': tracking_data}, timeout=15)
            return resp.status_code, resp.json() if resp.content else {}
        except Exception as e:
            return 0, {'error': str(e)}
    
    def register_webhook(self, topic, address):
        """Register a webhook."""
        return self._post('webhooks.json', {
            'webhook': {
                'topic': topic,
                'address': address,
                'format': 'json'
            }
        })
    
    def list_webhooks(self):
        """List all webhooks."""
        return self._get('webhooks.json')


class ShopifyChannelSplitService:
    """Determines WEB_PAID vs WEB_COD for Shopify orders."""
    
    @staticmethod
    def determine_channel(store: ShopifyStore, payload: dict) -> str:
        """
        Returns 'WEB_PAID' or 'WEB_COD' based on order payload and store rules.
        
        Default rule:
        - If financial_status == 'paid' OR successful captured transaction → WEB_PAID
        - If gateway/payment method contains COD keyword → WEB_COD
        - If financial_status in (pending, authorized) AND gateway matches COD list → WEB_COD
        - Otherwise → WEB_PAID
        """
        financial_status = payload.get('financial_status', '').lower()
        gateway = (payload.get('gateway') or '').lower()
        payment_gateway_names = payload.get('payment_gateway_names', []) or []
        
        # Get COD keywords from store settings
        cod_keywords = store.get_cod_keywords_list()
        cod_keywords_lower = [k.lower() for k in cod_keywords]
        
        # Check if explicitly paid
        if financial_status in ('paid', 'refunded', 'partially_refunded'):
            return 'WEB_PAID'
        
        # Check transactions for captured payments
        transactions = payload.get('transactions', []) or []
        for txn in transactions:
            if txn.get('status') == 'success' and txn.get('kind') in ('capture', 'sale'):
                return 'WEB_PAID'
        
        # Check gateway for COD keywords
        gateway_is_cod = any(kw in gateway for kw in cod_keywords_lower)
        
        # Check payment_gateway_names
        pgn_is_cod = any(
            any(kw in pgn.lower() for kw in cod_keywords_lower)
            for pgn in payment_gateway_names
        )
        
        if gateway_is_cod or pgn_is_cod:
            if store.treat_pending_cod_as_confirmed or financial_status in ('pending', 'authorized'):
                return 'WEB_COD'
        
        # Default fallback
        if financial_status == 'pending':
            return 'WEB_COD' if (gateway_is_cod or pgn_is_cod) else 'WEB_PAID'
        
        return 'WEB_PAID'
    
    @staticmethod
    def explain_channel(store: ShopifyStore, payload: dict) -> dict:
        """Return detailed explanation of channel decision."""
        financial_status = payload.get('financial_status', '').lower()
        gateway = (payload.get('gateway') or '').lower()
        cod_keywords = store.get_cod_keywords_list()
        cod_keywords_lower = [k.lower() for k in cod_keywords]
        gateway_is_cod = any(kw in gateway for kw in cod_keywords_lower)
        
        channel = ShopifyChannelSplitService.determine_channel(store, payload)
        
        reasons = []
        if financial_status in ('paid',):
            reasons.append(f"financial_status='{financial_status}' → paid")
        if gateway_is_cod:
            reasons.append(f"gateway='{payload.get('gateway')}' matches COD keyword")
        if not reasons:
            reasons.append(f"financial_status='{financial_status}', gateway='{payload.get('gateway')}'")
        
        return {
            'channel': channel,
            'financial_status': financial_status,
            'gateway': payload.get('gateway'),
            'cod_keywords_checked': cod_keywords,
            'gateway_is_cod': gateway_is_cod,
            'reasons': reasons,
        }


class ShopifyCustomerSyncService:
    """Syncs Shopify customers to ERP Leads and Customers."""
    
    @staticmethod
    def sync_customer(store: ShopifyStore, shopify_customer: dict, source: str = 'shopify_customer'):
        """
        Create or update Lead (and optionally Customer) from Shopify customer data.
        
        source options:
            - 'shopify_customer' (from customers/create webhook)
            - 'shopify_guest_checkout' (from order without customer account)
            - 'shopify_abandoned_checkout' (from abandoned checkout)
        """
        shopify_customer_id = str(shopify_customer.get('id', ''))
        phone = shopify_customer.get('phone') or shopify_customer.get('default_address', {}).get('phone', '')
        email = shopify_customer.get('email', '')
        first_name = shopify_customer.get('first_name', '')
        last_name = shopify_customer.get('last_name', '')
        name = f"{first_name} {last_name}".strip() or 'Shopify Customer'
        phone_normalized = normalize_phone(phone)
        
        # Map source to lead_source field
        lead_source_map = {
            'shopify_customer': 'shopify_order',
            'shopify_guest_checkout': 'shopify_checkout',
            'shopify_abandoned_checkout': 'shopify_abandoned_checkout',
        }
        lead_source = lead_source_map.get(source, 'shopify_order')
        
        # Find existing lead by phone, email, or external ID
        lead = None
        if phone_normalized:
            lead = Lead.objects.filter(phone_no__endswith=phone_normalized).first()
        if not lead and email:
            lead = Lead.objects.filter(email__iexact=email).first()
        
        if not lead:
            lead = Lead.objects.create(
                name=name,
                phone_no=f"+91{phone_normalized}" if phone_normalized else '',
                email=email or '',
                lead_source=lead_source,
                source_type='shopify',
                conversion_status='pending',
                notes=f"Shopify Customer ID: {shopify_customer_id}"
            )
        else:
            # Update existing lead if we have better data
            if not lead.email and email:
                lead.email = email
            if not lead.phone_no and phone_normalized:
                lead.phone_no = f"+91{phone_normalized}"
            lead.save(update_fields=['email', 'phone_no'])
        
        # Create external map for customer
        if shopify_customer_id:
            ShopifyExternalMap.objects.update_or_create(
                store=store,
                entity_type='CUSTOMER',
                external_id=shopify_customer_id,
                defaults={'internal_id': str(lead.id)}
            )
        
        # Optionally create/update Customer master record
        erp_customer = None
        if store.auto_promote_lead_to_customer and phone_normalized:
            try:
                erp_customer = Customer.objects.filter(phone_no__endswith=phone_normalized).first()
                if not erp_customer and store.create_lead_for_every_customer:
                    # Only create customer if they placed an order
                    pass  # Customer creation happens on order creation
            except Exception as e:
                logger.error(f"Customer sync error: {e}")
        
        return lead, erp_customer


class ShopifyOrderSyncService:
    """Syncs Shopify orders to ERP with channel split."""
    
    @staticmethod
    def _get_or_create_erp_customer(phone, email, name, shopify_customer_id=None):
        """Find or create an ERP Customer record."""
        from master.models import Customer
        import re
        phone_digits = re.sub(r'\D', '', str(phone or ''))
        phone_normalized = phone_digits[-10:] if len(phone_digits) >= 10 else None
        
        customer = None
        # Try to find by phone
        if phone_normalized:
            customer = Customer.objects.filter(phone_no__endswith=phone_normalized).first()
        # Try email-like search via phone as fallback
        if not customer and phone_normalized:
            customer = Customer.objects.filter(phone_no=phone_normalized).first()
        
        if not customer:
            # Create new customer
            parts = str(name or 'Shopify Customer').split(' ', 1)
            customer = Customer.objects.create(
                customer_name=name or 'Shopify Customer',
                phone_no=phone_normalized or '0000000000',
                pincode='000000',
                city='',
                state='',
                country='India',
            )
        return customer
    
    @staticmethod
    def _get_channel_for_split(channel_split):
        """Return the master.Channel for WEB_PAID or WEB_COD."""
        from master.models import Channel
        try:
            return Channel.objects.get(channel_type=channel_split)
        except Channel.DoesNotExist:
            # Try to create it
            prefix = 'WP' if channel_split == 'WEB_PAID' else 'WC'
            channel, _ = Channel.objects.get_or_create(
                channel_type=channel_split,
                defaults={'prefix': prefix}
            )
            return channel
    
    @staticmethod
    def _get_or_create_shopify_account():
        """Get or create the Shopify account for order assignment."""
        from master.models import Account
        account, _ = Account.objects.get_or_create(
            name='Shopify',
            defaults={'opening_balance': 0}
        )
        return account
    
    @staticmethod
    def _get_or_create_system_user():
        """Get a system user for auto-created orders."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.filter(is_superuser=True).first() or User.objects.first()
        return user
    
    @staticmethod
    def process_order(store: ShopifyStore, payload: dict, log=None):
        """Process an inbound Shopify order webhook - creates ERP Order."""
        import time
        start = time.time()
        
        order_id = str(payload.get('id', ''))
        order_number = payload.get('order_number', '') or payload.get('name', '')
        financial_status = payload.get('financial_status', '')
        fulfillment_status = payload.get('fulfillment_status', '')
        gateway = payload.get('gateway', '')
        tags = payload.get('tags', '')
        
        # Determine channel split
        channel_split = ShopifyChannelSplitService.determine_channel(store, payload)
        
        # Get customer info
        customer_data = payload.get('customer', {}) or {}
        shipping = payload.get('shipping_address', {}) or {}
        billing = payload.get('billing_address', {}) or {}
        phone = (customer_data.get('phone') or shipping.get('phone') or 
                 billing.get('phone') or payload.get('phone', ''))
        email = customer_data.get('email') or payload.get('email', '')
        first_name = (customer_data.get('first_name') or shipping.get('first_name') or billing.get('first_name', ''))
        last_name = (customer_data.get('last_name') or shipping.get('last_name') or billing.get('last_name', ''))
        name = f"{first_name} {last_name}".strip() or 'Shopify Customer'
        shopify_customer_id = str(customer_data.get('id', '')) if customer_data else None
        
        # Create or update ShopifyOrder
        shopify_order, created = ShopifyOrder.objects.update_or_create(
            store=store,
            shopify_order_id=order_id,
            defaults={
                'shopify_order_number': str(order_number),
                'shopify_data': payload,
                'financial_status': financial_status,
                'fulfillment_status': fulfillment_status,
                'channel_split': channel_split,
                'gateway': gateway,
                'shopify_tags': tags,
                'sync_status': 'synced'
            }
        )
        
        # Create ERP Order if not already linked
        erp_order = shopify_order.erp_order
        if not erp_order:
            try:
                erp_channel = ShopifyOrderSyncService._get_channel_for_split(channel_split)
                erp_account = ShopifyOrderSyncService._get_or_create_shopify_account()
                erp_user = ShopifyOrderSyncService._get_or_create_system_user()
                erp_customer = ShopifyOrderSyncService._get_or_create_erp_customer(
                    phone, email, name, shopify_customer_id
                )
                
                # Update customer address from Shopify
                if shipping.get('city') and not erp_customer.city:
                    erp_customer.city = shipping.get('city', '')
                    erp_customer.state = shipping.get('province', '') or shipping.get('state', '')
                    erp_customer.country = shipping.get('country', 'India')
                    if shipping.get('zip'):
                        erp_customer.pincode = shipping.get('zip', '000000')[:6]
                    erp_customer.save()
                
                total_price = Decimal(str(payload.get('total_price', '0')))
                cod_charge = Decimal('0')
                if channel_split == 'WEB_COD':
                    # Try to get COD charge from Shopify shipping lines
                    for sl in (payload.get('shipping_lines', []) or []):
                        if 'cod' in str(sl.get('title', '')).lower():
                            cod_charge = Decimal(str(sl.get('price', '0')))
                            break
                
                from master.models import Order as ERPOrder
                erp_order = ERPOrder.objects.create(
                    channel=erp_channel,
                    customer=erp_customer,
                    account=erp_account,
                    order_by=erp_user,
                    total_amount=total_price,
                    cod_charge=cod_charge,
                    source='shopify',
                    name=name,
                    phone=phone or erp_customer.phone_no,
                    address=shipping.get('address1', '') or billing.get('address1', ''),
                    city=shipping.get('city', '') or billing.get('city', ''),
                    state=shipping.get('province', '') or billing.get('province', ''),
                    country=shipping.get('country', 'India'),
                    pincode=(shipping.get('zip', '') or billing.get('zip', ''))[:6] if (shipping.get('zip') or billing.get('zip')) else '',
                    stage='Pending',
                )
                shopify_order.erp_order = erp_order
                shopify_order.save(update_fields=['erp_order'])
            except Exception as e:
                logger.error(f"ERP Order creation failed for Shopify order {order_id}: {e}")
        else:
            # Update channel on existing order if channel_split changed
            try:
                erp_channel = ShopifyOrderSyncService._get_channel_for_split(channel_split)
                if erp_order.channel != erp_channel:
                    erp_order.channel = erp_channel
                    erp_order.source = 'shopify'
                    erp_order.save(update_fields=['channel', 'source'])
            except Exception as e:
                logger.error(f"ERP Order update failed: {e}")
        
        # Create external map
        ShopifyExternalMap.objects.update_or_create(
            store=store,
            entity_type='ORDER',
            external_id=order_id,
            defaults={'internal_id': str(shopify_order.id)}
        )
        
        # Sync customer to leads
        source_type = 'shopify_customer' if customer_data.get('id') else 'shopify_guest_checkout'
        if not customer_data.get('phone') and phone:
            customer_data = dict(customer_data)
            customer_data['phone'] = phone
        if not customer_data.get('email') and email:
            customer_data = dict(customer_data)
            customer_data['email'] = email
        if not customer_data.get('first_name'):
            customer_data['first_name'] = first_name
            customer_data['last_name'] = last_name
        
        lead = None
        if phone or email:
            lead, _ = ShopifyCustomerSyncService.sync_customer(store, customer_data, source_type)
            if lead:
                order_value = Decimal(str(payload.get('total_price', 0)))
                if lead.conversion_status != 'won':
                    lead.conversion_status = 'won'
                    lead.won_at = timezone.now()
                    lead.conversion_value = order_value
                else:
                    lead.conversion_value = (lead.conversion_value or Decimal('0')) + order_value
                lead.save()
        
        # Check if this recovers an abandoned checkout
        ShopifyOrderSyncService._check_checkout_recovery(store, shopify_order, payload, lead)
        
        # Update store sync timestamp
        store.last_orders_sync_at = timezone.now()
        store.webhook_last_received_at = timezone.now()
        store.save(update_fields=['last_orders_sync_at', 'webhook_last_received_at'])
        
        if log:
            log.processed = True
            log.processing_time_ms = int((time.time() - start) * 1000)
            log.action_taken = f"order_{'created' if created else 'updated'}:{channel_split}"
            log.save()
        
        return shopify_order, lead, channel_split
    
    @staticmethod
    def _check_checkout_recovery(store, shopify_order, payload, lead=None):
        """Check if this order recovers an abandoned checkout."""
        customer = payload.get('customer', {}) or {}
        shipping = payload.get('shipping_address', {}) or {}
        phone = customer.get('phone') or shipping.get('phone') or payload.get('phone', '')
        phone_normalized = normalize_phone(phone)
        email = customer.get('email') or payload.get('email', '')
        
        checkout = None
        if phone_normalized:
            checkout = ShopifyAbandonedCheckout.objects.filter(
                store=store, customer_phone_normalized=phone_normalized, is_recovered=False
            ).order_by('-abandoned_at').first()
        if not checkout and email:
            checkout = ShopifyAbandonedCheckout.objects.filter(
                store=store, customer_email__iexact=email, is_recovered=False
            ).order_by('-abandoned_at').first()
        
        if checkout:
            checkout.is_recovered = True
            checkout.recovery_status = 'recovered'
            checkout.recovered_order = shopify_order
            checkout.completed_at = timezone.now()
            checkout.save()
            
            if checkout.lead:
                checkout.lead.conversion_status = 'won'
                checkout.lead.won_at = timezone.now()
                checkout.lead.save()


class ShopifyFulfillmentPushService:
    """Pushes fulfillment from ERP to Shopify."""
    
    @staticmethod
    def push_fulfillment(store: ShopifyStore, erp_order_id: str, shopify_order_id: str,
                         tracking_number: str, tracking_url: str, courier_name: str,
                         line_items=None) -> dict:
        """
        Push fulfillment to Shopify.
        Returns {'success': bool, 'message': str, 'shopify_response': dict}
        """
        if not store.access_token:
            return {'success': False, 'message': 'No Shopify access token configured', 'shopify_response': {}}
        
        client = ShopifyAPIClient(store)
        
        # Prepare fulfillment data
        fulfillment_data = {
            'location_id': None,  # Will use default location
            'tracking_number': tracking_number,
            'tracking_url': tracking_url,
            'tracking_company': courier_name,
            'notify_customer': True,
        }
        
        if line_items:
            fulfillment_data['line_items'] = line_items
        
        # Create outbox record
        outbox_record = ShopifyOutbox.objects.create(
            store=store,
            type='PUSH_FULFILLMENT',
            ref_internal_id=erp_order_id,
            ref_shopify_id=shopify_order_id,
            request_json={
                'shopify_order_id': shopify_order_id,
                'tracking_number': tracking_number,
                'tracking_url': tracking_url,
                'courier_name': courier_name,
            },
            status='PROCESSING'
        )
        
        try:
            status_code, response = client.create_fulfillment(shopify_order_id, fulfillment_data)
            
            if status_code in (200, 201):
                fulfillment = response.get('fulfillment', {})
                fulfillment_id = str(fulfillment.get('id', ''))
                
                # Update ShopifyOrder record
                ShopifyOrder.objects.filter(
                    store=store, shopify_order_id=shopify_order_id
                ).update(
                    fulfillment_sent=True,
                    fulfillment_id=fulfillment_id,
                    tracking_number=tracking_number,
                    tracking_url=tracking_url,
                    fulfillment_status='fulfilled'
                )
                
                # Create external map for fulfillment
                if fulfillment_id:
                    ShopifyExternalMap.objects.update_or_create(
                        store=store,
                        entity_type='FULFILLMENT',
                        external_id=fulfillment_id,
                        defaults={'internal_id': erp_order_id}
                    )
                
                outbox_record.status = 'DONE'
                outbox_record.response_json = response
                outbox_record.sent_at = timezone.now()
                outbox_record.save()
                
                return {'success': True, 'message': 'Fulfillment pushed successfully', 'shopify_response': response}
            else:
                error_msg = response.get('errors', str(response))
                outbox_record.status = 'FAILED'
                outbox_record.last_error = str(error_msg)
                outbox_record.response_json = response
                outbox_record.retries += 1
                outbox_record.save()
                return {'success': False, 'message': str(error_msg), 'shopify_response': response}
        
        except Exception as e:
            outbox_record.status = 'FAILED'
            outbox_record.last_error = str(e)
            outbox_record.retries += 1
            outbox_record.save()
            return {'success': False, 'message': str(e), 'shopify_response': {}}
    
    @staticmethod
    def push_from_erp_order(erp_order) -> dict:
        """Push fulfillment based on ERP Order object (when stage=Shipped)."""
        try:
            shopify_order_link = getattr(erp_order, 'shopify_order', None)
            if not shopify_order_link:
                return {'success': False, 'message': 'No Shopify order linked to this ERP order'}
            
            store = shopify_order_link.store
            if not store.auto_fulfill:
                return {'success': False, 'message': 'Auto-fulfill is disabled for this store'}
            
            tracking_number = getattr(erp_order, 'tracking_id', '') or ''
            tracking_url = ''
            courier_name = ''
            if erp_order.courier_partner:
                courier_name = str(erp_order.courier_partner)
            
            return ShopifyFulfillmentPushService.push_fulfillment(
                store=store,
                erp_order_id=str(erp_order.pk),
                shopify_order_id=shopify_order_link.shopify_order_id,
                tracking_number=tracking_number,
                tracking_url=tracking_url,
                courier_name=courier_name,
            )
        except Exception as e:
            logger.error(f"ERP order fulfillment push error: {e}")
            return {'success': False, 'message': str(e)}


class ShopifyAbandonedSyncService:
    """Syncs abandoned checkouts from Shopify."""
    
    @staticmethod
    def sync_abandoned_checkouts(store: ShopifyStore) -> dict:
        """Pull and sync abandoned checkouts from Shopify API."""
        if not store.access_token:
            return {'success': False, 'message': 'No access token', 'fetched': 0, 'inserted': 0, 'updated': 0, 'recovered': 0}
        
        client = ShopifyAPIClient(store)
        
        # Build params
        params = {
            'limit': 50,
            'status': 'open',
        }
        if store.last_abandoned_sync_at:
            params['updated_at_min'] = store.last_abandoned_sync_at.isoformat()
        
        status_code, response = client.get_abandoned_checkouts(params)
        
        if status_code != 200:
            return {
                'success': False,
                'message': f"API error: {response.get('errors', status_code)}",
                'fetched': 0, 'inserted': 0, 'updated': 0, 'recovered': 0
            }
        
        checkouts = response.get('checkouts', [])
        fetched = len(checkouts)
        inserted = updated = recovered = 0
        
        for checkout_data in checkouts:
            checkout_id = str(checkout_data.get('id', ''))
            if not checkout_id:
                continue
            
            # Check if already recovered
            if checkout_data.get('completed_at'):
                # Mark existing record as recovered
                existing = ShopifyAbandonedCheckout.objects.filter(
                    store=store, shopify_checkout_id=checkout_id, is_recovered=False
                ).first()
                if existing:
                    existing.is_recovered = True
                    existing.recovery_status = 'recovered'
                    existing.completed_at = ShopifyAbandonedSyncService._parse_dt(checkout_data.get('completed_at'))
                    existing.save()
                    if existing.lead:
                        existing.lead.conversion_status = 'won'
                        existing.lead.won_at = timezone.now()
                        existing.lead.save()
                    recovered += 1
                continue
            
            # Process the checkout
            result = ShopifyAbandonedSyncService._process_checkout(store, checkout_data)
            if result == 'created':
                inserted += 1
            elif result == 'updated':
                updated += 1
        
        # Update store sync time
        store.last_abandoned_sync_at = timezone.now()
        store.save(update_fields=['last_abandoned_sync_at'])
        
        return {
            'success': True,
            'message': f'Synced {fetched} checkouts',
            'fetched': fetched, 'inserted': inserted, 'updated': updated, 'recovered': recovered
        }
    
    @staticmethod
    def _process_checkout(store: ShopifyStore, checkout_data: dict) -> str:
        """Process a single abandoned checkout. Returns 'created', 'updated', or 'skipped'."""
        checkout_id = str(checkout_data.get('id', ''))
        token = checkout_data.get('token', '')
        
        customer = checkout_data.get('customer', {}) or {}
        billing = checkout_data.get('billing_address', {}) or {}
        shipping = checkout_data.get('shipping_address', {}) or {}
        
        phone = (customer.get('phone') or shipping.get('phone') or billing.get('phone', ''))
        phone_normalized = normalize_phone(phone)
        email = checkout_data.get('email') or customer.get('email', '')
        
        name = f"{billing.get('first_name', '')} {billing.get('last_name', '')}".strip()
        if not name:
            name = f"{shipping.get('first_name', '')} {shipping.get('last_name', '')}".strip()
        if not name:
            name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()
        
        line_items = checkout_data.get('line_items', []) or []
        cart_items = [
            {
                'product_title': item.get('title', ''),
                'variant_title': item.get('variant_title', ''),
                'quantity': item.get('quantity', 1),
                'price': str(item.get('price', '0'))
            }
            for item in line_items
        ]
        
        try:
            cart_value = Decimal(str(checkout_data.get('total_price', 0)))
        except Exception:
            cart_value = Decimal('0')
        
        checkout, created = ShopifyAbandonedCheckout.objects.update_or_create(
            store=store,
            shopify_checkout_id=checkout_id,
            defaults={
                'shopify_checkout_token': token,
                'customer_email': email,
                'customer_phone': phone,
                'customer_phone_normalized': phone_normalized,
                'customer_name': name,
                'cart_value': cart_value,
                'cart_items': cart_items,
                'cart_item_count': len(line_items),
                'currency': checkout_data.get('currency', 'INR'),
                'recovery_url': checkout_data.get('abandoned_checkout_url', ''),
                'abandoned_at': ShopifyAbandonedSyncService._parse_dt(checkout_data.get('created_at')),
                'shopify_data': checkout_data
            }
        )
        
        # Create lead if has contact info
        if (phone_normalized or email) and not checkout.lead:
            lead_data = {
                'id': customer.get('id'),
                'phone': phone,
                'email': email,
                'first_name': name.split(' ')[0] if name else '',
                'last_name': ' '.join(name.split(' ')[1:]) if name else '',
            }
            lead, _ = ShopifyCustomerSyncService.sync_customer(
                store, lead_data, 'shopify_abandoned_checkout'
            )
            # Add cart info to lead notes
            cart_info = f"Abandoned checkout - Cart value: ₹{cart_value} ({len(line_items)} items)"
            if checkout_data.get('abandoned_checkout_url'):
                cart_info += f"\nRecovery URL: {checkout_data['abandoned_checkout_url']}"
            if lead.notes:
                if cart_info not in lead.notes:
                    lead.notes += f"\n\n{cart_info}"
            else:
                lead.notes = cart_info
            lead.save()
            checkout.lead = lead
            checkout.save(update_fields=['lead'])
        
        # Create external map
        ShopifyExternalMap.objects.update_or_create(
            store=store,
            entity_type='ABANDONED_CHECKOUT',
            external_id=checkout_id,
            defaults={'internal_id': str(checkout.id)}
        )
        
        return 'created' if created else 'updated'
    
    @staticmethod
    def _parse_dt(dt_str):
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(str(dt_str).replace('Z', '+00:00'))
        except Exception:
            return None


class ShopifyEventInboxService:
    """Idempotent event inbox processor."""
    
    @staticmethod
    def receive_event(store: ShopifyStore, topic: str, payload: dict, webhook_id: str = None) -> ShopifyEventInbox:
        """
        Write webhook event to inbox with idempotency check.
        Returns the inbox record.
        """
        # Build idempotency key from store + topic + entity_id
        entity_id = str(payload.get('id', ''))
        idempotency_key = f"{store.id}:{topic}:{entity_id}:{webhook_id or ''}"
        
        # Check if already processed
        existing = ShopifyEventInbox.objects.filter(
            store=store,
            idempotency_key=idempotency_key,
            status='DONE'
        ).first()
        
        if existing:
            logger.info(f"Duplicate event skipped: {idempotency_key}")
            return existing
        
        try:
            event, created = ShopifyEventInbox.objects.get_or_create(
                store=store,
                idempotency_key=idempotency_key,
                defaults={
                    'topic': topic,
                    'webhook_id': webhook_id,
                    'payload_json': payload,
                    'status': 'PENDING',
                }
            )
        except Exception:
            # If unique constraint fails, return existing
            event = ShopifyEventInbox.objects.filter(
                store=store, idempotency_key=idempotency_key
            ).first()
        
        return event
    
    @staticmethod
    def process_event(event: ShopifyEventInbox) -> bool:
        """Process a single inbox event."""
        if event.status == 'DONE':
            return True
        
        event.status = 'PROCESSING'
        event.save(update_fields=['status'])
        
        store = event.store
        topic = event.topic
        payload = event.payload_json
        
        try:
            if topic.startswith('orders/'):
                ShopifyOrderSyncService.process_order(store, payload)
            elif topic.startswith('checkouts/'):
                ShopifyAbandonedSyncService._process_checkout(store, payload)
            elif topic.startswith('customers/'):
                customer_data = payload
                ShopifyCustomerSyncService.sync_customer(store, customer_data, 'shopify_customer')
            
            event.status = 'DONE'
            event.processed_at = timezone.now()
            event.save(update_fields=['status', 'processed_at'])
            return True
            
        except Exception as e:
            event.status = 'FAILED'
            event.last_error = str(e)
            event.retries = (event.retries or 0) + 1
            event.save(update_fields=['status', 'last_error', 'retries'])
            logger.error(f"Event processing failed: {e}")
            return False


class ShopifyConnectionService:
    """Handles store connection and webhook registration."""
    
    @staticmethod
    def connect_store(store: ShopifyStore, access_token: str, api_version: str = '2024-01') -> dict:
        """Connect a store by saving token and verifying connection."""
        store.access_token = access_token
        store.api_version = api_version
        store.save(update_fields=['access_token', 'api_version'])
        
        # Test connection
        client = ShopifyAPIClient(store)
        status_code, response = client.get_shop()
        
        if status_code != 200:
            return {'success': False, 'message': f'Failed to connect: {response.get("errors", status_code)}'}
        
        shop_data = response.get('shop', {})
        
        # Update store with shop info
        store.status = 'CONNECTED'
        store.connection_status = 'connected'
        store.installed_at = timezone.now()
        store.shop_domain = shop_data.get('myshopify_domain') or store.shop_domain
        store.granted_scopes = store.granted_scopes or ''
        store.save()
        
        return {
            'success': True,
            'message': 'Store connected successfully',
            'shop_name': shop_data.get('name'),
            'shop_email': shop_data.get('email'),
            'shop_currency': shop_data.get('currency'),
        }
    
    @staticmethod
    def disconnect_store(store: ShopifyStore) -> dict:
        """Disconnect a store."""
        store.status = 'DISCONNECTED'
        store.connection_status = 'disconnected'
        store.access_token = None
        store.save(update_fields=['status', 'connection_status', 'access_token'])
        return {'success': True, 'message': 'Store disconnected'}
    
    @staticmethod
    def verify_permissions(store: ShopifyStore) -> dict:
        """Verify API permissions by running test calls."""
        client = ShopifyAPIClient(store)
        results = {}
        
        status_code, response = client.get_shop()
        results['shop_info'] = status_code == 200
        
        status_code, response = client.get_orders({'limit': 1})
        results['read_orders'] = status_code == 200
        
        status_code, response = client.get_abandoned_checkouts({'limit': 1})
        results['read_checkouts'] = status_code in (200, 403)  # 403 = missing scope
        results['read_checkouts_scope'] = status_code == 200
        
        return {
            'success': all(results.values()),
            'permissions': results,
            'message': 'All permissions verified' if all(results.values()) else 'Some permissions missing'
        }
    
    @staticmethod
    def register_webhooks(store: ShopifyStore, base_url: str) -> dict:
        """Register all necessary webhooks."""
        if not store.access_token:
            return {'success': False, 'message': 'No access token'}
        
        client = ShopifyAPIClient(store)
        topics = [
            'orders/create',
            'orders/updated',
            'orders/paid',
            'orders/cancelled',
            'customers/create',
            'customers/update',
            'fulfillments/create',
            'fulfillments/update',
        ]
        
        webhook_url = f"{base_url}/webhooks/shopify/"
        results = []
        
        for topic in topics:
            status_code, response = client.register_webhook(topic, webhook_url)
            results.append({
                'topic': topic,
                'success': status_code in (200, 201, 422),  # 422 = already registered
                'status_code': status_code,
            })
        
        success_count = sum(1 for r in results if r['success'])
        return {
            'success': success_count == len(topics),
            'registered': success_count,
            'total': len(topics),
            'results': results
        }


class ShopifyPortalStatsService:
    """Stats for the portal overview tab."""
    
    @staticmethod
    def get_overview_stats(store: ShopifyStore) -> dict:
        """Get overview stats for the portal."""
        from django.utils import timezone
        from datetime import date
        
        today = timezone.now().date()
        today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
        
        # Orders synced today
        orders_today = ShopifyOrder.objects.filter(
            store=store,
            created__gte=today_start
        ).count()
        
        # Leads created today from Shopify
        customers_today = Lead.objects.filter(
            source_type='shopify',
            created__gte=today_start
        ).count()
        
        # Abandoned checkouts today
        abandoned_today = ShopifyAbandonedCheckout.objects.filter(
            store=store,
            created__gte=today_start
        ).count()
        
        # Total abandoned vs recovered
        total_abandoned = ShopifyAbandonedCheckout.objects.filter(store=store).count()
        total_recovered = ShopifyAbandonedCheckout.objects.filter(store=store, is_recovered=True).count()
        recovery_rate = round((total_recovered / total_abandoned * 100) if total_abandoned > 0 else 0, 1)
        
        # Fulfillment push success rate (last 30 days)
        month_ago = timezone.now() - timedelta(days=30)
        total_outbox = ShopifyOutbox.objects.filter(store=store, created__gte=month_ago).count()
        done_outbox = ShopifyOutbox.objects.filter(store=store, created__gte=month_ago, status='DONE').count()
        fulfillment_rate = round((done_outbox / total_outbox * 100) if total_outbox > 0 else 0, 1)
        
        # Last webhook received
        last_webhook = ShopifyWebhookLog.objects.filter(store=store).order_by('-created').first()
        
        return {
            'connection_status': store.status,
            'last_webhook_received': store.webhook_last_received_at,
            'orders_synced_today': orders_today,
            'customers_synced_today': customers_today,
            'abandoned_synced_today': abandoned_today,
            'fulfillment_push_success_rate': fulfillment_rate,
            'total_abandoned': total_abandoned,
            'total_recovered': total_recovered,
            'recovery_rate': recovery_rate,
            'last_orders_sync': store.last_orders_sync_at,
            'last_customers_sync': store.last_customers_sync_at,
            'last_abandoned_sync': store.last_abandoned_sync_at,
        }
