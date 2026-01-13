"""Courier API Service Registry and Base Classes."""
import requests
import time
import logging
from abc import ABC, abstractmethod
from django.utils import timezone
from .models import CarrierAPILog, Carrier

logger = logging.getLogger(__name__)


class CourierAPIBase(ABC):
    """Base class for all courier API integrations."""
    
    def __init__(self, carrier, credentials):
        self.carrier = carrier
        self.credentials = credentials
        self.base_url = credentials.base_url if credentials else None
        self.api_key = credentials.api_key if credentials else None
        self.api_secret = credentials.api_secret if credentials else None
    
    def log_api_call(self, log_type, url, method, headers, body, response_status, 
                     response_body, response_time_ms, is_success, error_message=None, reference_id=None):
        """Log API call to database."""
        try:
            # Mask sensitive data in headers
            safe_headers = {k: '***' if 'key' in k.lower() or 'token' in k.lower() or 'auth' in k.lower() 
                           else v for k, v in headers.items()}
            
            CarrierAPILog.objects.create(
                carrier=self.carrier,
                log_type=log_type,
                request_url=url,
                request_method=method,
                request_headers=safe_headers,
                request_body=body,
                response_status=response_status,
                response_body=response_body,
                response_time_ms=response_time_ms,
                is_success=is_success,
                error_message=error_message,
                reference_id=reference_id
            )
            
            # Update carrier API stats
            self.carrier.total_api_calls += 1
            if is_success:
                self.carrier.successful_api_calls += 1
            else:
                self.carrier.failed_api_calls += 1
            self.carrier.last_api_check = timezone.now()
            self.carrier.save(update_fields=['total_api_calls', 'successful_api_calls', 
                                             'failed_api_calls', 'last_api_check'])
        except Exception as e:
            logger.error(f"Error logging API call: {e}")
    
    def make_request(self, method, url, headers=None, data=None, json_data=None, 
                     log_type='other', reference_id=None, timeout=30):
        """Make HTTP request with logging."""
        headers = headers or {}
        start_time = time.time()
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                data=data,
                json=json_data,
                timeout=timeout
            )
            response_time_ms = int((time.time() - start_time) * 1000)
            
            try:
                response_body = response.json()
            except:
                response_body = {'text': response.text[:1000]}
            
            is_success = 200 <= response.status_code < 300
            
            self.log_api_call(
                log_type=log_type,
                url=url,
                method=method,
                headers=headers,
                body=json_data or data or {},
                response_status=response.status_code,
                response_body=response_body,
                response_time_ms=response_time_ms,
                is_success=is_success,
                reference_id=reference_id
            )
            
            return response
            
        except requests.exceptions.RequestException as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            self.log_api_call(
                log_type=log_type,
                url=url,
                method=method,
                headers=headers,
                body=json_data or data or {},
                response_status=None,
                response_body={},
                response_time_ms=response_time_ms,
                is_success=False,
                error_message=str(e),
                reference_id=reference_id
            )
            raise
    
    @abstractmethod
    def check_serviceability(self, pickup_pincode, delivery_pincode, is_cod=False):
        """Check if pincode is serviceable.
        
        Returns:
            dict: {
                'serviceable': bool,
                'cod_available': bool,
                'prepaid_available': bool,
                'delivery_days': int or None,
                'message': str
            }
        """
        pass
    
    @abstractmethod
    def create_shipment(self, order_data):
        """Create a shipment and generate AWB.
        
        Args:
            order_data: dict with order details
            
        Returns:
            dict: {
                'success': bool,
                'awb_number': str,
                'tracking_number': str,
                'label_url': str or None,
                'message': str,
                'raw_response': dict
            }
        """
        pass
    
    @abstractmethod
    def cancel_shipment(self, awb_number):
        """Cancel a shipment.
        
        Returns:
            dict: {
                'success': bool,
                'message': str
            }
        """
        pass
    
    @abstractmethod
    def get_tracking_status(self, awb_number):
        """Get tracking status for a shipment.
        
        Returns:
            dict: {
                'success': bool,
                'status': str,
                'status_code': str,
                'location': str,
                'events': list of tracking events,
                'message': str
            }
        """
        pass
    
    def generate_label(self, awb_number):
        """Generate shipping label (optional override)."""
        return {'success': False, 'message': 'Not implemented'}
    
    def test_connection(self):
        """Test API connectivity."""
        try:
            # Most carriers have a serviceability check we can use
            result = self.check_serviceability('110001', '400001')
            return {'success': True, 'message': 'Connection successful'}
        except Exception as e:
            return {'success': False, 'message': str(e)}


class MockCourierAPI(CourierAPIBase):
    """Mock courier API for testing."""
    
    def check_serviceability(self, pickup_pincode, delivery_pincode, is_cod=False):
        return {
            'serviceable': True,
            'cod_available': True,
            'prepaid_available': True,
            'delivery_days': 3,
            'message': 'Mock: Pincode is serviceable'
        }
    
    def create_shipment(self, order_data):
        import uuid
        awb = f"MOCK{uuid.uuid4().hex[:8].upper()}"
        return {
            'success': True,
            'awb_number': awb,
            'tracking_number': awb,
            'label_url': None,
            'message': 'Mock shipment created',
            'raw_response': {'mock': True}
        }
    
    def cancel_shipment(self, awb_number):
        return {
            'success': True,
            'message': 'Mock shipment cancelled'
        }
    
    def get_tracking_status(self, awb_number):
        return {
            'success': True,
            'status': 'in_transit',
            'status_code': 'IT',
            'location': 'Mock Hub',
            'events': [{
                'status': 'In Transit',
                'location': 'Mock Hub',
                'timestamp': timezone.now().isoformat(),
                'description': 'Package is in transit'
            }],
            'message': 'Mock tracking status'
        }


class CourierAPIRegistry:
    """Registry for courier API implementations."""
    
    _apis = {}
    
    @classmethod
    def register(cls, carrier_code, api_class):
        """Register an API implementation for a carrier code."""
        cls._apis[carrier_code.lower()] = api_class
    
    @classmethod
    def get_api(cls, carrier):
        """Get API instance for a carrier."""
        carrier_code = carrier.code.lower()
        api_class = cls._apis.get(carrier_code, MockCourierAPI)
        
        # Get production credentials
        credentials = carrier.credentials.filter(
            is_active=True, 
            environment='production'
        ).first()
        
        if not credentials:
            credentials = carrier.credentials.filter(is_active=True).first()
        
        return api_class(carrier, credentials)
    
    @classmethod
    def list_registered(cls):
        """List all registered carrier codes."""
        return list(cls._apis.keys())


# Register the mock API as default
CourierAPIRegistry.register('mock', MockCourierAPI)
