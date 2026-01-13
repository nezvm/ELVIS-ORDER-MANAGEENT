"""India Post Courier API Integration."""
import json
from . import CourierAPIBase, CourierAPIRegistry


class IndiaPostAPI(CourierAPIBase):
    """India Post (ePost/Speed Post) API integration."""
    
    def get_headers(self):
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}' if self.api_key else ''
        }
    
    def check_serviceability(self, pickup_pincode, delivery_pincode, is_cod=False):
        """Check pincode serviceability via India Post API."""
        try:
            # India Post covers all pincodes in India
            url = f"{self.base_url}/api/pincode/{delivery_pincode}"
            
            response = self.make_request(
                method='GET',
                url=url,
                headers=self.get_headers(),
                log_type='serviceability',
                reference_id=delivery_pincode
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'serviceable': True,
                    'cod_available': data.get('codAvailable', True),  # India Post supports COD in most areas
                    'prepaid_available': True,
                    'delivery_days': data.get('deliveryDays', 7),  # Default to 7 days
                    'message': 'Pincode is serviceable'
                }
            
            # Default to serviceable as India Post covers all pincodes
            return {
                'serviceable': True,
                'cod_available': True,
                'prepaid_available': True,
                'delivery_days': 7,
                'message': 'Pincode is serviceable (default)'
            }
                
        except Exception as e:
            # Default to serviceable
            return {
                'serviceable': True,
                'cod_available': True,
                'prepaid_available': True,
                'delivery_days': 7,
                'message': f'Defaulting to serviceable: {str(e)}'
            }
    
    def create_shipment(self, order_data):
        """Create shipment and generate AWB via India Post API."""
        try:
            url = f"{self.base_url}/api/booking"
            
            payload = {
                'bookingType': 'SpeedPost' if order_data.get('weight', 0.5) <= 2 else 'BusinessParcel',
                'paymentMode': 'COD' if order_data.get('is_cod') else 'Prepaid',
                'codAmount': order_data.get('cod_amount', 0) if order_data.get('is_cod') else 0,
                'weight': int(order_data.get('weight', 0.5) * 1000),  # Convert to grams
                'declaredValue': order_data.get('total_amount', 0),
                'contentDescription': order_data.get('product_description', 'Products'),
                'sender': {
                    'name': order_data.get('pickup_name', ''),
                    'addressLine1': order_data.get('pickup_address', ''),
                    'city': order_data.get('pickup_city', ''),
                    'state': order_data.get('pickup_state', ''),
                    'pincode': order_data.get('pickup_pincode', ''),
                    'mobile': order_data.get('pickup_phone', '')
                },
                'receiver': {
                    'name': order_data.get('customer_name', ''),
                    'addressLine1': order_data.get('address', ''),
                    'addressLine2': order_data.get('address2', ''),
                    'city': order_data.get('city', ''),
                    'state': order_data.get('state', ''),
                    'pincode': order_data.get('pincode', ''),
                    'mobile': order_data.get('phone', '')
                },
                'referenceNumber': order_data.get('order_no', '')
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
                if data.get('success') or data.get('articleNumber'):
                    awb = data.get('articleNumber') or data.get('trackingNumber')
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
        """Cancel shipment via India Post API."""
        try:
            url = f"{self.base_url}/api/booking/{awb_number}/cancel"
            
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
        """Get tracking status via India Post API."""
        try:
            url = f"{self.base_url}/api/tracking/{awb_number}"
            
            response = self.make_request(
                method='GET',
                url=url,
                headers=self.get_headers(),
                log_type='track',
                reference_id=awb_number
            )
            
            if response.status_code == 200:
                data = response.json()
                events = data.get('events', [])
                
                formatted_events = []
                for event in events:
                    formatted_events.append({
                        'status': event.get('status', ''),
                        'location': event.get('office', ''),
                        'timestamp': event.get('date', ''),
                        'description': event.get('description', '')
                    })
                
                return {
                    'success': True,
                    'status': data.get('currentStatus', 'Unknown'),
                    'status_code': data.get('statusCode', ''),
                    'location': data.get('currentLocation', ''),
                    'events': formatted_events,
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
CourierAPIRegistry.register('india_post', IndiaPostAPI)
