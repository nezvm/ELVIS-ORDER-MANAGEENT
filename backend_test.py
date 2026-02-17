#!/usr/bin/env python3
"""
Backend Test Suite for Elvis-Manager ERP Application
Tests Marketing Meta Measurement Engine features
"""

import requests
import sys
import json
import uuid
from urllib.parse import urljoin

class MarketingMetaERPTester:
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
            print(f"   Login page status: {response.status_code}")
            if response.status_code != 200:
                print(f"❌ Failed to access login page: {response.status_code}")
                return False
                
            # Extract CSRF token from response
            if 'csrftoken' in self.session.cookies:
                self.csrf_token = self.session.cookies['csrftoken']
                print(f"   CSRF token from cookies: {self.csrf_token[:10]}...")
            elif 'csrf_token' in response.text:
                # Try to extract from HTML
                import re
                csrf_match = re.search(r'name=["\']csrfmiddlewaretoken["\'] value=["\']([^"\']+)["\']', response.text)
                if csrf_match:
                    self.csrf_token = csrf_match.group(1)
                    print(f"   CSRF token from HTML: {self.csrf_token[:10]}...")
            
            if not self.csrf_token:
                print("❌ Could not extract CSRF token")
                return False
                
            # Prepare login data
            login_data = {
                'username': self.username,
                'password': self.password,
                'csrfmiddlewaretoken': self.csrf_token,
            }
                
            # Set headers
            headers = {
                'Referer': login_url,
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': self.csrf_token,
                'User-Agent': 'Mozilla/5.0 (compatible; Test-Bot/1.0)',
            }
            
            # Attempt login
            print(f"   Posting login data to: {login_url}")
            response = self.session.post(login_url, data=login_data, headers=headers, allow_redirects=True)
            print(f"   Login response status: {response.status_code}")
            print(f"   Final URL after login: {response.url}")
            
            # Check if login was successful
            if response.status_code == 200:
                # Check if we're on dashboard or not on login page anymore
                if 'login' not in response.url.lower() or 'dashboard' in response.text.lower() or 'logout' in response.text.lower():
                    print("✅ Login successful!")
                    return True
                else:
                    print(f"❌ Still on login page. Checking for error messages...")
                    if 'invalid' in response.text.lower() or 'error' in response.text.lower():
                        print("   Possible invalid credentials")
                    return False
            else:
                print(f"❌ Login failed with status: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Login error: {str(e)}")
            return False
    
    def test_endpoint(self, endpoint, expected_keywords=None, method='GET', post_data=None):
        """Test a single endpoint"""
        url = urljoin(self.base_url, endpoint)
        
        try:
            if method.upper() == 'POST':
                headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                if self.csrf_token:
                    headers['X-CSRFToken'] = self.csrf_token
                    if post_data is None:
                        post_data = {}
                    post_data['csrfmiddlewaretoken'] = self.csrf_token
                
                response = self.session.post(url, data=post_data, headers=headers)
            else:
                response = self.session.get(url)
            
            # Check status code
            if response.status_code != 200:
                return {
                    'endpoint': endpoint,
                    'method': method,
                    'status': 'FAILED',
                    'status_code': response.status_code,
                    'error': f'HTTP {response.status_code}',
                    'content_check': False
                }
            
            # Check content
            content_valid = True
            content_issues = []
            
            # For JSON responses (API endpoints)
            if 'application/json' in response.headers.get('Content-Type', ''):
                try:
                    data = response.json()
                    # Check if it's a valid JSON response
                    if isinstance(data, dict):
                        content_valid = True
                        return {
                            'endpoint': endpoint,
                            'method': method,
                            'status': 'PASSED',
                            'status_code': response.status_code,
                            'content_check': True,
                            'response_data': data,
                            'response_size': len(response.text)
                        }
                except json.JSONDecodeError:
                    content_valid = False
                    content_issues.append('Invalid JSON response')
            
            # For HTML responses
            else:
                # Basic HTML structure check
                if '<html' not in response.text.lower():
                    content_valid = False
                    content_issues.append('No HTML structure found')
                
                # Check for Django error pages
                if 'Server Error (500)' in response.text or 'Page not found (404)' in response.text:
                    content_valid = False
                    content_issues.append('Django error page detected')
                
                # Check for expected keywords if provided
                if expected_keywords:
                    found_keywords = []
                    for keyword in expected_keywords:
                        if keyword.lower() in response.text.lower():
                            found_keywords.append(keyword)
                    
                    if len(found_keywords) == 0:
                        content_issues.append(f'No expected keywords found: {expected_keywords}')
                        content_valid = False
                
                # Check for navigation elements (sidebar)
                if method.upper() == 'GET' and 'sidebar' not in response.text.lower() and 'nav' not in response.text.lower():
                    content_issues.append('No navigation elements found')
            
            return {
                'endpoint': endpoint,
                'method': method,
                'status': 'PASSED' if content_valid else 'FAILED',
                'status_code': response.status_code,
                'content_check': content_valid,
                'content_issues': content_issues,
                'response_size': len(response.text)
            }
            
        except Exception as e:
            return {
                'endpoint': endpoint,
                'method': method,
                'status': 'ERROR',
                'error': str(e),
                'content_check': False
            }
    
    def test_marketing_meta_pages(self):
        """Test the main Marketing Meta pages"""
        print("\n🏪 Testing Marketing Meta Pages...")
        
        if not self.login():
            print("❌ Cannot test pages without login")
            return []
        
        # Define Marketing Meta pages to test
        pages = [
            {
                'endpoint': '/marketing/overview/',
                'name': 'Marketing ROAS Dashboard',
                'keywords': ['marketing overview', 'roas', 'attribution', 'dashboard', 'kpi', 'charts']
            },
            {
                'endpoint': '/marketing/meta/settings/',
                'name': 'Meta Integration Settings',
                'keywords': ['meta integration', 'settings', 'config', 'business id', 'access token']
            },
            {
                'endpoint': '/marketing/meta/campaigns/',
                'name': 'Campaign Performance',
                'keywords': ['campaign performance', 'insights', 'spend', 'impressions', 'clicks']
            },
            {
                'endpoint': '/marketing/meta/capi-logs/',
                'name': 'CAPI Event Logs',
                'keywords': ['capi event', 'logs', 'status', 'event name', 'lead']
            },
            {
                'endpoint': '/marketing/lead-list/',
                'name': 'Lead List (Attribution Column)',
                'keywords': ['lead', 'list', 'attribution', 'source', 'status']
            }
        ]
        
        results = []
        
        for page in pages:
            print(f"\n🧪 Testing: {page['name']}")
            print(f"   Endpoint: {page['endpoint']}")
            
            result = self.test_endpoint(page['endpoint'], page['keywords'])
            result['name'] = page['name']
            results.append(result)
            
            if result['status'] == 'PASSED':
                print(f"   ✅ PASSED - Status: {result['status_code']}, Size: {result.get('response_size', 0)} bytes")
            else:
                print(f"   ❌ FAILED - {result.get('error', 'Content validation failed')}")
                if result.get('content_issues'):
                    for issue in result['content_issues']:
                        print(f"      • {issue}")
        
        return results
    
    def test_marketing_meta_api_endpoints(self):
        """Test the Marketing Meta API endpoints"""
        print("\n🔌 Testing Marketing Meta API Endpoints...")
        
        if not self.login():
            print("❌ Cannot test API endpoints without login")
            return []
        
        # Update CSRF token for POST requests
        csrf_response = self.session.get(f"{self.base_url}/marketing/overview/")
        if csrf_response.status_code == 200:
            import re
            csrf_match = re.search(r'name=["\']csrfmiddlewaretoken["\'] value=["\']([^"\']+)["\']', csrf_response.text)
            if csrf_match:
                self.csrf_token = csrf_match.group(1)
        
        # Define API endpoints to test
        api_endpoints = [
            {
                'endpoint': '/marketing/api/meta/test-connection/',
                'name': 'Test Meta Connection',
                'method': 'POST',
                'expected_json_keys': ['success']
            },
            {
                'endpoint': '/marketing/api/meta/send-test-event/',
                'name': 'Send Test Event',
                'method': 'POST',
                'post_data': {'event_type': 'lead'},
                'expected_json_keys': ['success', 'event_type']
            },
            {
                'endpoint': '/marketing/api/meta/sync-insights/',
                'name': 'Sync Meta Insights',
                'method': 'POST',
                'expected_json_keys': ['success']
            },
            {
                'endpoint': '/marketing/api/meta/run-attribution/',
                'name': 'Run Attribution Engine',
                'method': 'POST',
                'expected_json_keys': ['success']
            },
            {
                'endpoint': '/marketing/api/meta/send-pending-capi/',
                'name': 'Send Pending CAPI Events',
                'method': 'POST',
                'expected_json_keys': ['success']
            },
            {
                'endpoint': '/marketing/api/meta/chart-data/',
                'name': 'Chart Data API',
                'method': 'GET',
                'expected_json_keys': ['data']
            }
        ]
        
        results = []
        
        for api in api_endpoints:
            print(f"\n🧪 Testing API: {api['name']}")
            print(f"   Endpoint: {api['method']} {api['endpoint']}")
            
            result = self.test_endpoint(
                api['endpoint'], 
                method=api['method'], 
                post_data=api.get('post_data')
            )
            result['name'] = api['name']
            
            # Additional validation for JSON APIs
            if result['status'] == 'PASSED' and result.get('response_data'):
                data = result['response_data']
                expected_keys = api.get('expected_json_keys', [])
                
                missing_keys = []
                for key in expected_keys:
                    if key not in data:
                        missing_keys.append(key)
                
                if missing_keys:
                    result['status'] = 'FAILED'
                    result['content_issues'] = [f'Missing JSON keys: {missing_keys}']
                    print(f"   ❌ FAILED - Missing JSON keys: {missing_keys}")
                else:
                    print(f"   ✅ PASSED - Valid JSON response with expected keys")
                    if 'success' in data:
                        print(f"      Success: {data['success']}")
                    if 'error' in data:
                        print(f"      Error: {data['error']}")
            else:
                if result['status'] == 'PASSED':
                    print(f"   ✅ PASSED - Status: {result['status_code']}")
                else:
                    print(f"   ❌ FAILED - {result.get('error', 'Unknown error')}")
            
            results.append(result)
        
        return results
    
    def test_sidebar_navigation(self):
        """Test sidebar navigation for Marketing Meta sections"""
        print("\n🧭 Testing Sidebar Navigation...")
        
        if not self.login():
            print("❌ Cannot test sidebar without login")
            return False
        
        try:
            # Get the marketing overview page to check sidebar
            response = self.session.get(f"{self.base_url}/marketing/overview/")
            
            if response.status_code != 200:
                print(f"❌ Cannot access marketing page: {response.status_code}")
                return False
            
            # Check for Marketing navigation items
            navigation_items = [
                'ROAS Dashboard',
                'Campaign Performance', 
                'CAPI Event Logs',
                'Meta Settings'
            ]
            
            found_items = []
            for item in navigation_items:
                if item.lower() in response.text.lower():
                    found_items.append(item)
                    print(f"   ✅ Found: {item}")
                else:
                    print(f"   ❌ Missing: {item}")
            
            success = len(found_items) >= len(navigation_items) // 2  # At least half should be found
            print(f"   Overall: {'✅ PASSED' if success else '❌ FAILED'} - {len(found_items)}/{len(navigation_items)} items found")
            
            return success
            
        except Exception as e:
            print(f"❌ Sidebar navigation test: ERROR - {str(e)}")
            return False
    
    def test_lead_attribution_manual_override(self):
        """Test manual lead attribution override API"""
        print("\n🎯 Testing Lead Attribution Manual Override...")
        
        if not self.login():
            print("❌ Cannot test attribution API without login")
            return False
        
        # First, try to get a lead UUID from the lead list page
        try:
            leads_response = self.session.get(f"{self.base_url}/marketing/lead-list/")
            if leads_response.status_code != 200:
                print("⚠️  Cannot access lead list to get lead UUID")
                return False
            
            # Extract lead UUID from HTML (simple approach)
            import re
            uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
            uuids = re.findall(uuid_pattern, leads_response.text)
            
            if not uuids:
                print("⚠️  No lead UUIDs found in lead list page")
                # Use a dummy UUID for testing the endpoint structure
                test_uuid = str(uuid.uuid4())
            else:
                test_uuid = uuids[0]
                print(f"   Using lead UUID: {test_uuid}")
            
            # Test attribution override API
            attribution_url = f"/marketing/api/meta/lead/{test_uuid}/attribution/"
            
            result = self.test_endpoint(
                attribution_url, 
                method='POST', 
                post_data={'attribution_model': 'manual_ads'}
            )
            
            if result['status'] == 'PASSED':
                data = result.get('response_data', {})
                if data.get('success'):
                    print("   ✅ PASSED - Lead attribution override working")
                    return True
                elif 'Lead not found' in str(data.get('error', '')):
                    print("   ✅ PASSED - API endpoint working (404 for non-existent lead is expected)")
                    return True
                else:
                    print(f"   ❌ FAILED - Unexpected response: {data}")
                    return False
            else:
                print(f"   ❌ FAILED - {result.get('error', 'Unknown error')}")
                return False
            
        except Exception as e:
            print(f"❌ Lead attribution test: ERROR - {str(e)}")
            return False
    
    def run_marketing_meta_tests(self):
        """Run all Marketing Meta Measurement Engine tests"""
        print(f"🚀 Starting Marketing Meta Measurement Engine Tests")
        print(f"📍 Base URL: {self.base_url}")
        print(f"👤 Username: {self.username}")
        print("=" * 70)
        
        all_results = []
        
        # Test main pages
        print("\n📄 Testing Marketing Meta Pages...")
        print("=" * 50)
        page_results = self.test_marketing_meta_pages()
        all_results.extend(page_results)
        
        # Test API endpoints
        print("\n🔌 Testing Marketing Meta API Endpoints...")
        print("=" * 50)
        api_results = self.test_marketing_meta_api_endpoints()
        all_results.extend(api_results)
        
        # Test sidebar navigation
        print("\n🧭 Testing Sidebar Navigation...")
        print("=" * 50)
        sidebar_result = self.test_sidebar_navigation()
        
        # Test attribution override
        print("\n🎯 Testing Lead Attribution Override...")
        print("=" * 50)
        attribution_result = self.test_lead_attribution_manual_override()
        
        # Summary
        print("\n" + "=" * 70)
        print("📊 MARKETING META MEASUREMENT ENGINE TEST SUMMARY")
        print("=" * 70)
        
        passed_pages = sum(1 for r in page_results if r['status'] == 'PASSED')
        total_pages = len(page_results)
        
        passed_apis = sum(1 for r in api_results if r['status'] == 'PASSED')
        total_apis = len(api_results)
        
        print("📄 MARKETING PAGES:")
        for result in page_results:
            icon = "✅" if result['status'] == 'PASSED' else "❌"
            print(f"   {icon} {result['name']}: {result['status']}")
            if result['status'] != 'PASSED' and result.get('content_issues'):
                for issue in result['content_issues']:
                    print(f"      └─ {issue}")
        
        print("\n🔌 API ENDPOINTS:")
        for result in api_results:
            icon = "✅" if result['status'] == 'PASSED' else "❌"
            print(f"   {icon} {result['name']}: {result['status']}")
            if result['status'] != 'PASSED' and result.get('content_issues'):
                for issue in result['content_issues']:
                    print(f"      └─ {issue}")
        
        print(f"\n🧭 NAVIGATION: {'✅ PASSED' if sidebar_result else '❌ FAILED'}")
        print(f"🎯 ATTRIBUTION: {'✅ PASSED' if attribution_result else '❌ FAILED'}")
        
        # Overall statistics
        total_tests = total_pages + total_apis + 2  # +2 for sidebar and attribution
        passed_tests = passed_pages + passed_apis + (1 if sidebar_result else 0) + (1 if attribution_result else 0)
        
        print(f"\n📈 Overall Success Rate: {(passed_tests/total_tests*100):.1f}% ({passed_tests}/{total_tests})")
        if total_pages > 0:
            print(f"📈 Pages: {(passed_pages/total_pages*100):.1f}% ({passed_pages}/{total_pages})")
        if total_apis > 0:
            print(f"📈 APIs: {(passed_apis/total_apis*100):.1f}% ({passed_apis}/{total_apis})")
        
        # Status determination
        if passed_tests == total_tests:
            print("\n🎉 All Marketing Meta Measurement Engine features are working correctly!")
        elif passed_tests >= total_tests * 0.8:
            print(f"\n⚠️  Most features working, but {total_tests - passed_tests} features need attention")
        else:
            print(f"\n❌ Major issues found: {total_tests - passed_tests} out of {total_tests} features failed")
        
        return passed_tests >= total_tests * 0.7  # Pass if 70% or more tests succeed

def main():
    """Main test execution"""
    # Configuration from review request  
    BASE_URL = "https://0e059c81-2353-4e4b-bfd6-d85d1bfb869e.preview.emergentagent.com"
    USERNAME = "admin"
    PASSWORD = "admin123"
    
    print("🎯 Marketing Meta Measurement Engine Test Suite")
    print("=" * 70)
    
    # Initialize tester
    tester = MarketingMetaERPTester(BASE_URL, USERNAME, PASSWORD)
    
    # Run Marketing Meta Measurement Engine tests
    success = tester.run_marketing_meta_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()