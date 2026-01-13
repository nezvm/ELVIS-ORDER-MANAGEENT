#!/usr/bin/env python3
"""
Debug test for cohort analysis endpoint
"""

import requests
import sys
from urllib.parse import urljoin

def test_cohort_endpoint():
    base_url = "https://381c6107-1537-4edc-9827-0f764c1c1d3f.preview.emergentagent.com"
    session = requests.Session()
    
    print("🔍 Debugging Cohort Analysis Endpoint")
    print("=" * 50)
    
    # Step 1: Get login page
    print("1. Getting login page...")
    login_url = urljoin(base_url, '/accounts/login/')
    response = session.get(login_url)
    print(f"   Status: {response.status_code}")
    
    # Step 2: Extract CSRF token
    csrf_token = None
    if 'csrftoken' in session.cookies:
        csrf_token = session.cookies['csrftoken']
        print(f"   CSRF Token: {csrf_token[:20]}...")
    
    # Step 3: Login
    print("2. Logging in...")
    login_data = {
        'username': 'admin',
        'password': 'admin123',
    }
    
    if csrf_token:
        login_data['csrfmiddlewaretoken'] = csrf_token
    
    headers = {
        'Referer': login_url,
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    
    if csrf_token:
        headers['X-CSRFToken'] = csrf_token
    
    response = session.post(login_url, data=login_data, headers=headers, allow_redirects=False)
    print(f"   Login Status: {response.status_code}")
    
    # Step 4: Test cohort endpoint
    print("3. Testing cohort endpoint...")
    cohort_url = urljoin(base_url, '/segmentation/cohorts/')
    
    try:
        response = session.get(cohort_url, timeout=30)
        print(f"   Status: {response.status_code}")
        print(f"   URL: {response.url}")
        print(f"   Content Length: {len(response.text)}")
        
        if response.status_code != 200:
            print(f"   Response Headers: {dict(response.headers)}")
            if len(response.text) < 1000:
                print(f"   Response Content: {response.text}")
        else:
            print("   ✅ Success!")
            
    except requests.exceptions.Timeout:
        print("   ❌ Timeout after 30 seconds")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")

if __name__ == "__main__":
    test_cohort_endpoint()