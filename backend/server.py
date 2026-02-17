"""
Django ASGI server wrapper for uvicorn.
"""
import sys
import os

# Add parent directory to path for Django app access
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'elvis_erp.settings')

from django.core.asgi import get_asgi_application
app = get_asgi_application()
