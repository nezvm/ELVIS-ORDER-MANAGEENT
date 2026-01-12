"""Mock services for external integrations."""

import uuid
import random
from datetime import datetime, timedelta
from django.utils import timezone

from master.models import Customer, Order, Product
from channels_config.models import DynamicChannel
from .models import (
    GoogleWorkspaceConfig, ContactSyncLog, SyncedContact,
    ShopifyStore, ShopifyOrder, ShopifySyncLog
)


class MockGoogleContactsService:
    """Mock service for Google People API integration."""
    
    @staticmethod
    def fetch_contacts(config, incremental=True):
        """Simulate fetching contacts from Google."""
        # Create sync log
        sync_log = ContactSyncLog.objects.create(
            config=config,
            sync_type='incremental' if incremental else 'full',
            status='in_progress'
        )
        
        try:
            # Generate mock contacts
            mock_contacts = MockGoogleContactsService._generate_mock_contacts(10)
            
            created = 0
            updated = 0
            skipped = 0
            
            for contact_data in mock_contacts:
                phone = contact_data.get('phone')
                if not phone:
                    skipped += 1
                    continue
                
                # Check if contact exists
                existing = SyncedContact.objects.filter(
                    config=config,
                    google_resource_name=contact_data['resource_name']
                ).first()
                
                if existing:
                    # Update
                    existing.google_data = contact_data
                    existing.save()
                    updated += 1
                else:
                    # Check for existing customer by phone
                    customer = Customer.objects.filter(phone_no=phone).first()
                    
                    if not customer:
                        # Create new customer
                        customer = Customer.objects.create(
                            phone_no=phone,
                            customer_name=contact_data.get('name', 'Unknown'),
                            address=contact_data.get('address', ''),
                            city=contact_data.get('city', ''),
                            state=contact_data.get('state', ''),
                            pincode=contact_data.get('pincode', ''),
                            country='India'
                        )
                    
                    # Create synced contact record
                    SyncedContact.objects.create(
                        config=config,
                        google_resource_name=contact_data['resource_name'],
                        customer=customer,
                        google_data=contact_data
                    )
                    created += 1
            
            # Update sync log
            sync_log.status = 'completed'
            sync_log.contacts_fetched = len(mock_contacts)
            sync_log.contacts_created = created
            sync_log.contacts_updated = updated
            sync_log.contacts_skipped = skipped
            sync_log.completed_at = timezone.now()
            sync_log.save()
            
            # Update config
            config.last_sync_at = timezone.now()
            config.last_sync_token = f"sync_token_{uuid.uuid4().hex[:8]}"
            config.save()
            
            return sync_log
            
        except Exception as e:
            sync_log.status = 'failed'
            sync_log.error_message = str(e)
            sync_log.save()
            raise
    
    @staticmethod
    def _generate_mock_contacts(count):
        """Generate mock contact data."""
        names = ['Rahul Sharma', 'Priya Patel', 'Amit Kumar', 'Sneha Reddy', 'Vikram Singh',
                 'Anjali Gupta', 'Rajesh Verma', 'Kavita Nair', 'Suresh Menon', 'Deepa Joshi']
        cities = ['Mumbai', 'Delhi', 'Bangalore', 'Chennai', 'Hyderabad', 'Pune', 'Kolkata']
        states = ['Maharashtra', 'Delhi', 'Karnataka', 'Tamil Nadu', 'Telangana', 'West Bengal']
        
        contacts = []
        for i in range(count):
            contacts.append({
                'resource_name': f'people/{uuid.uuid4().hex}',
                'name': random.choice(names),
                'phone': f'+91{random.randint(7000000000, 9999999999)}',
                'email': f'user{i}@example.com',
                'address': f'{random.randint(1, 100)}, Sample Street',
                'city': random.choice(cities),
                'state': random.choice(states),
                'pincode': str(random.randint(100000, 999999)),
            })
        
        return contacts


class MockShopifyService:
    """Mock service for Shopify integration."""
    
    @staticmethod
    def sync_orders(store):
        """Simulate syncing orders from Shopify."""
        sync_log = ShopifySyncLog.objects.create(
            store=store,
            sync_type='orders',
            status='started'
        )
        
        try:
            # Generate mock Shopify orders
            mock_orders = MockShopifyService._generate_mock_orders(5)
            
            created = 0
            updated = 0
            failed = 0
            
            for order_data in mock_orders:
                try:
                    # Check if order exists
                    existing = ShopifyOrder.objects.filter(
                        store=store,
                        shopify_order_id=order_data['id']
                    ).first()
                    
                    if existing:
                        existing.shopify_data = order_data
                        existing.financial_status = order_data['financial_status']
                        existing.fulfillment_status = order_data['fulfillment_status']
                        existing.save()
                        updated += 1
                    else:
                        # Determine channel based on payment status
                        is_paid = order_data['financial_status'] == 'paid'
                        channel = store.web_paid_channel if is_paid else store.web_cod_channel
                        
                        if not channel:
                            # Try to get default channel
                            channel = DynamicChannel.objects.filter(is_active=True).first()
                        
                        # Find or create customer
                        customer_data = order_data.get('customer', {})
                        phone = customer_data.get('phone', f'+91{random.randint(7000000000, 9999999999)}')
                        
                        customer, _ = Customer.objects.get_or_create(
                            phone_no=phone,
                            defaults={
                                'customer_name': customer_data.get('name', 'Shopify Customer'),
                                'address': customer_data.get('address', ''),
                                'city': customer_data.get('city', ''),
                                'state': customer_data.get('state', ''),
                                'pincode': customer_data.get('pincode', ''),
                                'country': 'India'
                            }
                        )
                        
                        # Create Shopify order record (ERP order would be created manually or via separate process)
                        ShopifyOrder.objects.create(
                            store=store,
                            shopify_order_id=order_data['id'],
                            shopify_order_number=order_data['order_number'],
                            shopify_data=order_data,
                            financial_status=order_data['financial_status'],
                            fulfillment_status=order_data['fulfillment_status'],
                            sync_status='synced'
                        )
                        created += 1
                        
                except Exception as e:
                    failed += 1
            
            # Update sync log
            sync_log.status = 'completed'
            sync_log.items_processed = len(mock_orders)
            sync_log.items_created = created
            sync_log.items_updated = updated
            sync_log.items_failed = failed
            sync_log.completed_at = timezone.now()
            sync_log.save()
            
            # Update store
            store.last_sync_at = timezone.now()
            store.connection_status = 'connected'
            store.save()
            
            return sync_log
            
        except Exception as e:
            sync_log.status = 'failed'
            sync_log.error_message = str(e)
            sync_log.save()
            raise
    
    @staticmethod
    def send_fulfillment(shopify_order, tracking_number, tracking_url=None):
        """Simulate sending fulfillment to Shopify."""
        # Mock fulfillment response
        fulfillment_id = f"gid://shopify/Fulfillment/{random.randint(1000000, 9999999)}"
        
        shopify_order.fulfillment_sent = True
        shopify_order.fulfillment_id = fulfillment_id
        shopify_order.tracking_number = tracking_number
        shopify_order.tracking_url = tracking_url
        shopify_order.fulfillment_status = 'fulfilled'
        shopify_order.save()
        
        return {
            'success': True,
            'fulfillment_id': fulfillment_id,
            'message': 'Fulfillment created successfully (MOCK)'
        }
    
    @staticmethod
    def _generate_mock_orders(count):
        """Generate mock Shopify order data."""
        products = ['Product A', 'Product B', 'Product C']
        financial_statuses = ['paid', 'pending', 'paid', 'paid']  # More paid orders
        fulfillment_statuses = ['unfulfilled', 'fulfilled', 'unfulfilled']
        
        orders = []
        for i in range(count):
            order_id = random.randint(1000000000, 9999999999)
            orders.append({
                'id': str(order_id),
                'order_number': f'#{1000 + i}',
                'financial_status': random.choice(financial_statuses),
                'fulfillment_status': random.choice(fulfillment_statuses),
                'total_price': str(random.randint(500, 5000)),
                'currency': 'INR',
                'created_at': (timezone.now() - timedelta(days=random.randint(0, 30))).isoformat(),
                'customer': {
                    'id': random.randint(100000, 999999),
                    'name': f'Customer {i}',
                    'phone': f'+91{random.randint(7000000000, 9999999999)}',
                    'email': f'customer{i}@example.com',
                    'address': f'{random.randint(1, 100)}, Sample Address',
                    'city': random.choice(['Mumbai', 'Delhi', 'Bangalore']),
                    'state': random.choice(['Maharashtra', 'Delhi', 'Karnataka']),
                    'pincode': str(random.randint(100000, 999999))
                },
                'line_items': [
                    {
                        'id': random.randint(10000, 99999),
                        'title': random.choice(products),
                        'quantity': random.randint(1, 3),
                        'price': str(random.randint(200, 1000))
                    }
                ],
                'shipping_address': {
                    'address1': f'{random.randint(1, 100)}, Shipping Address',
                    'city': random.choice(['Mumbai', 'Delhi', 'Bangalore']),
                    'province': random.choice(['Maharashtra', 'Delhi', 'Karnataka']),
                    'zip': str(random.randint(100000, 999999)),
                    'country': 'India'
                }
            })
        
        return orders
    
    @staticmethod
    def test_connection(store):
        """Test Shopify connection."""
        # Mock connection test
        return {
            'success': True,
            'shop_name': store.name,
            'message': 'Connection successful (MOCK)'
        }


class WebhookService:
    """Service for sending webhooks."""
    
    @staticmethod
    def send_webhook(endpoint, event_type, payload):
        """Send webhook to endpoint."""
        from .models import WebhookLog
        import requests
        import time
        
        start_time = time.time()
        
        log = WebhookLog.objects.create(
            endpoint=endpoint,
            event_type=event_type,
            payload=payload
        )
        
        try:
            headers = {'Content-Type': 'application/json'}
            headers.update(endpoint.headers)
            
            # Add signature if secret is configured
            if endpoint.secret:
                import hmac
                import hashlib
                import json
                signature = hmac.new(
                    endpoint.secret.encode(),
                    json.dumps(payload).encode(),
                    hashlib.sha256
                ).hexdigest()
                headers['X-Webhook-Signature'] = signature
            
            # In production, this would make actual HTTP request
            # For mock, we simulate success
            response_time = int((time.time() - start_time) * 1000) + random.randint(50, 200)
            
            log.status_code = 200
            log.response_body = '{"success": true}'
            log.success = True
            log.response_time_ms = response_time
            log.save()
            
            # Update endpoint stats
            endpoint.total_sent += 1
            endpoint.last_sent_at = timezone.now()
            endpoint.save()
            
            return True
            
        except Exception as e:
            log.success = False
            log.error_message = str(e)
            log.save()
            
            endpoint.total_failed += 1
            endpoint.save()
            
            return False
    
    @staticmethod
    def trigger_event(event_type, payload):
        """Trigger webhooks for an event type."""
        from .models import WebhookEndpoint
        
        endpoints = WebhookEndpoint.objects.filter(
            event_type=event_type,
            is_enabled=True,
            is_active=True
        )
        
        results = []
        for endpoint in endpoints:
            success = WebhookService.send_webhook(endpoint, event_type, payload)
            results.append({
                'endpoint': endpoint.name,
                'success': success
            })
        
        return results
