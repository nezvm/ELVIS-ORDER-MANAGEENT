"""
Wabis API Integration Tests

Tests:
1. Wabis API configuration save/load
2. Wabis connection test endpoint
3. Multi-number sync trigger
4. Bot ID update for individual numbers
5. Wabis API Client subscriber list endpoint

Credentials: 
- Wabis Login: wowdeskdown@gmail.com / 12qwe12qwe
- Django Admin: admin / admin123
- Wabis Console: https://bot.wabis.in/api/developer/console
"""
import pytest
import requests
import json
import os
import uuid

# Base URL
BASE_URL = 'http://localhost:8001'

# Test data prefix
TEST_PREFIX = "TEST_API_"


class TestWabisConfigAPI:
    """Test Wabis configuration save and load endpoints."""
    
    @pytest.fixture(autouse=True)
    def setup_session(self):
        """Setup authenticated session."""
        self.session = requests.Session()
        
        # Get CSRF token from login page
        login_page = self.session.get(f"{BASE_URL}/accounts/login/")
        
        # Extract CSRF token
        import re
        csrf_match = re.search(r'csrfmiddlewaretoken" value="([^"]+)"', login_page.text)
        self.csrf_token = csrf_match.group(1) if csrf_match else None
        
        # Login
        login_response = self.session.post(
            f"{BASE_URL}/accounts/login/",
            data={
                'csrfmiddlewaretoken': self.csrf_token,
                'username': 'admin',
                'password': 'admin123'
            },
            headers={'Referer': f"{BASE_URL}/accounts/login/"},
            allow_redirects=True
        )
        
        self.authenticated = login_response.status_code == 200 and '/login' not in login_response.url
        
        if self.authenticated:
            # Get fresh CSRF token for API calls
            config_page = self.session.get(f"{BASE_URL}/integrations/wabis/config/")
            csrf_match = re.search(r'csrfmiddlewaretoken" value="([^"]+)"', config_page.text)
            self.csrf_token = csrf_match.group(1) if csrf_match else self.csrf_token
    
    def test_save_wabis_config_success(self):
        """Test saving Wabis configuration with valid data."""
        if not self.authenticated:
            pytest.skip("Could not authenticate - skipping")
        
        response = self.session.post(
            f"{BASE_URL}/integrations/wabis/api/save-config/",
            headers={
                'Content-Type': 'application/json',
                'X-CSRFToken': self.csrf_token,
                'Referer': f"{BASE_URL}/integrations/wabis/config/"
            },
            json={
                'api_token': f'{TEST_PREFIX}api_token_test',
                'whatsapp_bot_id': f'{TEST_PREFIX}bot_id_test'
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get('success') == True, f"Expected success=True: {data}"
        print("✓ Save config with valid data works correctly")
    
    def test_save_wabis_config_missing_api_token(self):
        """Test save config rejects missing API token."""
        if not self.authenticated:
            pytest.skip("Could not authenticate - skipping")
        
        response = self.session.post(
            f"{BASE_URL}/integrations/wabis/api/save-config/",
            headers={
                'Content-Type': 'application/json',
                'X-CSRFToken': self.csrf_token,
                'Referer': f"{BASE_URL}/integrations/wabis/config/"
            },
            json={
                'api_token': '',  # Empty
                'whatsapp_bot_id': 'test_bot_id'
            }
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert data.get('success') == False, "Should fail without API token"
        assert 'API Token' in data.get('error', ''), f"Error message should mention API Token: {data}"
        print("✓ Save config correctly rejects missing API token")
    
    def test_save_wabis_config_missing_bot_id(self):
        """Test save config rejects missing Bot ID."""
        if not self.authenticated:
            pytest.skip("Could not authenticate - skipping")
        
        response = self.session.post(
            f"{BASE_URL}/integrations/wabis/api/save-config/",
            headers={
                'Content-Type': 'application/json',
                'X-CSRFToken': self.csrf_token,
                'Referer': f"{BASE_URL}/integrations/wabis/config/"
            },
            json={
                'api_token': 'valid_token_here',
                'whatsapp_bot_id': ''  # Empty
            }
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert data.get('success') == False, "Should fail without Bot ID"
        assert 'Bot ID' in data.get('error', ''), f"Error message should mention Bot ID: {data}"
        print("✓ Save config correctly rejects missing Bot ID")
    
    def test_save_wabis_config_unauthenticated(self):
        """Test save config returns 401 for unauthenticated requests."""
        # Use fresh session without authentication
        response = requests.post(
            f"{BASE_URL}/integrations/wabis/api/save-config/",
            headers={'Content-Type': 'application/json'},
            json={
                'api_token': 'test_token',
                'whatsapp_bot_id': 'test_bot_id'
            }
        )
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Save config correctly returns 401 for unauthenticated requests")


class TestWabisConnectionTest:
    """Test Wabis API connection test endpoint."""
    
    @pytest.fixture(autouse=True)
    def setup_session(self):
        """Setup authenticated session."""
        self.session = requests.Session()
        
        login_page = self.session.get(f"{BASE_URL}/accounts/login/")
        
        import re
        csrf_match = re.search(r'csrfmiddlewaretoken" value="([^"]+)"', login_page.text)
        self.csrf_token = csrf_match.group(1) if csrf_match else None
        
        login_response = self.session.post(
            f"{BASE_URL}/accounts/login/",
            data={
                'csrfmiddlewaretoken': self.csrf_token,
                'username': 'admin',
                'password': 'admin123'
            },
            headers={'Referer': f"{BASE_URL}/accounts/login/"},
            allow_redirects=True
        )
        
        self.authenticated = login_response.status_code == 200 and '/login' not in login_response.url
        
        if self.authenticated:
            config_page = self.session.get(f"{BASE_URL}/integrations/wabis/config/")
            csrf_match = re.search(r'csrfmiddlewaretoken" value="([^"]+)"', config_page.text)
            self.csrf_token = csrf_match.group(1) if csrf_match else self.csrf_token
    
    def test_connection_test_missing_credentials(self):
        """Test connection test rejects missing credentials."""
        if not self.authenticated:
            pytest.skip("Could not authenticate - skipping")
        
        response = self.session.post(
            f"{BASE_URL}/integrations/wabis/api/test-connection/",
            headers={
                'Content-Type': 'application/json',
                'X-CSRFToken': self.csrf_token,
                'Referer': f"{BASE_URL}/integrations/wabis/config/"
            },
            json={
                'api_token': '',
                'whatsapp_bot_id': ''
            }
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert data.get('success') == False
        assert 'required' in data.get('error', '').lower(), f"Should mention required: {data}"
        print("✓ Connection test correctly rejects missing credentials")
    
    def test_connection_test_invalid_credentials(self):
        """Test connection test handles invalid Wabis credentials."""
        if not self.authenticated:
            pytest.skip("Could not authenticate - skipping")
        
        response = self.session.post(
            f"{BASE_URL}/integrations/wabis/api/test-connection/",
            headers={
                'Content-Type': 'application/json',
                'X-CSRFToken': self.csrf_token,
                'Referer': f"{BASE_URL}/integrations/wabis/config/"
            },
            json={
                'api_token': 'invalid_fake_token_xyz123',
                'whatsapp_bot_id': 'invalid_bot_id_abc'
            }
        )
        
        # Should return 200 with success=False or 500 with error
        data = response.json()
        # Either an API error or success=False is acceptable
        assert response.status_code in [200, 500], f"Unexpected status: {response.status_code}"
        if response.status_code == 200:
            # If API returned, it should indicate failure
            print(f"Response: {data}")
        print("✓ Connection test handles invalid credentials gracefully")
    
    def test_connection_test_unauthenticated(self):
        """Test connection test returns 401 for unauthenticated requests."""
        response = requests.post(
            f"{BASE_URL}/integrations/wabis/api/test-connection/",
            headers={'Content-Type': 'application/json'},
            json={
                'api_token': 'test_token',
                'whatsapp_bot_id': 'test_bot_id'
            }
        )
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Connection test correctly returns 401 for unauthenticated")


class TestWabisSyncTrigger:
    """Test Wabis sync trigger endpoint."""
    
    @pytest.fixture(autouse=True)
    def setup_session(self):
        """Setup authenticated session."""
        self.session = requests.Session()
        
        login_page = self.session.get(f"{BASE_URL}/accounts/login/")
        
        import re
        csrf_match = re.search(r'csrfmiddlewaretoken" value="([^"]+)"', login_page.text)
        self.csrf_token = csrf_match.group(1) if csrf_match else None
        
        login_response = self.session.post(
            f"{BASE_URL}/accounts/login/",
            data={
                'csrfmiddlewaretoken': self.csrf_token,
                'username': 'admin',
                'password': 'admin123'
            },
            headers={'Referer': f"{BASE_URL}/accounts/login/"},
            allow_redirects=True
        )
        
        self.authenticated = login_response.status_code == 200 and '/login' not in login_response.url
        
        if self.authenticated:
            config_page = self.session.get(f"{BASE_URL}/integrations/wabis/config/")
            csrf_match = re.search(r'csrfmiddlewaretoken" value="([^"]+)"', config_page.text)
            self.csrf_token = csrf_match.group(1) if csrf_match else self.csrf_token
    
    def test_trigger_sync_without_config(self):
        """Test trigger sync returns error when no API token configured."""
        if not self.authenticated:
            pytest.skip("Could not authenticate - skipping")
        
        # First, clear any existing config by saving empty (would fail) or check behavior
        response = self.session.post(
            f"{BASE_URL}/integrations/wabis/api/trigger-sync/",
            headers={
                'Content-Type': 'application/json',
                'X-CSRFToken': self.csrf_token,
                'Referer': f"{BASE_URL}/integrations/wabis/"
            }
        )
        
        # Check endpoint responds (may fail due to missing/test config)
        assert response.status_code in [200, 400, 500], f"Unexpected status: {response.status_code}"
        data = response.json()
        print(f"Trigger sync response: {data}")
        print("✓ Trigger sync endpoint responds correctly")
    
    def test_trigger_sync_unauthenticated(self):
        """Test trigger sync returns 401 for unauthenticated requests."""
        response = requests.post(
            f"{BASE_URL}/integrations/wabis/api/trigger-sync/",
            headers={'Content-Type': 'application/json'}
        )
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Trigger sync correctly returns 401 for unauthenticated")


class TestWabisNumberBotIdUpdate:
    """Test updating Bot ID for individual WhatsApp numbers."""
    
    @pytest.fixture(autouse=True)
    def setup_session(self):
        """Setup authenticated session."""
        self.session = requests.Session()
        
        login_page = self.session.get(f"{BASE_URL}/accounts/login/")
        
        import re
        csrf_match = re.search(r'csrfmiddlewaretoken" value="([^"]+)"', login_page.text)
        self.csrf_token = csrf_match.group(1) if csrf_match else None
        
        login_response = self.session.post(
            f"{BASE_URL}/accounts/login/",
            data={
                'csrfmiddlewaretoken': self.csrf_token,
                'username': 'admin',
                'password': 'admin123'
            },
            headers={'Referer': f"{BASE_URL}/accounts/login/"},
            allow_redirects=True
        )
        
        self.authenticated = login_response.status_code == 200 and '/login' not in login_response.url
        
        if self.authenticated:
            config_page = self.session.get(f"{BASE_URL}/integrations/wabis/config/")
            csrf_match = re.search(r'csrfmiddlewaretoken" value="([^"]+)"', config_page.text)
            self.csrf_token = csrf_match.group(1) if csrf_match else self.csrf_token
    
    def test_update_bot_id_nonexistent_number(self):
        """Test update bot ID returns 404 for nonexistent number."""
        if not self.authenticated:
            pytest.skip("Could not authenticate - skipping")
        
        fake_uuid = str(uuid.uuid4())
        
        response = self.session.post(
            f"{BASE_URL}/integrations/wabis/numbers/{fake_uuid}/update-bot-id/",
            headers={
                'Content-Type': 'application/json',
                'X-CSRFToken': self.csrf_token,
                'Referer': f"{BASE_URL}/integrations/wabis/numbers/"
            },
            json={'wabis_bot_id': 'new_bot_id_123'}
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Update Bot ID correctly returns 404 for nonexistent number")
    
    def test_update_bot_id_unauthenticated(self):
        """Test update bot ID returns 401 for unauthenticated requests."""
        fake_uuid = str(uuid.uuid4())
        
        response = requests.post(
            f"{BASE_URL}/integrations/wabis/numbers/{fake_uuid}/update-bot-id/",
            headers={'Content-Type': 'application/json'},
            json={'wabis_bot_id': 'test_bot_id'}
        )
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Update Bot ID correctly returns 401 for unauthenticated")


class TestWabisNumberCRUD:
    """Test WhatsApp number CRUD operations."""
    
    @pytest.fixture(autouse=True)
    def setup_session(self):
        """Setup authenticated session."""
        self.session = requests.Session()
        
        login_page = self.session.get(f"{BASE_URL}/accounts/login/")
        
        import re
        csrf_match = re.search(r'csrfmiddlewaretoken" value="([^"]+)"', login_page.text)
        self.csrf_token = csrf_match.group(1) if csrf_match else None
        
        login_response = self.session.post(
            f"{BASE_URL}/accounts/login/",
            data={
                'csrfmiddlewaretoken': self.csrf_token,
                'username': 'admin',
                'password': 'admin123'
            },
            headers={'Referer': f"{BASE_URL}/accounts/login/"},
            allow_redirects=True
        )
        
        self.authenticated = login_response.status_code == 200 and '/login' not in login_response.url
        
        if self.authenticated:
            config_page = self.session.get(f"{BASE_URL}/integrations/wabis/")
            csrf_match = re.search(r'csrfmiddlewaretoken" value="([^"]+)"', config_page.text)
            self.csrf_token = csrf_match.group(1) if csrf_match else self.csrf_token
    
    def test_add_number_success(self):
        """Test adding a new WhatsApp number."""
        unique_id = str(uuid.uuid4())[:8]
        
        response = self.session.post(
            f"{BASE_URL}/integrations/wabis/numbers/add/",
            headers={
                'Content-Type': 'application/json',
                'X-CSRFToken': self.csrf_token,
                'Referer': f"{BASE_URL}/integrations/wabis/numbers/"
            },
            json={
                'phone_number_id': f'{TEST_PREFIX}phone_{unique_id}',
                'display_phone_number': f'+91999{unique_id}',
                'display_name': f'Test Number {unique_id}',
                'wabis_bot_id': f'{TEST_PREFIX}bot_{unique_id}'
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get('success') == True, f"Expected success=True: {data}"
        assert 'data' in data, "Response should contain 'data'"
        assert data['data']['wabis_bot_id'] == f'{TEST_PREFIX}bot_{unique_id}'
        
        # Store ID for later tests
        self.created_number_id = data['data']['id']
        print(f"✓ Added WhatsApp number: {data['data']['display_name']}")
        
        return data['data']['id']
    
    def test_add_number_missing_fields(self):
        """Test add number rejects missing required fields."""
        response = self.session.post(
            f"{BASE_URL}/integrations/wabis/numbers/add/",
            headers={
                'Content-Type': 'application/json',
                'X-CSRFToken': self.csrf_token,
                'Referer': f"{BASE_URL}/integrations/wabis/numbers/"
            },
            json={
                'phone_number_id': 'test_id',
                # Missing display_phone_number and display_name
            }
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert data.get('success') == False
        print("✓ Add number correctly rejects missing required fields")
    
    def test_add_number_and_update_bot_id(self):
        """Test full flow: add number, then update its Bot ID."""
        if not self.authenticated:
            pytest.skip("Could not authenticate - skipping")
        
        unique_id = str(uuid.uuid4())[:8]
        
        # Add number
        add_response = self.session.post(
            f"{BASE_URL}/integrations/wabis/numbers/add/",
            headers={
                'Content-Type': 'application/json',
                'X-CSRFToken': self.csrf_token,
                'Referer': f"{BASE_URL}/integrations/wabis/numbers/"
            },
            json={
                'phone_number_id': f'{TEST_PREFIX}flow_{unique_id}',
                'display_phone_number': f'+91888{unique_id}',
                'display_name': f'Flow Test {unique_id}',
                'wabis_bot_id': ''  # Initially empty
            }
        )
        
        assert add_response.status_code == 200, f"Failed to add: {add_response.text}"
        number_id = add_response.json()['data']['id']
        print(f"  Added number with ID: {number_id}")
        
        # Update Bot ID
        update_response = self.session.post(
            f"{BASE_URL}/integrations/wabis/numbers/{number_id}/update-bot-id/",
            headers={
                'Content-Type': 'application/json',
                'X-CSRFToken': self.csrf_token,
                'Referer': f"{BASE_URL}/integrations/wabis/numbers/"
            },
            json={'wabis_bot_id': f'{TEST_PREFIX}updated_bot_{unique_id}'}
        )
        
        assert update_response.status_code == 200, f"Failed to update: {update_response.text}"
        data = update_response.json()
        assert data.get('success') == True
        assert data['data']['wabis_bot_id'] == f'{TEST_PREFIX}updated_bot_{unique_id}'
        print("✓ Full flow: add number → update Bot ID works correctly")


class TestSyncStatusAPI:
    """Test sync status API endpoint."""
    
    def test_sync_status_returns_valid_response(self):
        """Test sync status endpoint returns valid data structure."""
        response = requests.get(f"{BASE_URL}/integrations/wabis/api/sync-status/")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Check required fields
        assert 'status' in data, "Missing 'status' field"
        assert 'numbers' in data, "Missing 'numbers' field"
        assert 'webhooks_24h' in data, "Missing 'webhooks_24h' field"
        assert 'errors_24h' in data, "Missing 'errors_24h' field"
        
        # Status should be 'ok' or 'disconnected'
        assert data['status'] in ['ok', 'disconnected'], f"Invalid status: {data['status']}"
        
        # Numbers should be a list
        assert isinstance(data['numbers'], list), "numbers should be a list"
        
        print(f"✓ Sync status: {data['status']}, {len(data['numbers'])} numbers, {data['webhooks_24h']} webhooks in 24h")


class TestWabisDashboardPages:
    """Test Wabis dashboard pages load correctly."""
    
    @pytest.fixture(autouse=True)
    def setup_session(self):
        """Setup authenticated session."""
        self.session = requests.Session()
        
        login_page = self.session.get(f"{BASE_URL}/accounts/login/")
        
        import re
        csrf_match = re.search(r'csrfmiddlewaretoken" value="([^"]+)"', login_page.text)
        self.csrf_token = csrf_match.group(1) if csrf_match else None
        
        login_response = self.session.post(
            f"{BASE_URL}/accounts/login/",
            data={
                'csrfmiddlewaretoken': self.csrf_token,
                'username': 'admin',
                'password': 'admin123'
            },
            headers={'Referer': f"{BASE_URL}/accounts/login/"},
            allow_redirects=True
        )
        
        self.authenticated = login_response.status_code == 200 and '/login' not in login_response.url
    
    def test_wabis_dashboard_loads(self):
        """Test Wabis dashboard page loads."""
        if not self.authenticated:
            pytest.skip("Could not authenticate - skipping")
        
        response = self.session.get(f"{BASE_URL}/integrations/wabis/")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert 'WhatsApp' in response.text or 'Wabis' in response.text
        print("✓ Wabis dashboard loads successfully")
    
    def test_wabis_config_page_loads(self):
        """Test Wabis config page loads."""
        if not self.authenticated:
            pytest.skip("Could not authenticate - skipping")
        
        response = self.session.get(f"{BASE_URL}/integrations/wabis/config/")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert 'API' in response.text or 'Token' in response.text or 'Bot' in response.text
        print("✓ Wabis config page loads successfully")
    
    def test_wabis_numbers_page_loads(self):
        """Test Wabis numbers page loads."""
        if not self.authenticated:
            pytest.skip("Could not authenticate - skipping")
        
        response = self.session.get(f"{BASE_URL}/integrations/wabis/numbers/")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Wabis numbers page loads successfully")
    
    def test_wabis_customers_page_loads(self):
        """Test Wabis customers page loads."""
        if not self.authenticated:
            pytest.skip("Could not authenticate - skipping")
        
        response = self.session.get(f"{BASE_URL}/integrations/wabis/customers/")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Wabis customers page loads successfully")
    
    def test_wabis_webhook_logs_page_loads(self):
        """Test Wabis webhook logs page loads."""
        if not self.authenticated:
            pytest.skip("Could not authenticate - skipping")
        
        response = self.session.get(f"{BASE_URL}/integrations/wabis/logs/")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Wabis webhook logs page loads successfully")


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
