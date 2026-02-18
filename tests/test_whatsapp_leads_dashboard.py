"""
WhatsApp Leads Dashboard Backend Tests
Tests for /marketing/leads/whatsapp/ endpoint
Tests KPIs, sales number performance table, leads list, and filtering
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'elvis_erp.settings')
django.setup()

import pytest
from django.test import Client
from django.contrib.auth import get_user_model
import re
from decimal import Decimal

# Get base URL
BASE_URL = "https://whatsapp-analytics-4.preview.emergentagent.com"

User = get_user_model()


@pytest.fixture
def authenticated_client():
    """Return authenticated Django test client"""
    client = Client()
    login_success = client.login(username='admin', password='admin123')
    assert login_success, "Login failed - check credentials"
    return client


@pytest.fixture
def db_data():
    """Verify test data exists in database"""
    from marketing.models import Lead
    from integrations.wabis.models import WabisNumber
    from django.db.models import Q
    
    wa_filter = Q(lead_source__icontains='whatsapp') | Q(source_type='whatsapp')
    leads = Lead.objects.filter(wa_filter, is_active=True)
    numbers = WabisNumber.objects.filter(is_active=True)
    
    return {
        'total_leads': leads.count(),
        'won': leads.filter(conversion_status='won').count(),
        'lost': leads.filter(conversion_status='lost').count(),
        'pending': leads.filter(conversion_status='pending').count(),
        'numbers': numbers,
    }


class TestWhatsAppLeadsDashboardAccess:
    """Test dashboard access and page loading"""
    
    @pytest.mark.django_db
    def test_dashboard_requires_login(self):
        """Test that unauthenticated access redirects to login"""
        client = Client()
        response = client.get('/marketing/leads/whatsapp/')
        assert response.status_code == 302  # Redirect to login
        assert '/accounts/login' in response.url
    
    @pytest.mark.django_db
    def test_dashboard_loads_authenticated(self, authenticated_client):
        """Test that authenticated user can access dashboard"""
        response = authenticated_client.get('/marketing/leads/whatsapp/')
        assert response.status_code == 200
        assert b'WhatsApp Leads' in response.content


class TestWhatsAppLeadsKPIs:
    """Test KPI values on dashboard"""
    
    @pytest.mark.django_db
    def test_kpis_with_last_30_days_filter(self, authenticated_client, db_data):
        """Test KPIs show correct values with last_30_days filter"""
        response = authenticated_client.get('/marketing/leads/whatsapp/?date_filter=last_30_days')
        assert response.status_code == 200
        
        content = response.content.decode('utf-8')
        
        # Extract KPI values from HTML
        # Total leads
        total_match = re.search(r'Total.*?<p class="text-2xl font-bold text-gray-900.*?>(\d+)</p>', content, re.DOTALL)
        assert total_match, "Total leads KPI not found"
        total_in_page = int(total_match.group(1))
        assert total_in_page == db_data['total_leads'], f"Expected {db_data['total_leads']}, got {total_in_page}"
        
        # Won leads
        won_match = re.search(r'Won.*?<p class="text-2xl font-bold text-green-600.*?>(\d+)</p>', content, re.DOTALL)
        assert won_match, "Won leads KPI not found"
        won_in_page = int(won_match.group(1))
        assert won_in_page == db_data['won'], f"Expected {db_data['won']}, got {won_in_page}"
        
        # Lost leads
        lost_match = re.search(r'Lost.*?<p class="text-2xl font-bold text-red-600.*?>(\d+)</p>', content, re.DOTALL)
        assert lost_match, "Lost leads KPI not found"
        lost_in_page = int(lost_match.group(1))
        assert lost_in_page == db_data['lost'], f"Expected {db_data['lost']}, got {lost_in_page}"
        
        # Pending leads
        pending_match = re.search(r'Pending.*?<p class="text-2xl font-bold text-yellow-600.*?>(\d+)</p>', content, re.DOTALL)
        assert pending_match, "Pending leads KPI not found"
        pending_in_page = int(pending_match.group(1))
        assert pending_in_page == db_data['pending'], f"Expected {db_data['pending']}, got {pending_in_page}"
    
    @pytest.mark.django_db
    def test_conversion_rate_calculated(self, authenticated_client):
        """Test conversion rate is calculated correctly"""
        response = authenticated_client.get('/marketing/leads/whatsapp/?date_filter=last_30_days')
        content = response.content.decode('utf-8')
        
        # Conversion rate should be shown
        assert 'Conv. Rate' in content or 'CONV%' in content
        # Should have percentage value
        assert re.search(r'\d+\.?\d*%', content), "Conversion rate percentage not found"


class TestPerformanceBySalesNumberTable:
    """Test Performance by Sales Number table"""
    
    @pytest.mark.django_db
    def test_sales_numbers_displayed(self, authenticated_client, db_data):
        """Test that all active sales numbers are shown in table"""
        response = authenticated_client.get('/marketing/leads/whatsapp/?date_filter=last_30_days')
        content = response.content.decode('utf-8')
        
        # Check each number is present
        for number in db_data['numbers']:
            assert number.display_name in content, f"Number {number.display_name} not found in table"
    
    @pytest.mark.django_db
    def test_numbers_table_has_required_columns(self, authenticated_client):
        """Test table has all required columns"""
        response = authenticated_client.get('/marketing/leads/whatsapp/?date_filter=last_30_days')
        content = response.content.decode('utf-8')
        
        required_columns = ['NUMBER', 'LEADS', 'PENDING', 'WON', 'LOST', 'CONV%', 'REVENUE']
        for col in required_columns:
            assert col in content, f"Column {col} not found in numbers table"
    
    @pytest.mark.django_db
    def test_all_numbers_row_shows_totals(self, authenticated_client, db_data):
        """Test 'All Numbers' row shows aggregate totals"""
        response = authenticated_client.get('/marketing/leads/whatsapp/?date_filter=last_30_days')
        content = response.content.decode('utf-8')
        
        # All Numbers row should be present
        assert 'All Numbers' in content
        
        # The total leads count should match
        assert str(db_data['total_leads']) in content


class TestAllWhatsAppLeadsTable:
    """Test individual leads table"""
    
    @pytest.mark.django_db
    def test_leads_table_displayed(self, authenticated_client):
        """Test leads table is shown with correct headers"""
        response = authenticated_client.get('/marketing/leads/whatsapp/?date_filter=last_30_days')
        content = response.content.decode('utf-8')
        
        # Check table headers
        assert 'LEAD' in content
        assert 'PHONE' in content
        assert 'SALES NUMBER' in content
        assert 'STATUS' in content
        assert 'ATTRIBUTION' in content
        assert 'VALUE' in content
        assert 'CREATED' in content
    
    @pytest.mark.django_db
    def test_status_badges_displayed(self, authenticated_client):
        """Test status badges (Won/Lost/Pending) are shown"""
        response = authenticated_client.get('/marketing/leads/whatsapp/?date_filter=last_30_days')
        content = response.content.decode('utf-8')
        
        # Status badges should be present
        assert 'Won' in content
        assert 'Lost' in content
        assert 'Pending' in content


class TestDateFilter:
    """Test date filter functionality"""
    
    @pytest.mark.django_db
    def test_date_filter_options(self, authenticated_client):
        """Test all date filter options are available"""
        response = authenticated_client.get('/marketing/leads/whatsapp/')
        content = response.content.decode('utf-8')
        
        # Check dropdown options
        assert 'today' in content.lower()
        assert 'yesterday' in content.lower()
        assert 'this_week' in content.lower() or 'this week' in content.lower()
        assert 'this_month' in content.lower() or 'this month' in content.lower()
        assert 'last_30_days' in content.lower() or 'last 30 days' in content.lower()
    
    @pytest.mark.django_db
    def test_filter_applied_to_url(self, authenticated_client):
        """Test date filter is passed in URL"""
        filters = ['today', 'yesterday', 'this_week', 'this_month', 'last_7_days', 'last_30_days']
        
        for f in filters:
            response = authenticated_client.get(f'/marketing/leads/whatsapp/?date_filter={f}')
            assert response.status_code == 200, f"Filter {f} returned error"


class TestNumberFiltering:
    """Test filtering by sales number"""
    
    @pytest.mark.django_db
    def test_filter_by_number_id(self, authenticated_client, db_data):
        """Test filtering leads by number_id parameter"""
        if db_data['numbers'].count() == 0:
            pytest.skip("No sales numbers in database")
        
        number = db_data['numbers'].first()
        response = authenticated_client.get(f'/marketing/leads/whatsapp/?date_filter=last_30_days&number_id={number.id}')
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Should show filtered leads heading
        assert 'Filtered Leads' in content
        # Should show Clear link
        assert 'Clear' in content
    
    @pytest.mark.django_db
    def test_filter_unassigned_leads(self, authenticated_client):
        """Test filtering unassigned leads"""
        response = authenticated_client.get('/marketing/leads/whatsapp/?date_filter=last_30_days&number_id=unassigned')
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Should show unassigned leads heading
        assert 'Unassigned Leads' in content or 'Filtered Leads' in content


class TestViewContext:
    """Test view context data"""
    
    @pytest.mark.django_db
    def test_context_has_required_data(self, authenticated_client):
        """Test view provides all required context data"""
        response = authenticated_client.get('/marketing/leads/whatsapp/?date_filter=last_30_days')
        
        # Check response context
        context = response.context
        
        assert 'total_leads' in context
        assert 'pending_leads' in context
        assert 'won_leads' in context
        assert 'lost_leads' in context
        assert 'conversion_rate' in context
        assert 'total_revenue' in context
        assert 'numbers_stats' in context
        assert 'recent_leads' in context
