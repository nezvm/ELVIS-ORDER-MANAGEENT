"""Professional Couriers API Integration."""
import json
from . import CourierAPIBase, CourierAPIRegistry


class ProfessionalCouriersAPI(CourierAPIBase):
    """Professional Couriers (TPC) API integration."""
    
    def get_headers(self):
        return {
            'Content-Type': 'application/json',
            'apikey': self.api_key or ''
        }
    
    def check_serviceability(self, pickup_pincode, delivery_pincode, is_cod=False):
        """Check pincode serviceability via Professional Couriers API."""
        try:
            url = f"{self.base_url}/api/serviceability"
            payload = {
                'originPincode': pickup_pincode,
                'destinationPincode': delivery_pincode,
                'paymentMode': 'COD' if is_cod else 'Prepaid'
            }
            
            response = self.make_request(
                method='POST',
                url=url,
                headers=self.get_headers(),
                json_data=payload,
                log_type='serviceability',
                reference_id=delivery_pincode
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('serviceable'):
                    return {
                        'serviceable': True,
                        'cod_available': data.get('codAvailable', True),
                        'prepaid_available': True,
                        'delivery_days': data.get('estimatedDays', 5),
                        'message': 'Pincode is serviceable'
                    }
            
            return {
                'serviceable': False,
                'cod_available': False,
                'prepaid_available': False,
                'delivery_days': None,
                'message': 'Pincode not serviceable'
            }
                
        except Exception as e:
            return {
                'serviceable': False,
                'cod_available': False,
                'prepaid_available': False,
                'delivery_days': None,
                'message': str(e)
            }
    
    def create_shipment(self, order_data):
        """Create shipment and generate AWB via Professional Couriers API."""
        try:
            url = f"{self.base_url}/api/createShipment"
            
            payload = {
                'referenceNumber': order_data.get('order_no', ''),
                'paymentMode': 'COD' if order_data.get('is_cod') else 'Prepaid',
                'codAmount': order_data.get('cod_amount', 0) if order_data.get('is_cod') else 0,
                'declaredValue': order_data.get('total_amount', 0),
                'weight': order_data.get('weight', 0.5),
                'dimensions': {
                    'length': order_data.get('length', 10),
                    'width': order_data.get('width', 10),
                    'height': order_data.get('height', 10)
                },
                'productDescription': order_data.get('product_description', 'Products'),
                'pieces': order_data.get('quantity', 1),
                'consignee': {
                    'name': order_data.get('customer_name', ''),
                    'address': order_data.get('address', ''),
                    'city': order_data.get('city', ''),
                    'state': order_data.get('state', ''),
                    'pincode': order_data.get('pincode', ''),
                    'phone': order_data.get('phone', ''),
                    'email': order_data.get('email', '')
                },
                'shipper': {
                    'name': order_data.get('pickup_name', ''),
                    'address': order_data.get('pickup_address', ''),
                    'city': order_data.get('pickup_city', ''),
                    'state': order_data.get('pickup_state', ''),
                    'pincode': order_data.get('pickup_pincode', ''),
                    'phone': order_data.get('pickup_phone', '')
                }
            }
            
            response = self.make_request(
                method='POST',
                url=url,
                headers=self.get_headers(),
                json_data=payload,
                log_type='create_shipment',
                reference_id=order_data.get('order_no')
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                if data.get('success') or data.get('docketNumber'):
                    awb = data.get('docketNumber') or data.get('awbNumber')
                    return {
                        'success': True,
                        'awb_number': awb,
                        'tracking_number': awb,
                        'label_url': data.get('labelUrl'),
                        'message': 'Shipment created successfully',
                        'raw_response': data
                    }
                else:
                    return {
                        'success': False,
                        'awb_number': None,
                        'tracking_number': None,
                        'label_url': None,
                        'message': data.get('message', 'Shipment creation failed'),
                        'raw_response': data
                    }
            else:
                return {
                    'success': False,
                    'awb_number': None,
                    'tracking_number': None,
                    'label_url': None,
                    'message': f'API error: {response.status_code}',
                    'raw_response': response.text
                }
                
        except Exception as e:
            return {
                'success': False,
                'awb_number': None,
                'tracking_number': None,
                'label_url': None,
                'message': str(e),
                'raw_response': {}
            }
    
    def cancel_shipment(self, awb_number):
        """Cancel shipment via Professional Couriers API."""
        try:
            url = f"{self.base_url}/api/cancelShipment"
            payload = {
                'docketNumber': awb_number,
                'reason': 'Customer requested cancellation'
            }
            
            response = self.make_request(
                method='POST',
                url=url,
                headers=self.get_headers(),
                json_data=payload,
                log_type='cancel_shipment',
                reference_id=awb_number
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return {'success': True, 'message': 'Shipment cancelled'}
                else:
                    return {'success': False, 'message': data.get('message', 'Cancellation failed')}
            else:
                return {'success': False, 'message': f'API error: {response.status_code}'}
                
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def get_tracking_status(self, awb_number):
        """Get tracking status via Professional Couriers API."""
        try:
            url = f"{self.base_url}/api/tracking"
            
            response = self.make_request(
                method='GET',
                url=f"{url}?docketNumber={awb_number}",
                headers=self.get_headers(),
                log_type='track',
                reference_id=awb_number
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    tracking = data.get('trackingDetails', {})
                    scans = tracking.get('history', [])
                    
                    events = []
                    for scan in scans:
                        events.append({
                            'status': scan.get('status', ''),
                            'location': scan.get('location', ''),
                            'timestamp': scan.get('datetime', ''),
                            'description': scan.get('remarks', '')
                        })
                    
                    return {
                        'success': True,
                        'status': tracking.get('currentStatus', 'Unknown'),
                        'status_code': tracking.get('statusCode', ''),
                        'location': tracking.get('currentLocation', ''),
                        'events': events,
                        'message': 'Tracking retrieved'
                    }
            
            return {
                'success': False,
                'status': None,
                'status_code': None,
                'location': None,
                'events': [],
                'message': 'Tracking failed'
            }
                
        except Exception as e:
            return {
                'success': False,
                'status': None,
                'status_code': None,
                'location': None,
                'events': [],
                'message': str(e)
            }


# Register the API
CourierAPIRegistry.register('professional_couriers', ProfessionalCouriersAPI)
CourierAPIRegistry.register('tpc', ProfessionalCouriersAPI)
