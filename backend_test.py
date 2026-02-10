#!/usr/bin/env python3
"""
Backend Test Suite for Elvis-Manager ERP Application
Tests WhatsApp Lead Auto-Save feature endpoints and UI pages
"""

import requests
import sys
import json
from urllib.parse import urljoin

class WhatsAppERPTester:
    def __init__(self, base_url, username, password):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.csrf_token = None
        
    def login(self):
        """Login to get session cookie and CSRF token"""
        print("🔐 Attempting to login...")
        
        # First get the login page to extract CSRF token
        login_url = urljoin(self.base_url, '/accounts/login/')
        try:
            response = self.session.get(login_url)
            if response.status_code != 200:
                print(f"❌ Failed to access login page: {response.status_code}")
                return False
                
            # Extract CSRF token from response
            if 'csrftoken' in self.session.cookies:
                self.csrf_token = self.session.cookies['csrftoken']
            elif 'csrf_token' in response.text:
                # Try to extract from HTML
                import re
                csrf_match = re.search(r'name=["\']csrfmiddlewaretoken["\'] value=["\']([^"\']+)["\']', response.text)
                if csrf_match:
                    self.csrf_token = csrf_match.group(1)
            
            # Prepare login data
            login_data = {
                'username': self.username,
                'password': self.password,
            }
            
            if self.csrf_token:
                login_data['csrfmiddlewaretoken'] = self.csrf_token
                
            # Set headers
            headers = {
                'Referer': login_url,
                'Content-Type': 'application/x-www-form-urlencoded',
            }
            
            if self.csrf_token:
                headers['X-CSRFToken'] = self.csrf_token
            
            # Attempt login
            response = self.session.post(login_url, data=login_data, headers=headers, allow_redirects=False)
            
            # Check if login was successful (redirect or 200 with success indicators)
            if response.status_code in [200, 302, 303]:
                # Verify we're logged in by checking a protected page
                dashboard_response = self.session.get(self.base_url + '/')
                if dashboard_response.status_code == 200 and 'login' not in dashboard_response.url.lower():
                    print("✅ Login successful!")
                    return True
                else:
                    print(f"❌ Login verification failed. Redirected to: {dashboard_response.url}")
                    return False
            else:
                print(f"❌ Login failed with status: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Login error: {str(e)}")
            return False
    
    def test_endpoint(self, endpoint, expected_title_keywords=None):
        """Test a single endpoint"""
        url = urljoin(self.base_url, endpoint)
        
        try:
            response = self.session.get(url)
            
            # Check status code
            if response.status_code != 200:
                return {
                    'endpoint': endpoint,
                    'status': 'FAILED',
                    'status_code': response.status_code,
                    'error': f'HTTP {response.status_code}',
                    'content_check': False
                }
            
            # Check content
            content_valid = True
            content_issues = []
            
            # Basic HTML structure check
            if '<html' not in response.text.lower():
                content_valid = False
                content_issues.append('No HTML structure found')
            
            # Check for Django error pages
            if 'Server Error (500)' in response.text or 'Page not found (404)' in response.text:
                content_valid = False
                content_issues.append('Django error page detected')
            
            # Check for expected title keywords if provided
            if expected_title_keywords:
                title_found = False
                for keyword in expected_title_keywords:
                    if keyword.lower() in response.text.lower():
                        title_found = True
                        break
                if not title_found:
                    content_issues.append(f'Expected keywords not found: {expected_title_keywords}')
            
            # Check for navigation elements (sidebar)
            if 'sidebar' not in response.text.lower() and 'nav' not in response.text.lower():
                content_issues.append('No navigation elements found')
            
            return {
                'endpoint': endpoint,
                'status': 'PASSED' if content_valid else 'FAILED',
                'status_code': response.status_code,
                'content_check': content_valid,
                'content_issues': content_issues,
                'response_size': len(response.text)
            }
            
        except Exception as e:
            return {
                'endpoint': endpoint,
                'status': 'ERROR',
                'error': str(e),
                'content_check': False
            }
    
    def run_all_tests(self):
        """Run all endpoint tests"""
        print(f"🚀 Starting Elvis-Manager ERP Backend Tests")
        print(f"📍 Base URL: {self.base_url}")
        print(f"👤 Username: {self.username}")
        print("=" * 60)
        
        # Login first
        if not self.login():
            print("❌ Cannot proceed without successful login")
            return False
        
        print("\n📋 Testing Endpoints...")
        print("=" * 60)
        
        # Define test endpoints with expected content
        test_cases = [
            # Segmentation Module
            {
                'endpoint': '/segmentation/',
                'name': 'Segmentation Dashboard',
                'keywords': ['segmentation', 'dashboard', 'customer']
            },
            {
                'endpoint': '/segmentation/profiles/',
                'name': 'Customer Profiles',
                'keywords': ['profile', 'customer', 'list']
            },
            {
                'endpoint': '/segmentation/segments/',
                'name': 'Segments List',
                'keywords': ['segment', 'list', 'customer']
            },
            {
                'endpoint': '/segmentation/cohorts/',
                'name': 'Cohort Analysis',
                'keywords': ['cohort', 'analysis', 'customer']
            },
            
            # Inventory Module
            {
                'endpoint': '/inventory/',
                'name': 'Inventory Dashboard',
                'keywords': ['inventory', 'dashboard', 'stock']
            },
            {
                'endpoint': '/inventory/warehouses/',
                'name': 'Warehouse List',
                'keywords': ['warehouse', 'list', 'inventory']
            },
            {
                'endpoint': '/inventory/stock/',
                'name': 'Stock Levels',
                'keywords': ['stock', 'level', 'inventory']
            },
            {
                'endpoint': '/inventory/movements/',
                'name': 'Stock Movements',
                'keywords': ['movement', 'stock', 'inventory']
            },
            {
                'endpoint': '/inventory/transfers/',
                'name': 'Stock Transfers',
                'keywords': ['transfer', 'stock', 'inventory']
            },
            
            # Logistics Module
            {
                'endpoint': '/logistics/panel/',
                'name': 'Logistics Panel',
                'keywords': ['logistics', 'panel', 'shipping']
            },
            {
                'endpoint': '/logistics/ndr/',
                'name': 'NDR Management',
                'keywords': ['ndr', 'management', 'logistics']
            },
            {
                'endpoint': '/logistics/rules/',
                'name': 'Shipping Rules',
                'keywords': ['rule', 'shipping', 'logistics']
            },
            {
                'endpoint': '/logistics/carriers/',
                'name': 'Carriers',
                'keywords': ['carrier', 'logistics', 'shipping']
            },
            {
                'endpoint': '/logistics/shipments/',
                'name': 'Shipments',
                'keywords': ['shipment', 'logistics', 'shipping']
            },
            
            # User Management
            {
                'endpoint': '/accounts/users/',
                'name': 'Users List',
                'keywords': ['user', 'list', 'account']
            },
            
            # Master Accounts
            {
                'endpoint': '/master/accounts/',
                'name': 'Accounts List',
                'keywords': ['account', 'list', 'master']
            }
        ]
        
        results = []
        passed = 0
        failed = 0
        
        for test_case in test_cases:
            print(f"\n🧪 Testing: {test_case['name']}")
            print(f"   Endpoint: {test_case['endpoint']}")
            
            result = self.test_endpoint(test_case['endpoint'], test_case['keywords'])
            result['name'] = test_case['name']
            results.append(result)
            
            if result['status'] == 'PASSED':
                print(f"   ✅ PASSED - Status: {result['status_code']}, Size: {result.get('response_size', 0)} bytes")
                passed += 1
            else:
                print(f"   ❌ FAILED - {result.get('error', 'Content validation failed')}")
                if result.get('content_issues'):
                    for issue in result['content_issues']:
                        print(f"      • {issue}")
                failed += 1
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📈 Success Rate: {(passed/(passed+failed)*100):.1f}%")
        
        # Detailed results
        print("\n📋 DETAILED RESULTS:")
        print("-" * 60)
        for result in results:
            status_icon = "✅" if result['status'] == 'PASSED' else "❌"
            print(f"{status_icon} {result['name']:<25} | {result['endpoint']:<25} | {result['status']}")
            if result['status'] != 'PASSED' and result.get('content_issues'):
                for issue in result['content_issues']:
                    print(f"   └─ {issue}")
        
        return passed == len(test_cases)
    
    def test_whatsapp_webhook_verification(self):
        """Test WhatsApp webhook verification (GET endpoint)"""
        print("\n🔍 Testing WhatsApp Webhook Verification...")
        
        # Test with correct token
        verify_url = f"{self.base_url}/webhooks/whatsapp/"
        params_correct = {
            'hub.mode': 'subscribe',
            'hub.verify_token': 'elvis_whatsapp_verify_2024',
            'hub.challenge': 'test123'
        }
        
        try:
            response = requests.get(verify_url, params=params_correct)
            if response.status_code == 200 and response.text == 'test123':
                print("✅ Webhook verification with correct token: PASSED")
                correct_token_result = True
            else:
                print(f"❌ Webhook verification with correct token: FAILED - Status: {response.status_code}, Response: {response.text}")
                correct_token_result = False
        except Exception as e:
            print(f"❌ Webhook verification with correct token: ERROR - {str(e)}")
            correct_token_result = False
        
        # Test with wrong token
        params_wrong = {
            'hub.mode': 'subscribe',
            'hub.verify_token': 'wrong_token',
            'hub.challenge': 'test123'
        }
        
        try:
            response = requests.get(verify_url, params=params_wrong)
            if response.status_code == 403:
                print("✅ Webhook verification with wrong token: PASSED (correctly rejected)")
                wrong_token_result = True
            else:
                print(f"❌ Webhook verification with wrong token: FAILED - Status: {response.status_code}, Expected: 403")
                wrong_token_result = False
        except Exception as e:
            print(f"❌ Webhook verification with wrong token: ERROR - {str(e)}")
            wrong_token_result = False
        
        return correct_token_result and wrong_token_result
    
    def test_whatsapp_message_reception(self):
        """Test WhatsApp webhook message reception (POST endpoint)"""
        print("\n📨 Testing WhatsApp Message Reception...")
        
        webhook_url = f"{self.base_url}/webhooks/whatsapp/"
        
        # Sample WhatsApp message payload from review request
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "123456789",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "919876543210",
                            "phone_number_id": "test_phone_001"
                        },
                        "contacts": [{"profile": {"name": "Test Lead"}, "wa_id": "919999888877"}],
                        "messages": [{
                            "from": "919999888877",
                            "id": "msg_test_unique_001",
                            "timestamp": "1707590000",
                            "type": "text",
                            "text": {"body": "Hello testing!"}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        
        try:
            response = requests.post(
                webhook_url, 
                json=payload, 
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200 and response.text == 'OK':
                print("✅ WhatsApp message reception: PASSED")
                return True
            else:
                print(f"❌ WhatsApp message reception: FAILED - Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ WhatsApp message reception: ERROR - {str(e)}")
            return False
    
    def test_customer_deduplication(self):
        """Test customer deduplication across multiple sales numbers"""
        print("\n👥 Testing Customer Deduplication...")
        
        webhook_url = f"{self.base_url}/webhooks/whatsapp/"
        
        # First message to phone_number_id_1
        payload1 = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "123456789",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "919876543210",
                            "phone_number_id": "test_phone_001"
                        },
                        "contacts": [{"profile": {"name": "Test Dedup Lead"}, "wa_id": "919999888866"}],
                        "messages": [{
                            "from": "919999888866",
                            "id": "msg_dedup_001",
                            "timestamp": "1707590100",
                            "type": "text",
                            "text": {"body": "First message to sales 1"}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        
        # Second message from same wa_id to different phone_number_id
        payload2 = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "123456789",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "919876543211",
                            "phone_number_id": "test_phone_002"
                        },
                        "contacts": [{"profile": {"name": "Test Dedup Lead"}, "wa_id": "919999888866"}],
                        "messages": [{
                            "from": "919999888866",
                            "id": "msg_dedup_002",
                            "timestamp": "1707590200",
                            "type": "text",
                            "text": {"body": "Second message to sales 2"}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        
        try:
            # Send first message
            response1 = requests.post(webhook_url, json=payload1, headers={'Content-Type': 'application/json'})
            if response1.status_code != 200:
                print(f"❌ First dedup message failed: {response1.status_code}")
                return False
            
            # Send second message
            response2 = requests.post(webhook_url, json=payload2, headers={'Content-Type': 'application/json'})
            if response2.status_code != 200:
                print(f"❌ Second dedup message failed: {response2.status_code}")
                return False
                
            print("✅ Customer deduplication test messages sent successfully")
            print("   (Should create 1 WhatsAppCustomer + 2 WhatsAppCustomerChannel records)")
            return True
            
        except Exception as e:
            print(f"❌ Customer deduplication test: ERROR - {str(e)}")
            return False
    
    def test_ad_attribution(self):
        """Test Click-to-WhatsApp ad attribution"""
        print("\n🎯 Testing Ad Attribution...")
        
        webhook_url = f"{self.base_url}/webhooks/whatsapp/"
        
        # Message with referral data (CTWA ad)
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "123456789",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "919876543210",
                            "phone_number_id": "test_phone_ad"
                        },
                        "contacts": [{"profile": {"name": "Ad Lead"}, "wa_id": "919999888855"}],
                        "messages": [{
                            "from": "919999888855",
                            "id": "msg_ad_001",
                            "timestamp": "1707590300",
                            "type": "text",
                            "text": {"body": "Hello from ad!"},
                            "referral": {
                                "source_type": "ad",
                                "source_id": "123456",
                                "headline": "Test Ad Headline",
                                "body": "Test Ad Body",
                                "ctwa_clid": "test_click_id_123"
                            }
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        
        try:
            response = requests.post(webhook_url, json=payload, headers={'Content-Type': 'application/json'})
            
            if response.status_code == 200:
                print("✅ Ad attribution test: PASSED")
                print("   (Customer should have is_from_ad=True and meta_ad_headline captured)")
                return True
            else:
                print(f"❌ Ad attribution test: FAILED - Status: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Ad attribution test: ERROR - {str(e)}")
            return False
    
    def test_ui_pages(self):
        """Test WhatsApp UI pages (authenticated)"""
        print("\n🌐 Testing WhatsApp UI Pages...")
        
        if not self.login():
            print("❌ Cannot test UI pages without login")
            return False
        
        ui_pages = [
            {
                'url': '/integrations/whatsapp/',
                'name': 'WhatsApp Dashboard',
                'keywords': ['whatsapp', 'webhook', 'integration']
            },
            {
                'url': '/integrations/whatsapp/customers/',
                'name': 'WhatsApp Customers',
                'keywords': ['whatsapp', 'customer', 'lead']
            },
            {
                'url': '/marketing/leads/',
                'name': 'All Leads Page',
                'keywords': ['lead', 'marketing', 'list']
            }
        ]
        
        results = []
        for page in ui_pages:
            try:
                response = self.session.get(f"{self.base_url}{page['url']}")
                
                if response.status_code == 200:
                    # Basic content checks
                    content_valid = True
                    issues = []
                    
                    if not any(keyword.lower() in response.text.lower() for keyword in page['keywords']):
                        issues.append(f"Missing expected keywords: {page['keywords']}")
                        content_valid = False
                    
                    if '<html' not in response.text.lower():
                        issues.append("No HTML structure found")
                        content_valid = False
                    
                    status = "PASSED" if content_valid else "FAILED"
                    print(f"   {'✅' if content_valid else '❌'} {page['name']}: {status}")
                    
                    if issues:
                        for issue in issues:
                            print(f"      • {issue}")
                    
                    results.append(content_valid)
                else:
                    print(f"   ❌ {page['name']}: FAILED - Status: {response.status_code}")
                    results.append(False)
                    
            except Exception as e:
                print(f"   ❌ {page['name']}: ERROR - {str(e)}")
                results.append(False)
        
        return all(results)
    
    def test_sidebar_navigation(self):
        """Test sidebar navigation for WhatsApp sections"""
        print("\n🧭 Testing Sidebar Navigation...")
        
        if not self.login():
            print("❌ Cannot test sidebar without login")
            return False
        
        try:
            # Get the main page to check sidebar
            response = self.session.get(f"{self.base_url}/")
            
            if response.status_code != 200:
                print(f"❌ Cannot access main page: {response.status_code}")
                return False
            
            # Check for WhatsApp navigation items
            navigation_items = [
                'WhatsApp Leads',  # Under Marketing section
                'WhatsApp Setup'   # Under Integrations section
            ]
            
            found_items = []
            for item in navigation_items:
                if item.lower() in response.text.lower():
                    found_items.append(item)
                    print(f"   ✅ Found: {item}")
                else:
                    print(f"   ❌ Missing: {item}")
            
            success = len(found_items) == len(navigation_items)
            print(f"   Overall: {'✅ PASSED' if success else '❌ FAILED'} - {len(found_items)}/{len(navigation_items)} items found")
            
            return success
            
        except Exception as e:
            print(f"❌ Sidebar navigation test: ERROR - {str(e)}")
            return False
    
    def run_whatsapp_tests(self):
        """Run all WhatsApp-specific tests"""
        print(f"🚀 Starting WhatsApp Lead Auto-Save Backend Tests")
        print(f"📍 Base URL: {self.base_url}")
        print(f"👤 Username: {self.username}")
        print("=" * 60)
        
        test_results = {}
        
        # Run individual tests
        print("\n🧪 Running WhatsApp Feature Tests...")
        print("=" * 60)
        
        test_results['webhook_verification'] = self.test_whatsapp_webhook_verification()
        test_results['message_reception'] = self.test_whatsapp_message_reception()
        test_results['customer_deduplication'] = self.test_customer_deduplication()
        test_results['ad_attribution'] = self.test_ad_attribution()
        test_results['ui_pages'] = self.test_ui_pages()
        test_results['sidebar_navigation'] = self.test_sidebar_navigation()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 WHATSAPP TESTS SUMMARY")
        print("=" * 60)
        
        passed = sum(test_results.values())
        total = len(test_results)
        
        for test_name, result in test_results.items():
            icon = "✅" if result else "❌"
            status = "PASSED" if result else "FAILED"
            print(f"{icon} {test_name.replace('_', ' ').title()}: {status}")
        
        print(f"\n📈 Success Rate: {(passed/total*100):.1f}% ({passed}/{total})")
        
        return passed == total

def main():
    """Main test execution"""
    # Configuration from review request
    BASE_URL = "http://localhost:8001"
    USERNAME = "admin"
    PASSWORD = "admin123"
    
    print("🎯 WhatsApp Lead Auto-Save Test Suite")
    print("=" * 60)
    
    # Initialize tester
    tester = WhatsAppERPTester(BASE_URL, USERNAME, PASSWORD)
    
    # Run WhatsApp tests
    success = tester.run_whatsapp_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()