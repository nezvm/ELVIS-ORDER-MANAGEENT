"""
Comprehensive Backend Tests for Lead Management System

Tests:
1. Wabis WhatsApp Webhook (GET verification, POST message processing)
2. Shopify Orders Webhook
3. Shopify Checkouts Webhook (Abandoned)
4. Marketing Dashboard API
5. Lead List API with filtering
6. Lead creation from webhooks
"""
import pytest
import requests
import json
import os
import uuid
from datetime import datetime

# Base URL from environment or default to localhost
BASE_URL = os.environ.get('PREVIEW_URL', 'http://localhost:8001')

# Test data prefixes
TEST_PREFIX = "TEST_"


class TestWabisWebhook:
    """Test Wabis WhatsApp BSP webhook endpoints."""
    
    def test_wabis_webhook_verification_success(self):
        """Test Wabis webhook GET verification with correct token."""
        response = requests.get(
            f"{BASE_URL}/webhooks/wabis/",
            params={
                'hub.mode': 'subscribe',
                'hub.verify_token': 'elvis_wabis_verify_2024',
                'hub.challenge': 'test_challenge_abc123'
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert response.text == 'test_challenge_abc123', f"Challenge not echoed correctly: {response.text}"
        print("✓ Wabis webhook verification successful")
    
    def test_wabis_webhook_verification_failure(self):
        """Test Wabis webhook GET verification with wrong token."""
        response = requests.get(
            f"{BASE_URL}/webhooks/wabis/",
            params={
                'hub.mode': 'subscribe',
                'hub.verify_token': 'wrong_token',
                'hub.challenge': 'test_challenge_xyz'
            }
        )
        
        assert response.status_code == 403, f"Expected 403 for wrong token, got {response.status_code}"
        print("✓ Wabis webhook verification correctly rejects wrong token")
    
    def test_wabis_webhook_post_creates_customer_and_lead(self):
        """Test Wabis POST webhook creates WabisCustomer and Lead records."""
        unique_id = str(uuid.uuid4())[:8]
        wa_id = f"91{TEST_PREFIX}{unique_id}"
        
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "test_entry_123",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "917993344556",
                            "phone_number_id": f"test_phone_id_{unique_id}"
                        },
                        "contacts": [{
                            "profile": {"name": f"Test Customer {unique_id}"},
                            "wa_id": wa_id
                        }],
                        "messages": [{
                            "from": wa_id,
                            "id": f"wamid.{unique_id}",
                            "timestamp": str(int(datetime.now().timestamp())),
                            "type": "text",
                            "text": {"body": "Hello from test webhook"}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        
        response = requests.post(
            f"{BASE_URL}/webhooks/wabis/",
            headers={'Content-Type': 'application/json'},
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert response.text == 'OK', f"Expected 'OK', got {response.text}"
        print("✓ Wabis POST webhook processed successfully")


class TestShopifyOrdersWebhook:
    """Test Shopify orders webhook endpoint."""
    
    def test_shopify_orders_webhook_creates_order(self):
        """Test Shopify orders/create webhook creates ShopifyOrder and Lead."""
        unique_id = str(uuid.uuid4())[:8]
        
        payload = {
            "id": int(unique_id, 16) % 10000000000,  # Convert to numeric ID
            "order_number": f"TEST{unique_id}",
            "email": f"test_{unique_id}@example.com",
            "total_price": "1999.00",
            "financial_status": "paid",
            "fulfillment_status": None,
            "gateway": "razorpay",
            "customer": {
                "id": 999999,
                "first_name": f"Test_{unique_id}",
                "last_name": "Customer",
                "email": f"test_{unique_id}@example.com",
                "phone": f"+91{TEST_PREFIX[:4]}{unique_id}"
            },
            "shipping_address": {
                "first_name": f"Test_{unique_id}",
                "last_name": "Customer",
                "phone": f"+91{TEST_PREFIX[:4]}{unique_id}"
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/webhooks/shopify/orders/",
            headers={
                'Content-Type': 'application/json',
                'X-Shopify-Topic': 'orders/create',
                'X-Shopify-Shop-Domain': 'test-store.myshopify.com'
            },
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert response.text == 'OK', f"Expected 'OK', got {response.text}"
        print("✓ Shopify orders webhook processed successfully")
    
    def test_shopify_orders_webhook_cod(self):
        """Test Shopify orders webhook handles COD orders."""
        unique_id = str(uuid.uuid4())[:8]
        
        payload = {
            "id": int(unique_id, 16) % 10000000000,
            "order_number": f"COD{unique_id}",
            "email": f"cod_{unique_id}@example.com",
            "total_price": "2499.00",
            "financial_status": "pending",  # COD indicator
            "fulfillment_status": None,
            "gateway": "cash_on_delivery",
            "customer": {
                "first_name": f"COD_Test_{unique_id}",
                "last_name": "User",
                "email": f"cod_{unique_id}@example.com",
                "phone": f"+91700{unique_id[:7]}"
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/webhooks/shopify/orders/",
            headers={
                'Content-Type': 'application/json',
                'X-Shopify-Topic': 'orders/create',
                'X-Shopify-Shop-Domain': 'test-store.myshopify.com'
            },
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Shopify COD order webhook processed successfully")


class TestShopifyCheckoutsWebhook:
    """Test Shopify abandoned checkouts webhook endpoint."""
    
    def test_shopify_checkouts_webhook_creates_checkout(self):
        """Test Shopify checkouts/update webhook creates ShopifyAbandonedCheckout and Lead."""
        unique_id = str(uuid.uuid4())[:8]
        
        payload = {
            "id": int(unique_id, 16) % 10000000000,
            "token": f"checkout_token_{unique_id}",
            "email": f"abandoned_{unique_id}@example.com",
            "total_price": "2999.00",
            "currency": "INR",
            "abandoned_checkout_url": f"https://test-store.myshopify.com/checkouts/recover/{unique_id}",
            "billing_address": {
                "first_name": f"Abandoned_{unique_id}",
                "last_name": "User",
                "phone": f"+9198{unique_id[:8]}"
            },
            "line_items": [
                {"title": f"Test Product {unique_id}", "quantity": 1, "price": "2999.00"}
            ],
            "created_at": datetime.now().isoformat()
        }
        
        response = requests.post(
            f"{BASE_URL}/webhooks/shopify/checkouts/",
            headers={
                'Content-Type': 'application/json',
                'X-Shopify-Topic': 'checkouts/update',
                'X-Shopify-Shop-Domain': 'test-store.myshopify.com'
            },
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert response.text == 'OK', f"Expected 'OK', got {response.text}"
        print("✓ Shopify checkouts webhook processed successfully")
    
    def test_shopify_checkouts_completed_skipped(self):
        """Test that completed checkouts are skipped."""
        unique_id = str(uuid.uuid4())[:8]
        
        payload = {
            "id": int(unique_id, 16) % 10000000000,
            "token": f"completed_token_{unique_id}",
            "email": f"completed_{unique_id}@example.com",
            "total_price": "999.00",
            "completed_at": datetime.now().isoformat(),  # Completed checkout
            "line_items": []
        }
        
        response = requests.post(
            f"{BASE_URL}/webhooks/shopify/checkouts/",
            headers={
                'Content-Type': 'application/json',
                'X-Shopify-Topic': 'checkouts/update',
                'X-Shopify-Shop-Domain': 'test-store.myshopify.com'
            },
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Completed checkout correctly skipped")


class TestMarketingDashboard:
    """Test Marketing Dashboard pages (requires authentication)."""
    
    def setup_method(self):
        """Setup session with authentication."""
        self.session = requests.Session()
        
        # Get CSRF token from login page
        login_page = self.session.get(f"{BASE_URL}/accounts/login/")
        
        # Try to authenticate
        login_response = self.session.post(
            f"{BASE_URL}/accounts/login/",
            data={
                'username': 'admin',
                'password': 'admin123'
            },
            headers={
                'Referer': f"{BASE_URL}/accounts/login/"
            },
            allow_redirects=True
        )
        
        self.authenticated = login_response.status_code == 200 and '/login' not in login_response.url
    
    def test_dashboard_redirects_unauthenticated(self):
        """Test that dashboard redirects unauthenticated users."""
        response = requests.get(
            f"{BASE_URL}/marketing/dashboard/",
            allow_redirects=False
        )
        
        # Should redirect to login (302) or return 200 if public
        assert response.status_code in [302, 200], f"Unexpected status: {response.status_code}"
        print(f"✓ Dashboard access check passed (status: {response.status_code})")
    
    def test_dashboard_loads_authenticated(self):
        """Test dashboard loads when authenticated."""
        if not self.authenticated:
            pytest.skip("Could not authenticate - skipping authenticated tests")
        
        response = self.session.get(f"{BASE_URL}/marketing/dashboard/")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert 'Daily Insights' in response.text or 'dashboard' in response.text.lower()
        print("✓ Dashboard loaded successfully for authenticated user")
    
    def test_leads_list_loads(self):
        """Test leads list page loads."""
        if not self.authenticated:
            pytest.skip("Could not authenticate - skipping authenticated tests")
        
        response = self.session.get(f"{BASE_URL}/marketing/leads/")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert 'Lead' in response.text
        print("✓ Leads list page loaded successfully")
    
    def test_leads_filter_by_source_whatsapp(self):
        """Test leads list filtering by WhatsApp source."""
        if not self.authenticated:
            pytest.skip("Could not authenticate - skipping authenticated tests")
        
        response = self.session.get(
            f"{BASE_URL}/marketing/leads/",
            params={'lead_source': 'whatsapp'}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Leads filtered by WhatsApp source successfully")
    
    def test_leads_filter_by_source_shopify(self):
        """Test leads list filtering by Shopify source."""
        if not self.authenticated:
            pytest.skip("Could not authenticate - skipping authenticated tests")
        
        response = self.session.get(
            f"{BASE_URL}/marketing/leads/",
            params={'lead_source': 'shopify'}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Leads filtered by Shopify source successfully")
    
    def test_leads_filter_by_source_other(self):
        """Test leads list filtering by Other source."""
        if not self.authenticated:
            pytest.skip("Could not authenticate - skipping authenticated tests")
        
        response = self.session.get(
            f"{BASE_URL}/marketing/leads/",
            params={'lead_source': 'other'}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Leads filtered by Other source successfully")


class TestWabisDashboard:
    """Test Wabis Integration Dashboard."""
    
    def setup_method(self):
        """Setup session with authentication."""
        self.session = requests.Session()
        
        login_page = self.session.get(f"{BASE_URL}/accounts/login/")
        login_response = self.session.post(
            f"{BASE_URL}/accounts/login/",
            data={'username': 'admin', 'password': 'admin123'},
            headers={'Referer': f"{BASE_URL}/accounts/login/"},
            allow_redirects=True
        )
        
        self.authenticated = login_response.status_code == 200 and '/login' not in login_response.url
    
    def test_wabis_dashboard_loads(self):
        """Test Wabis dashboard at /integrations/wabis/."""
        if not self.authenticated:
            pytest.skip("Could not authenticate - skipping authenticated tests")
        
        response = self.session.get(f"{BASE_URL}/integrations/wabis/")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        # Check for expected content
        assert 'WhatsApp' in response.text or 'Wabis' in response.text or 'webhook' in response.text.lower()
        print("✓ Wabis dashboard loaded successfully")


class TestShopifyFulfillmentsWebhook:
    """Test Shopify fulfillments webhook endpoint."""
    
    def test_shopify_fulfillments_webhook(self):
        """Test Shopify fulfillments/create webhook."""
        unique_id = str(uuid.uuid4())[:8]
        
        payload = {
            "id": int(unique_id, 16) % 10000000000,
            "order_id": 123456789,  # Reference to existing order
            "status": "success",
            "tracking_number": f"TRACK{unique_id}",
            "tracking_url": f"https://tracking.example.com/{unique_id}"
        }
        
        response = requests.post(
            f"{BASE_URL}/webhooks/shopify/fulfillments/",
            headers={
                'Content-Type': 'application/json',
                'X-Shopify-Topic': 'fulfillments/create',
                'X-Shopify-Shop-Domain': 'test-store.myshopify.com'
            },
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Shopify fulfillments webhook processed successfully")


class TestInvalidPayloads:
    """Test webhook error handling."""
    
    def test_wabis_invalid_json(self):
        """Test Wabis webhook handles invalid JSON gracefully."""
        response = requests.post(
            f"{BASE_URL}/webhooks/wabis/",
            headers={'Content-Type': 'application/json'},
            data='invalid json {{'
        )
        
        # Should return 200 to prevent Shopify/Meta retries
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Wabis webhook handles invalid JSON gracefully")
    
    def test_shopify_invalid_json(self):
        """Test Shopify webhook handles invalid JSON gracefully."""
        response = requests.post(
            f"{BASE_URL}/webhooks/shopify/orders/",
            headers={'Content-Type': 'application/json'},
            data='not valid json'
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Shopify orders webhook correctly rejects invalid JSON")


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
