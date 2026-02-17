"""
Shopify Integration Services

This module provides services for:
- Webhook verification and processing
- Lead creation from orders and abandoned checkouts
- Order sync and fulfillment management
"""
import hashlib
import hmac
import base64
import json
import logging
import re
from decimal import Decimal
from datetime import datetime
from django.utils import timezone
from django.conf import settings

from integrations.models import (
    ShopifyStore, ShopifyOrder, ShopifyAbandonedCheckout, 
    ShopifyWebhookLog, ShopifySyncLog
)
from marketing.models import Lead

logger = logging.getLogger(__name__)


def normalize_phone(phone):
    """Normalize phone number for matching."""
    if not phone:
        return None
    digits = re.sub(r'\D', '', phone)
    if len(digits) >= 10:
        return digits[-10:]
    return None


class ShopifyWebhookService:
    """Service for handling Shopify webhooks."""
    
    @staticmethod
    def verify_webhook(request, secret):
        """Verify Shopify webhook HMAC signature."""
        hmac_header = request.headers.get('X-Shopify-Hmac-SHA256', '')
        if not hmac_header or not secret:
            return False
        
        try:
            computed_hmac = base64.b64encode(
                hmac.new(
                    secret.encode('utf-8'),
                    request.body,
                    hashlib.sha256
                ).digest()
            ).decode()
            return hmac.compare_digest(computed_hmac, hmac_header)
        except Exception as e:
            logger.error(f"Webhook verification error: {e}")
            return False
    
    @staticmethod
    def get_store_from_request(request):
        """Get ShopifyStore from webhook request headers."""
        shop_domain = request.headers.get('X-Shopify-Shop-Domain', '')
        if shop_domain:
            return ShopifyStore.objects.filter(shop_domain__icontains=shop_domain).first()
        return None
    
    @staticmethod
    def log_webhook(store, topic, payload, request):
        """Create webhook log entry."""
        return ShopifyWebhookLog.objects.create(
            store=store,
            webhook_topic=topic,
            shopify_domain=request.headers.get('X-Shopify-Shop-Domain', ''),
            shopify_hmac=request.headers.get('X-Shopify-Hmac-SHA256', '')[:50],
            payload=payload
        )


class ShopifyOrderService:
    """Service for processing Shopify orders."""
    
    @staticmethod
    def process_order_webhook(store, payload, log=None):
        """Process order create/update webhook."""
        import time
        start = time.time()
        
        try:
            order_id = str(payload.get('id', ''))
            order_number = payload.get('order_number', '') or payload.get('name', '')
            
            # Create or update ShopifyOrder
            shopify_order, created = ShopifyOrder.objects.update_or_create(
                store=store,
                shopify_order_id=order_id,
                defaults={
                    'shopify_order_number': str(order_number),
                    'shopify_data': payload,
                    'financial_status': payload.get('financial_status', ''),
                    'fulfillment_status': payload.get('fulfillment_status', ''),
                    'sync_status': 'synced'
                }
            )
            
            # Create Lead from order
            lead = ShopifyOrderService.create_lead_from_order(store, shopify_order, payload)
            
            # Check if this recovers an abandoned checkout
            ShopifyOrderService.check_checkout_recovery(store, shopify_order, payload)
            
            if log:
                log.processed = True
                log.processing_time_ms = int((time.time() - start) * 1000)
                log.action_taken = 'created' if created else 'updated'
                log.save()
            
            return shopify_order, lead
            
        except Exception as e:
            logger.error(f"Order webhook processing error: {e}")
            if log:
                log.error_message = str(e)
                log.save()
            raise
    
    @staticmethod
    def create_lead_from_order(store, shopify_order, payload):
        """Create or update Lead from Shopify order."""
        customer = payload.get('customer', {})
        shipping = payload.get('shipping_address', {}) or payload.get('billing_address', {})
        
        # Extract customer info
        phone = (
            customer.get('phone') or 
            shipping.get('phone') or 
            payload.get('phone', '')
        )
        phone_normalized = normalize_phone(phone)
        
        email = customer.get('email') or payload.get('email', '')
        name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()
        if not name:
            name = f"{shipping.get('first_name', '')} {shipping.get('last_name', '')}".strip()
        
        if not phone_normalized and not email:
            logger.warning(f"No contact info for order {shopify_order.shopify_order_id}")
            return None
        
        # Determine if COD or Prepaid
        payment_gateway = payload.get('gateway', '') or ''
        financial_status = payload.get('financial_status', '')
        is_cod = (
            financial_status == 'pending' or
            'cod' in payment_gateway.lower() or
            'cash' in payment_gateway.lower()
        )
        
        order_value = Decimal(str(payload.get('total_price', 0)))
        
        # Find or create lead
        lead = None
        if phone_normalized:
            lead = Lead.objects.filter(phone_no__endswith=phone_normalized).first()
        if not lead and email:
            lead = Lead.objects.filter(email__iexact=email).first()
        
        if not lead:
            lead = Lead.objects.create(
                name=name or 'Shopify Customer',
                phone_no=f"+91{phone_normalized}" if phone_normalized else '',
                email=email,
                lead_source='shopify_order',
                source_type='shopify',
                conversion_status='won',
                won_at=timezone.now(),
                conversion_value=order_value,
                notes=f"Shopify Order #{shopify_order.shopify_order_number}\n{'COD' if is_cod else 'Prepaid'}"
            )
        else:
            # Update lead to Won if not already
            if lead.conversion_status != 'won':
                lead.conversion_status = 'won'
                lead.status = 'Won'
                lead.won_at = timezone.now()
                lead.conversion_value = (lead.conversion_value or Decimal('0')) + order_value
            else:
                lead.conversion_value = (lead.conversion_value or Decimal('0')) + order_value
            
            if lead.notes:
                lead.notes += f"\n\nShopify Order #{shopify_order.shopify_order_number}"
            else:
                lead.notes = f"Shopify Order #{shopify_order.shopify_order_number}"
            lead.save()
        
        return lead
    
    @staticmethod
    def check_checkout_recovery(store, shopify_order, payload):
        """Check if this order recovers an abandoned checkout."""
        customer = payload.get('customer', {})
        shipping = payload.get('shipping_address', {})
        
        phone = customer.get('phone') or shipping.get('phone') or payload.get('phone', '')
        phone_normalized = normalize_phone(phone)
        email = customer.get('email') or payload.get('email', '')
        
        # Find matching abandoned checkout
        checkout = None
        if phone_normalized:
            checkout = ShopifyAbandonedCheckout.objects.filter(
                store=store,
                customer_phone_normalized=phone_normalized,
                is_recovered=False
            ).order_by('-abandoned_at').first()
        
        if not checkout and email:
            checkout = ShopifyAbandonedCheckout.objects.filter(
                store=store,
                customer_email__iexact=email,
                is_recovered=False
            ).order_by('-abandoned_at').first()
        
        if checkout:
            checkout.is_recovered = True
            checkout.recovery_status = 'recovered'
            checkout.recovered_order = shopify_order
            checkout.completed_at = timezone.now()
            checkout.save()
            
            # Update lead if linked
            if checkout.lead:
                checkout.lead.conversion_status = 'won'
                checkout.lead.status = 'Won'
                checkout.lead.won_at = timezone.now()
                checkout.lead.save()
            
            logger.info(f"Recovered checkout {checkout.shopify_checkout_id} via order {shopify_order.shopify_order_id}")


class ShopifyCheckoutService:
    """Service for processing Shopify abandoned checkouts."""
    
    @staticmethod
    def process_checkout_webhook(store, payload, log=None):
        """Process checkout create/update webhook (abandoned checkout)."""
        import time
        start = time.time()
        
        try:
            checkout_id = str(payload.get('id', ''))
            token = payload.get('token', '')
            
            # Check if checkout is completed (not abandoned)
            if payload.get('completed_at'):
                logger.info(f"Checkout {checkout_id} completed, skipping")
                if log:
                    log.processed = True
                    log.action_taken = 'completed_checkout_skipped'
                    log.save()
                return None, None
            
            # Extract customer info
            customer = payload.get('customer', {}) or {}
            billing = payload.get('billing_address', {}) or {}
            shipping = payload.get('shipping_address', {}) or {}
            
            phone = customer.get('phone') or shipping.get('phone') or billing.get('phone', '')
            phone_normalized = normalize_phone(phone)
            email = payload.get('email') or customer.get('email', '')
            name = payload.get('buyer_accepts_marketing_updated_at') or ''
            if not name:
                name = f"{billing.get('first_name', '')} {billing.get('last_name', '')}".strip()
            if not name:
                name = f"{shipping.get('first_name', '')} {shipping.get('last_name', '')}".strip()
            
            # Extract cart info
            line_items = payload.get('line_items', [])
            cart_items = [
                {
                    'product_title': item.get('title', ''),
                    'variant_title': item.get('variant_title', ''),
                    'quantity': item.get('quantity', 1),
                    'price': str(item.get('price', '0'))
                }
                for item in line_items
            ]
            cart_value = Decimal(str(payload.get('total_price', 0)))
            
            # Create or update checkout record
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
                    'currency': payload.get('currency', 'INR'),
                    'recovery_url': payload.get('abandoned_checkout_url', ''),
                    'abandoned_at': ShopifyCheckoutService._parse_datetime(payload.get('created_at')),
                    'shopify_data': payload
                }
            )
            
            # Create Lead from abandoned checkout
            lead = None
            if phone_normalized or email:
                lead = ShopifyCheckoutService.create_lead_from_checkout(checkout)
            
            if log:
                log.processed = True
                log.processing_time_ms = int((time.time() - start) * 1000)
                log.action_taken = 'checkout_created' if created else 'checkout_updated'
                log.save()
            
            return checkout, lead
            
        except Exception as e:
            logger.error(f"Checkout webhook processing error: {e}")
            if log:
                log.error_message = str(e)
                log.save()
            raise
    
    @staticmethod
    def create_lead_from_checkout(checkout):
        """Create Lead from abandoned checkout."""
        # Find existing lead
        lead = None
        if checkout.customer_phone_normalized:
            lead = Lead.objects.filter(
                phone_no__endswith=checkout.customer_phone_normalized
            ).first()
        if not lead and checkout.customer_email:
            lead = Lead.objects.filter(email__iexact=checkout.customer_email).first()
        
        if not lead:
            lead = Lead.objects.create(
                name=checkout.customer_name or 'Shopify Checkout',
                phone_no=f"+91{checkout.customer_phone_normalized}" if checkout.customer_phone_normalized else '',
                email=checkout.customer_email or '',
                lead_source='shopify_checkout',
                source_type='shopify',
                status='Pending',
                conversion_status='pending',
                notes=f"Abandoned checkout - Cart value: ₹{checkout.cart_value}\nItems: {checkout.cart_item_count}"
            )
        else:
            # Update existing lead notes
            cart_info = f"Abandoned checkout - Cart value: ₹{checkout.cart_value}"
            if lead.notes and cart_info not in lead.notes:
                lead.notes += f"\n\n{cart_info}"
            lead.save()
        
        # Link lead to checkout
        checkout.lead = lead
        checkout.save()
        
        return lead
    
    @staticmethod
    def _parse_datetime(dt_str):
        """Parse Shopify datetime string."""
        if not dt_str:
            return None
        try:
            if isinstance(dt_str, str):
                return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            return dt_str
        except Exception:
            return None


class ShopifyFulfillmentService:
    """Service for handling fulfillment updates."""
    
    @staticmethod
    def process_fulfillment_webhook(store, payload, log=None):
        """Process fulfillment create/update webhook."""
        import time
        start = time.time()
        
        try:
            order_id = str(payload.get('order_id', ''))
            fulfillment_id = str(payload.get('id', ''))
            tracking_number = payload.get('tracking_number', '')
            tracking_url = payload.get('tracking_url', '') or payload.get('tracking_urls', [''])[0] if payload.get('tracking_urls') else ''
            status = payload.get('status', '')
            
            # Find the ShopifyOrder
            shopify_order = ShopifyOrder.objects.filter(
                store=store,
                shopify_order_id=order_id
            ).first()
            
            if shopify_order:
                shopify_order.fulfillment_id = fulfillment_id
                shopify_order.tracking_number = tracking_number
                shopify_order.tracking_url = tracking_url
                shopify_order.fulfillment_status = status
                shopify_order.fulfillment_sent = True
                shopify_order.save()
                
                if log:
                    log.processed = True
                    log.processing_time_ms = int((time.time() - start) * 1000)
                    log.action_taken = 'fulfillment_updated'
                    log.save()
                
                return shopify_order
            else:
                logger.warning(f"Order {order_id} not found for fulfillment {fulfillment_id}")
                if log:
                    log.error_message = f"Order {order_id} not found"
                    log.save()
                return None
                
        except Exception as e:
            logger.error(f"Fulfillment webhook processing error: {e}")
            if log:
                log.error_message = str(e)
                log.save()
            raise
