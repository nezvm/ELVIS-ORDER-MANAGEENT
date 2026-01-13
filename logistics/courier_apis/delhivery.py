"""Delhivery Courier API Integration."""
import json
from . import CourierAPIBase, CourierAPIRegistry


class DelhiveryAPI(CourierAPIBase):
    """Delhivery API integration."""
    
    def get_headers(self):
        return {
            'Authorization': f'Token {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    def check_serviceability(self, pickup_pincode, delivery_pincode, is_cod=False):
        """Check pincode serviceability via Delhivery API."""
        try:
            url = f"{self.base_url}/c/api/pin-codes/json/"
            params = {
                'filter_codes': delivery_pincode
            }
            
            response = self.make_request(
                method='GET',
                url=url,
                headers=self.get_headers(),
                log_type='serviceability',
                reference_id=delivery_pincode
            )
            
            if response.status_code == 200:
                data = response.json()
                delivery_codes = data.get('delivery_codes', [])
                
                if delivery_codes:
                    info = delivery_codes[0].get('postal_code', {})
                    return {
                        'serviceable': True,
                        'cod_available': info.get('cod', 'N') == 'Y',
                        'prepaid_available': info.get('pre_paid', 'N') == 'Y',
                        'delivery_days': info.get('max_time', 5),
                        'message': 'Pincode is serviceable'
                    }
                else:
                    return {
                        'serviceable': False,
                        'cod_available': False,
                        'prepaid_available': False,
                        'delivery_days': None,
                        'message': 'Pincode not serviceable'
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
        """Create shipment and generate AWB via Delhivery API."""
        try:
            url = f"{self.base_url}/api/cmu/create.json"
            
            # Format shipment data for Delhivery
            shipment = {
                'name': order_data.get('customer_name', ''),
                'add': order_data.get('address', ''),
                'pin': order_data.get('pincode', ''),
                'city': order_data.get('city', ''),
                'state': order_data.get('state', ''),
                'country': 'India',
                'phone': order_data.get('phone', ''),
                'order': order_data.get('order_no', ''),
                'payment_mode': 'COD' if order_data.get('is_cod') else 'Prepaid',
                'return_pin': order_data.get('pickup_pincode', ''),
                'return_city': order_data.get('pickup_city', ''),
                'return_phone': order_data.get('pickup_phone', ''),
                'return_add': order_data.get('pickup_address', ''),
                'return_state': order_data.get('pickup_state', ''),
                'return_country': 'India',
                'return_name': order_data.get('pickup_name', ''),
                'products_desc': order_data.get('product_description', 'Products'),
                'hsn_code': order_data.get('hsn_code', ''),
                'cod_amount': str(order_data.get('cod_amount', 0)) if order_data.get('is_cod') else '0',
                'order_date': order_data.get('order_date', ''),
                'total_amount': str(order_data.get('total_amount', 0)),
                'seller_add': order_data.get('pickup_address', ''),
                'seller_name': order_data.get('pickup_name', ''),
                'seller_inv': order_data.get('invoice_no', ''),
                'quantity': str(order_data.get('quantity', 1)),
                'waybill': '',  # Leave empty for auto-generation
                'shipment_width': str(order_data.get('width', 10)),
                'shipment_height': str(order_data.get('height', 10)),
                'weight': str(order_data.get('weight', 0.5)),
                'seller_gst_tin': order_data.get('seller_gst', ''),
                'shipping_mode': 'Surface',
                'address_type': 'home',
            }
            
            payload = {
                'format': 'json',
                'data': json.dumps({'shipments': [shipment], 'pickup_location': {'name': order_data.get('pickup_name', 'Default')}})
            }
            
            response = self.make_request(
                method='POST',
                url=url,
                headers={'Authorization': f'Token {self.api_key}', 'Content-Type': 'application/x-www-form-urlencoded'},
                data=payload,
                log_type='create_shipment',
                reference_id=order_data.get('order_no')
            )
            
            if response.status_code == 200:
                data = response.json()
                packages = data.get('packages', [])
                
                if packages and packages[0].get('waybill'):
                    awb = packages[0]['waybill']
                    return {
                        'success': True,
                        'awb_number': awb,
                        'tracking_number': awb,
                        'label_url': f"{self.base_url}/api/p/packing_slip?wbns={awb}",
                        'message': 'Shipment created successfully',
                        'raw_response': data
                    }
                else:
                    remarks = packages[0].get('remarks', ['Unknown error']) if packages else ['No packages returned']
                    return {
                        'success': False,
                        'awb_number': None,
                        'tracking_number': None,
                        'label_url': None,
                        'message': '; '.join(remarks) if isinstance(remarks, list) else str(remarks),
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
        """Cancel shipment via Delhivery API."""
        try:
            url = f"{self.base_url}/api/p/edit"
            payload = {
                'waybill': awb_number,
                'cancellation': 'true'
            }
            
            response = self.make_request(
                method='POST',
                url=url,
                headers=self.get_headers(),
                data=payload,
                log_type='cancel_shipment',
                reference_id=awb_number
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status'):
                    return {'success': True, 'message': 'Shipment cancelled'}
                else:
                    return {'success': False, 'message': data.get('error', 'Cancellation failed')}
            else:
                return {'success': False, 'message': f'API error: {response.status_code}'}
                
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def get_tracking_status(self, awb_number):
        """Get tracking status via Delhivery API."""
        try:
            url = f"{self.base_url}/api/v1/packages/json/"
            params = {'waybill': awb_number}
            
            response = self.make_request(
                method='GET',
                url=f"{url}?waybill={awb_number}",
                headers=self.get_headers(),
                log_type='track',
                reference_id=awb_number
            )
            
            if response.status_code == 200:
                data = response.json()
                shipment_data = data.get('ShipmentData', [{}])[0].get('Shipment', {})
                
                status = shipment_data.get('Status', {}).get('Status', 'Unknown')
                scans = shipment_data.get('Scans', [])
                
                events = []
                for scan in scans:
                    scan_detail = scan.get('ScanDetail', {})
                    events.append({
                        'status': scan_detail.get('Scan', ''),
                        'location': scan_detail.get('ScannedLocation', ''),
                        'timestamp': scan_detail.get('ScanDateTime', ''),
                        'description': scan_detail.get('Instructions', '')
                    })
                
                return {
                    'success': True,
                    'status': status,
                    'status_code': shipment_data.get('Status', {}).get('StatusCode', ''),
                    'location': shipment_data.get('Status', {}).get('StatusLocation', ''),
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
CourierAPIRegistry.register('delhivery', DelhiveryAPI)
