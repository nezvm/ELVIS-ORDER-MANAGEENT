"""
Pytest configuration for Django tests
"""
import os
import django
import pytest

# Set up Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'elvis_erp.settings')
django.setup()


def pytest_configure():
    """Configure Django before running tests"""
    from django.conf import settings
    settings.DEBUG = True


@pytest.fixture(scope='session')
def django_db_setup():
    """Setup database for tests"""
    pass
