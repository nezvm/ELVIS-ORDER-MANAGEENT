"""DTDC Courier API Integration."""
import json
import hashlib
from . import CourierAPIBase, CourierAPIRegistry


class DTDCAPI(CourierAPIBase):
    """DTDC API integration."""
    
    def get_headers(self):
        return {
            'Content-Type': 'application/json',
            'api-key': self.api_key
        }
    
    def check_serviceability(self, pickup_pincode, delivery_pincode, is_cod=False):
        """Check pincode serviceability via DTDC API."""
        try:
            url = f"{self.base_url}/dtdc-api/api/pincode/pincodeserviceability"
            payload = {
                'orgPincode': pickup_pincode,
                'desPincode': delivery_pincode
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
                if data.get('status') == 'SUCCESS':
                    service_info = data.get('data', {})
                    return {
                        'serviceable': True,
                        'cod_available': service_info.get('codAvailable', False),
                        'prepaid_available': True,
                        'delivery_days': service_info.get('estimatedDays', 5),
                        'message': 'Pincode is serviceable'
                    }
                else:
                    return {
                        'serviceable': False,
                        'cod_available': False,
                        'prepaid_available': False,
                        'delivery_days': None,
                        'message': data.get('message', 'Pincode not serviceable')
                    }
            else:
                return {
                    'serviceable': False,
                    'cod_available': False,
                    'prepaid_available': False,
                    'delivery_days': None,
                    'message': f'API error: {response.status_code}'
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
        """Create shipment and generate AWB via DTDC API."""
        try:
            url = f"{self.base_url}/dtdc-api/api/softdata"
            
            payload = {
                'customerCode': self.credentials.additional_config.get('customer_code', ''),
                'servicetype': 'DTDC' if not order_data.get('is_cod') else 'COD',
                'loadtype': 'NON-DOCUMENT',
                'producttype': 'GROUND EXPRESS' if order_data.get('weight', 0.5) <= 10 else 'HEAVY',
                'dimension': {
                    'length': order_data.get('length', 10),
                    'width': order_data.get('width', 10),
                    'height': order_data.get('height', 10)
                },
                'weight': order_data.get('weight', 0.5),
                'declaredValue': order_data.get('total_amount', 0),
                'codAmount': order_data.get('cod_amount', 0) if order_data.get('is_cod') else 0,
                'invoiceNumber': order_data.get('invoice_no', order_data.get('order_no', '')),
                'invoiceDate': order_data.get('order_date', ''),
                'consignee': {
                    'name': order_data.get('customer_name', ''),
                    'address1': order_data.get('address', ''),
                    'address2': order_data.get('address2', ''),
                    'city': order_data.get('city', ''),
                    'state': order_data.get('state', ''),
                    'pincode': order_data.get('pincode', ''),
                    'phone': order_data.get('phone', ''),
                    'email': order_data.get('email', '')
                },
                'shipper': {
                    'name': order_data.get('pickup_name', ''),
                    'address1': order_data.get('pickup_address', ''),
                    'city': order_data.get('pickup_city', ''),
                    'state': order_data.get('pickup_state', ''),
                    'pincode': order_data.get('pickup_pincode', ''),
                    'phone': order_data.get('pickup_phone', '')
                },
                'referenceNumber': order_data.get('order_no', ''),
                'pieces': order_data.get('quantity', 1),
                'commodity': order_data.get('product_description', 'Products')
            }
            
            response = self.make_request(
                method='POST',
                url=url,
                headers=self.get_headers(),
                json_data=payload,
                log_type='create_shipment',
                reference_id=order_data.get('order_no')
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'SUCCESS':
                    awb = data.get('data', {}).get('strCnno', '')
                    return {
                        'success': True,
                        'awb_number': awb,
                        'tracking_number': awb,
                        'label_url': data.get('data', {}).get('labelUrl'),
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
        """Cancel shipment via DTDC API."""
        try:
            url = f"{self.base_url}/dtdc-api/api/cancel"
            payload = {
                'customerCode': self.credentials.additional_config.get('customer_code', ''),
                'cnno': awb_number,
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
                if data.get('status') == 'SUCCESS':
                    return {'success': True, 'message': 'Shipment cancelled'}
                else:
                    return {'success': False, 'message': data.get('message', 'Cancellation failed')}
            else:
                return {'success': False, 'message': f'API error: {response.status_code}'}
                
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def get_tracking_status(self, awb_number):
        """Get tracking status via DTDC API."""
        try:
            url = f"{self.base_url}/dtdc-api/api/trackshipment"
            payload = {'cnno': awb_number}
            
            response = self.make_request(
                method='POST',
                url=url,
                headers=self.get_headers(),
                json_data=payload,
                log_type='track',
                reference_id=awb_number
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'SUCCESS':
                    shipment = data.get('data', {})
                    scans = shipment.get('scans', [])
                    
                    events = []
                    for scan in scans:
                        events.append({
                            'status': scan.get('activity', ''),
                            'location': scan.get('origin', ''),
                            'timestamp': scan.get('datetime', ''),
                            'description': scan.get('remarks', '')
                        })
                    
                    return {
                        'success': True,
                        'status': shipment.get('currentStatus', 'Unknown'),
                        'status_code': shipment.get('statusCode', ''),
                        'location': shipment.get('currentLocation', ''),
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
                        'message': data.get('message', 'Tracking failed')
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
CourierAPIRegistry.register('dtdc', DTDCAPI)
