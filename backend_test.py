#!/usr/bin/env python3
"""
Backend Test Suite for Elvis-Manager ERP Application
Tests all new frontend pages and backend endpoints
"""

import requests
import sys
import json
from urllib.parse import urljoin

class ElvisERPTester:
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

def main():
    """Main test execution"""
    # Configuration from review request
    BASE_URL = "https://modular-elvis.preview.emergentagent.com"
    USERNAME = "admin"
    PASSWORD = "admin123"
    
    print("🎯 Elvis-Manager ERP Backend Test Suite")
    print("=" * 60)
    
    # Initialize tester
    tester = ElvisERPTester(BASE_URL, USERNAME, PASSWORD)
    
    # Run tests
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()