"""Ekart Courier API Integration."""
import json
import base64
from . import CourierAPIBase, CourierAPIRegistry


class EkartAPI(CourierAPIBase):
    """Ekart Logistics API integration."""
    
    def get_headers(self):
        if self.credentials:
            auth_string = f"{self.credentials.client_id}:{self.credentials.client_secret}"
            encoded = base64.b64encode(auth_string.encode()).decode()
            return {
                'Authorization': f'Basic {encoded}',
                'Content-Type': 'application/json'
            }
        return {'Content-Type': 'application/json'}
    
    def check_serviceability(self, pickup_pincode, delivery_pincode, is_cod=False):
        """Check pincode serviceability via Ekart API."""
        try:
            url = f"{self.base_url}/v2/serviceability"
            payload = {
                'sourcePinCode': pickup_pincode,
                'destinationPinCode': delivery_pincode
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
                        'delivery_days': data.get('estimatedTat', 5),
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
        """Create shipment and generate AWB via Ekart API."""
        try:
            url = f"{self.base_url}/v2/shipments"
            
            payload = {
                'orderNumber': order_data.get('order_no', ''),
                'paymentType': 'COD' if order_data.get('is_cod') else 'PREPAID',
                'collectableAmount': order_data.get('cod_amount', 0) if order_data.get('is_cod') else 0,
                'orderValue': order_data.get('total_amount', 0),
                'productDescription': order_data.get('product_description', 'Products'),
                'deliveryAddress': {
                    'name': order_data.get('customer_name', ''),
                    'address1': order_data.get('address', ''),
                    'address2': order_data.get('address2', ''),
                    'city': order_data.get('city', ''),
                    'state': order_data.get('state', ''),
                    'pincode': order_data.get('pincode', ''),
                    'phone': order_data.get('phone', ''),
                    'email': order_data.get('email', '')
                },
                'returnAddress': {
                    'name': order_data.get('pickup_name', ''),
                    'address1': order_data.get('pickup_address', ''),
                    'city': order_data.get('pickup_city', ''),
                    'state': order_data.get('pickup_state', ''),
                    'pincode': order_data.get('pickup_pincode', ''),
                    'phone': order_data.get('pickup_phone', '')
                },
                'dimensions': {
                    'weight': order_data.get('weight', 0.5),
                    'length': order_data.get('length', 10),
                    'width': order_data.get('width', 10),
                    'height': order_data.get('height', 10)
                },
                'items': [{
                    'name': order_data.get('product_description', 'Products'),
                    'quantity': order_data.get('quantity', 1),
                    'price': order_data.get('total_amount', 0)
                }]
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
                if data.get('trackingId'):
                    awb = data.get('trackingId')
                    return {
                        'success': True,
                        'awb_number': awb,
                        'tracking_number': awb,
                        'label_url': data.get('shippingLabel'),
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
        """Cancel shipment via Ekart API."""
        try:
            url = f"{self.base_url}/v2/shipments/{awb_number}/cancel"
            
            response = self.make_request(
                method='POST',
                url=url,
                headers=self.get_headers(),
                json_data={'reason': 'Customer requested cancellation'},
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
        """Get tracking status via Ekart API."""
        try:
            url = f"{self.base_url}/v2/shipments/{awb_number}/track"
            
            response = self.make_request(
                method='GET',
                url=url,
                headers=self.get_headers(),
                log_type='track',
                reference_id=awb_number
            )
            
            if response.status_code == 200:
                data = response.json()
                scans = data.get('trackingHistory', [])
                
                events = []
                for scan in scans:
                    events.append({
                        'status': scan.get('status', ''),
                        'location': scan.get('location', ''),
                        'timestamp': scan.get('timestamp', ''),
                        'description': scan.get('description', '')
                    })
                
                return {
                    'success': True,
                    'status': data.get('currentStatus', 'Unknown'),
                    'status_code': data.get('statusCode', ''),
                    'location': data.get('currentLocation', ''),
                    'events': events,
                    'message': 'Tracking retrieved'
                }
            else:
                return {
                    'success': False,
                    'status': None,
                    'status_code': None,
                    'location': None,
                    'events': [],
                    'message': f'API error: {response.status_code}'
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
CourierAPIRegistry.register('ekart', EkartAPI)
