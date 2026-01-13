"""Ecom Express Courier API Integration."""
import json
from . import CourierAPIBase, CourierAPIRegistry


class EcomExpressAPI(CourierAPIBase):
    """Ecom Express API integration."""
    
    def get_headers(self):
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.credentials.access_token}' if self.credentials and self.credentials.access_token else ''
        }
    
    def get_auth_headers(self):
        """Get headers for authentication."""
        import base64
        if self.credentials:
            auth_string = f"{self.credentials.client_id}:{self.credentials.client_secret}"
            encoded = base64.b64encode(auth_string.encode()).decode()
            return {
                'Authorization': f'Basic {encoded}',
                'Content-Type': 'application/json'
            }
        return {}
    
    def check_serviceability(self, pickup_pincode, delivery_pincode, is_cod=False):
        """Check pincode serviceability via Ecom Express API."""
        try:
            url = f"{self.base_url}/apiv2/pincodes/"
            payload = {'pincode': delivery_pincode}
            
            response = self.make_request(
                method='GET',
                url=f"{url}?pincode={delivery_pincode}",
                headers=self.get_headers(),
                log_type='serviceability',
                reference_id=delivery_pincode
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    pin_info = data.get('data', {}).get(delivery_pincode, {})
                    return {
                        'serviceable': pin_info.get('serviceable', False),
                        'cod_available': pin_info.get('cod', False),
                        'prepaid_available': pin_info.get('prepaid', False),
                        'delivery_days': pin_info.get('tat', 5),
                        'message': 'Serviceability check complete'
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
        """Create shipment and generate AWB via Ecom Express API."""
        try:
            url = f"{self.base_url}/apiv2/manifest_awb/"
            
            payload = {
                'AWB_NUMBER': '',  # Auto-generate
                'ORDER_NUMBER': order_data.get('order_no', ''),
                'PRODUCT': 'COD' if order_data.get('is_cod') else 'PPD',
                'CONSIGNEE': order_data.get('customer_name', ''),
                'CONSIGNEE_ADDRESS1': order_data.get('address', ''),
                'CONSIGNEE_ADDRESS2': order_data.get('address2', ''),
                'CONSIGNEE_ADDRESS3': '',
                'DESTINATION_CITY': order_data.get('city', ''),
                'PINCODE': order_data.get('pincode', ''),
                'STATE': order_data.get('state', ''),
                'MOBILE': order_data.get('phone', ''),
                'TELEPHONE': '',
                'ITEM_DESCRIPTION': order_data.get('product_description', 'Products'),
                'PIECES': order_data.get('quantity', 1),
                'COLLECTABLE_VALUE': order_data.get('cod_amount', 0) if order_data.get('is_cod') else 0,
                'DECLARED_VALUE': order_data.get('total_amount', 0),
                'ACTUAL_WEIGHT': order_data.get('weight', 0.5),
                'VOLUMETRIC_WEIGHT': order_data.get('volumetric_weight', 0),
                'LENGTH': order_data.get('length', 10),
                'BREADTH': order_data.get('width', 10),
                'HEIGHT': order_data.get('height', 10),
                'PICKUP_NAME': order_data.get('pickup_name', ''),
                'PICKUP_ADDRESS_LINE1': order_data.get('pickup_address', ''),
                'PICKUP_ADDRESS_LINE2': '',
                'PICKUP_PINCODE': order_data.get('pickup_pincode', ''),
                'PICKUP_PHONE': order_data.get('pickup_phone', ''),
                'PICKUP_MOBILE': order_data.get('pickup_phone', ''),
                'RETURN_NAME': order_data.get('pickup_name', ''),
                'RETURN_ADDRESS_LINE1': order_data.get('pickup_address', ''),
                'RETURN_ADDRESS_LINE2': '',
                'RETURN_PINCODE': order_data.get('pickup_pincode', ''),
                'RETURN_PHONE': order_data.get('pickup_phone', ''),
                'RETURN_MOBILE': order_data.get('pickup_phone', ''),
                'DG_SHIPMENT': 'false',
                'ADDITIONAL_INFORMATION': {}
            }
            
            response = self.make_request(
                method='POST',
                url=url,
                headers=self.get_headers(),
                json_data={'shipments': [payload]},
                log_type='create_shipment',
                reference_id=order_data.get('order_no')
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('shipments'):
                    shipment = data['shipments'][0]
                    if shipment.get('success'):
                        awb = shipment.get('awb')
                        return {
                            'success': True,
                            'awb_number': awb,
                            'tracking_number': awb,
                            'label_url': shipment.get('label'),
                            'message': 'Shipment created successfully',
                            'raw_response': data
                        }
                    else:
                        return {
                            'success': False,
                            'awb_number': None,
                            'tracking_number': None,
                            'label_url': None,
                            'message': shipment.get('reason', 'Shipment creation failed'),
                            'raw_response': data
                        }
                        
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
        """Cancel shipment via Ecom Express API."""
        try:
            url = f"{self.base_url}/apiv2/cancel_awb/"
            payload = {
                'awbs': [awb_number],
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
                    return {'success': False, 'message': data.get('reason', 'Cancellation failed')}
            else:
                return {'success': False, 'message': f'API error: {response.status_code}'}
                
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def get_tracking_status(self, awb_number):
        """Get tracking status via Ecom Express API."""
        try:
            url = f"{self.base_url}/apiv2/track_me/"
            
            response = self.make_request(
                method='GET',
                url=f"{url}?awb={awb_number}",
                headers=self.get_headers(),
                log_type='track',
                reference_id=awb_number
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    tracking = data.get('data', {})
                    scans = tracking.get('scans', [])
                    
                    events = []
                    for scan in scans:
                        events.append({
                            'status': scan.get('status', ''),
                            'location': scan.get('location', ''),
                            'timestamp': scan.get('time', ''),
                            'description': scan.get('remarks', '')
                        })
                    
                    return {
                        'success': True,
                        'status': tracking.get('status', 'Unknown'),
                        'status_code': tracking.get('status_code', ''),
                        'location': tracking.get('current_location', ''),
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
CourierAPIRegistry.register('ecom_express', EcomExpressAPI)
