"""
Logistics Service Layer

This module provides shipping services that read credentials from the database
instead of hardcoded values. It serves as a bridge between the old courier_partner.py
and the new CarrierCredential model.
"""
import json
import time
import requests
from decimal import Decimal
from django.utils import timezone
from django.conf import settings
from .models import Carrier, CarrierCredential, CarrierAPILog, ShippingRule, Shipment, ShippingSettings


class CarrierService:
    """
    Service class for carrier operations.
    Reads credentials from database instead of hardcoded values.
    """
    
    @staticmethod
    def get_credentials(carrier_code, environment='production'):
        """
        Get carrier credentials from database.
        
        Args:
            carrier_code: Carrier code (e.g., 'delhivery', 'bluedart')
            environment: 'sandbox' or 'production'
        
        Returns:
            CarrierCredential object or None
        """
        try:
            return CarrierCredential.objects.get(
                carrier__code=carrier_code,
                environment=environment,
                is_active=True
            )
        except CarrierCredential.DoesNotExist:
            return None
    
    @staticmethod
    def get_carrier_by_code(code):
        """Get carrier by code."""
        try:
            return Carrier.objects.get(code=code, is_active=True)
        except Carrier.DoesNotExist:
            return None
    
    @staticmethod
    def log_api_call(carrier, log_type, request_url, request_method, request_headers,
                     request_body, response_status, response_body, response_time_ms,
                     is_success, error_message=None, reference_id=None):
        """Log an API call to a carrier."""
        # Mask sensitive data in headers
        safe_headers = {k: '***' if 'auth' in k.lower() or 'token' in k.lower() else v 
                       for k, v in request_headers.items()}
        
        return CarrierAPILog.objects.create(
            carrier=carrier,
            log_type=log_type,
            request_url=request_url,
            request_method=request_method,
            request_headers=safe_headers,
            request_body=request_body,
            response_status=response_status,
            response_body=response_body,
            response_time_ms=response_time_ms,
            is_success=is_success,
            error_message=error_message,
            reference_id=reference_id
        )


class DelhiveryService:
    """
    Delhivery shipping service using database credentials.
    """
    CARRIER_CODE = 'delhivery'
    API_URL = 'https://api.delhivery.com/api/cmu/create.json'
    
    @classmethod
    def get_credentials(cls, environment='production'):
        """Get Delhivery credentials from database."""
        creds = CarrierService.get_credentials(cls.CARRIER_CODE, environment)
        if creds:
            return {
                'api_token': creds.api_key,
                'pickup_name': creds.additional_config.get('pickup_name', 'Elvis co'),
                'base_url': creds.base_url or cls.API_URL,
            }
        
        # Fallback to settings/env vars if database credentials not found
        return {
            'api_token': getattr(settings, 'DELHIVERY_API_TOKEN', ''),
            'pickup_name': getattr(settings, 'DELHIVERY_PICKUP_NAME', 'Elvis co'),
            'base_url': cls.API_URL,
        }
    
    @classmethod
    def book_shipment(cls, order, environment='production'):
        """Book a shipment with Delhivery."""
        creds = cls.get_credentials(environment)
        
        if not creds['api_token']:
            return {
                'success': False,
                'message': 'Delhivery API token not configured',
            }
        
        carrier = CarrierService.get_carrier_by_code(cls.CARRIER_CODE)
        payment_mode = "COD" if hasattr(order, 'channel') and 'COD' in str(order.channel.channel_type) else "Prepaid"
        
        cod_amount = ""
        if payment_mode == 'COD':
            cod_charge = 50 if getattr(order, 'cod_charge', 0) == 0 else 0
            amt = order.get_shipping_amount() + cod_charge
            cod_amount = str(amt)
        
        shipment = {
            "name": order.name,
            "add": order.address,
            "pin": order.pincode,
            "city": order.city,
            "state": order.state,
            "country": order.country or "India",
            "phone": order.phone or order.mobile,
            "order": order.order_no,
            "payment_mode": payment_mode,
            "products_desc": order.get_products_desc(),
            "cod_amount": cod_amount,
            "total_amount": str(order.get_shipping_amount()),
            "shipment_width": "10",
            "shipment_height": "10",
            "weight": "0.5",
            "shipping_mode": "Surface",
            "address_type": "home"
        }
        
        data_payload = {
            "shipments": [shipment],
            "pickup_location": {"name": creds['pickup_name']}
        }
        
        headers = {
            "Authorization": f"Token {creds['api_token']}",
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        start_time = time.time()
        try:
            response = requests.post(
                creds['base_url'],
                data={"format": "json", "data": json.dumps(data_payload)},
                headers=headers,
                timeout=30
            )
            response_time_ms = int((time.time() - start_time) * 1000)
            
            try:
                res_data = response.json()
            except Exception:
                res_data = {'raw': response.text}
            
            # Log API call
            if carrier:
                CarrierService.log_api_call(
                    carrier=carrier,
                    log_type='create_shipment',
                    request_url=creds['base_url'],
                    request_method='POST',
                    request_headers=headers,
                    request_body=data_payload,
                    response_status=response.status_code,
                    response_body=res_data,
                    response_time_ms=response_time_ms,
                    is_success=response.status_code == 200,
                    reference_id=order.order_no
                )
            
            if response.status_code != 200:
                return {'success': False, 'message': 'Delhivery API error', 'data': res_data}
            
            packages = res_data.get("packages")
            if not packages:
                return {'success': False, 'message': res_data.get("rmk", "Pincode not serviceable"), 'data': res_data}
            
            package = packages[0]
            waybill = package.get("waybill")
            
            if not waybill:
                return {'success': False, 'message': package.get("remarks") or "Waybill not generated", 'data': res_data}
            
            # Update order
            order.tracking_id = waybill
            order.last_tracking_status = "Booked"
            order.booked_date = timezone.localtime()
            order.tracking_last_checked = timezone.localtime()
            order.stage = "Booked"
            order.save()
            
            return {'success': True, 'message': f"Booked – AWB {waybill}", 'data': package}
            
        except requests.RequestException as e:
            return {'success': False, 'message': str(e)}


class BlueDartService:
    """
    BlueDart shipping service using database credentials.
    """
    CARRIER_CODE = 'bluedart'
    TOKEN_URL = 'https://apigateway.bluedart.com/in/transportation/token/v1/login'
    WAYBILL_URL = 'https://apigateway.bluedart.com/in/transportation/waybill/v1/GenerateWayBill'
    
    @classmethod
    def get_credentials(cls, environment='production'):
        """Get BlueDart credentials from database."""
        creds = CarrierService.get_credentials(cls.CARRIER_CODE, environment)
        if creds:
            return {
                'client_id': creds.client_id,
                'client_secret': creds.client_secret,
                'licence_key': creds.additional_config.get('licence_key', ''),
                'login_id': creds.additional_config.get('login_id', ''),
                'customer_code': creds.additional_config.get('customer_code', ''),
                'shipper_name': creds.additional_config.get('shipper_name', ''),
                'shipper_mobile': creds.additional_config.get('shipper_mobile', ''),
                'shipper_pincode': creds.additional_config.get('shipper_pincode', ''),
                'origin_area': creds.additional_config.get('origin_area', ''),
            }
        
        # Fallback to settings
        return {
            'client_id': getattr(settings, 'BLUEDART_CLIENT_ID', ''),
            'client_secret': getattr(settings, 'BLUEDART_CLIENT_SECRET', ''),
            'licence_key': getattr(settings, 'BLUEDART_LICENCE_KEY', ''),
            'login_id': getattr(settings, 'BLUEDART_LOGIN_ID', ''),
            'customer_code': getattr(settings, 'BLUEDART_CUSTOMER_CODE', ''),
            'shipper_name': getattr(settings, 'BLUEDART_SHIPPER_NAME', ''),
            'shipper_mobile': getattr(settings, 'BLUEDART_SHIPPER_MOBILE', ''),
            'shipper_pincode': getattr(settings, 'BLUEDART_SHIPPER_PINCODE', ''),
            'origin_area': getattr(settings, 'BLUEDART_ORIGIN_AREA', ''),
        }
    
    @classmethod
    def get_token(cls, environment='production'):
        """Get JWT token from BlueDart."""
        creds = cls.get_credentials(environment)
        
        headers = {
            "Accept": "application/json",
            "ClientID": creds['client_id'],
            "clientSecret": creds['client_secret'],
        }
        
        response = requests.get(cls.TOKEN_URL, headers=headers, timeout=20)
        
        if response.status_code != 200:
            raise Exception(f"BlueDart token error: {response.text}")
        
        data = response.json()
        return data.get("JWTToken")


class ShippingRuleEngine:
    """
    Engine for automatic carrier allocation based on rules.
    """
    
    @staticmethod
    def get_order_data(order):
        """Extract order data for rule evaluation."""
        return {
            'state': order.state,
            'city': order.city,
            'pincode': order.pincode,
            'total_amount': float(order.total_amount),
            'weight': 0.5,  # Default weight
            'channel': order.channel.channel_type if hasattr(order.channel, 'channel_type') else str(order.channel),
            'payment_type': 'cod' if 'COD' in str(order.channel.channel_type) else 'prepaid',
        }
    
    @classmethod
    def allocate_carrier(cls, order):
        """
        Allocate a carrier to an order based on shipping rules.
        
        Returns:
            Carrier object or None
        """
        from core.feature_flags import use_legacy_shipping
        
        # If legacy shipping enabled, return None (use old courier_partner.py)
        if use_legacy_shipping():
            return None
        
        order_data = cls.get_order_data(order)
        
        # Get all enabled rules, sorted by priority
        rules = ShippingRule.objects.filter(is_enabled=True, is_active=True).order_by('-priority')
        
        for rule in rules:
            if rule.evaluate(order_data):
                return rule.assigned_carrier
        
        # Fallback to primary carrier
        settings_obj = ShippingSettings.get_settings()
        return settings_obj.primary_carrier
