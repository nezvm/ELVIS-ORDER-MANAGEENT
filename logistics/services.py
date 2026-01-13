"""Shipping Allocation Service for automatic carrier assignment."""
import logging
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from .models import (
    Carrier, PincodeRule, ChannelShippingRule, ShippingRule, 
    Shipment, ShippingSettings, CarrierAPILog
)
from .courier_apis import CourierAPIRegistry

logger = logging.getLogger(__name__)


class ShipmentAllocationService:
    """Service for allocating carriers to orders."""
    
    def __init__(self):
        self.settings = ShippingSettings.get_settings()
    
    def get_order_data(self, order):
        """Extract relevant data from order for rule evaluation."""
        customer = order.customer
        channel = order.channel
        
        return {
            'order_no': order.order_no,
            'order_date': order.created.strftime('%Y-%m-%d') if order.created else '',
            'channel': channel.channel_type if channel else '',
            'channel_id': str(channel.pk) if channel else '',
            'payment_type': order.payment_type or 'prepaid',
            'is_cod': order.payment_type == 'cod',
            'cod_amount': float(order.total_amount) if order.payment_type == 'cod' else 0,
            'total_amount': float(order.total_amount or 0),
            'weight': float(order.get_total_weight() if hasattr(order, 'get_total_weight') else 0.5),
            'quantity': order.items.count() if hasattr(order, 'items') else 1,
            'product_description': ', '.join([item.product.product_name for item in order.items.all()[:3]]) if hasattr(order, 'items') else 'Products',
            
            # Customer details
            'customer_name': customer.customer_name if customer else '',
            'phone': customer.phone_no if customer else '',
            'email': customer.email if customer else '',
            'address': order.shipping_address or (customer.address if customer else ''),
            'address2': '',
            'city': customer.city if customer else '',
            'state': customer.state if customer else '',
            'pincode': customer.pincode if customer else '',
            'customer_tier': customer.tier if hasattr(customer, 'tier') else '',
            
            # Pickup details (from settings or first warehouse)
            'pickup_name': self.settings.primary_carrier.name if self.settings.primary_carrier else 'Warehouse',
            'pickup_address': 'Default Warehouse Address',
            'pickup_city': 'Default City',
            'pickup_state': 'Default State',
            'pickup_pincode': '110001',
            'pickup_phone': '',
            
            # Dimensions (default values)
            'length': 10,
            'width': 10,
            'height': 10,
            'volumetric_weight': 0,
            
            # Invoice
            'invoice_no': order.order_no,
            'hsn_code': '',
            'seller_gst': '',
        }
    
    def check_serviceability(self, carrier, pincode, is_cod=False):
        """Check if a carrier can service a pincode."""
        try:
            if not self.settings.check_serviceability_before_allocation:
                return True
            
            api = CourierAPIRegistry.get_api(carrier)
            result = api.check_serviceability('110001', pincode, is_cod)
            
            if result.get('serviceable'):
                if is_cod and not result.get('cod_available'):
                    return False
                return True
            return False
        except Exception as e:
            logger.error(f"Serviceability check failed for {carrier.name}: {e}")
            return False  # Fail safe - don't allocate if check fails
    
    def get_carrier_by_pincode_rule(self, pincode, is_cod=False):
        """Get carrier based on pincode rules (highest priority)."""
        if not self.settings.enable_pincode_rules:
            return None
        
        rules = PincodeRule.objects.filter(
            pincode=pincode,
            carrier__status='active',
            is_active=True
        ).select_related('carrier').order_by('-priority')
        
        for rule in rules:
            if is_cod and not rule.supports_cod:
                continue
            if not is_cod and not rule.supports_prepaid:
                continue
            
            # Check serviceability
            if self.check_serviceability(rule.carrier, pincode, is_cod):
                return rule.carrier
        
        return None
    
    def get_carrier_by_channel_rule(self, channel, payment_type):
        """Get carrier based on channel and payment type."""
        if not self.settings.enable_channel_rules or not channel:
            return None
        
        # Look for exact match first
        rule = ChannelShippingRule.objects.filter(
            channel=channel,
            payment_type=payment_type,
            carrier__status='active',
            is_enabled=True,
            is_active=True
        ).select_related('carrier').order_by('-priority').first()
        
        if rule:
            return rule.carrier
        
        # Try with 'all' payment type
        rule = ChannelShippingRule.objects.filter(
            channel=channel,
            payment_type='all',
            carrier__status='active',
            is_enabled=True,
            is_active=True
        ).select_related('carrier').order_by('-priority').first()
        
        return rule.carrier if rule else None
    
    def get_carrier_by_shipping_rule(self, order_data):
        """Get carrier based on shipping rules."""
        rules = ShippingRule.objects.filter(
            assigned_carrier__status='active',
            is_enabled=True,
            is_active=True
        ).select_related('assigned_carrier', 'fallback_carrier').order_by('-priority')
        
        for rule in rules:
            if rule.evaluate(order_data):
                # Check if primary carrier is available
                if self.check_serviceability(rule.assigned_carrier, order_data['pincode'], order_data.get('is_cod')):
                    return rule.assigned_carrier, rule
                # Try fallback
                elif rule.fallback_carrier and self.check_serviceability(rule.fallback_carrier, order_data['pincode'], order_data.get('is_cod')):
                    return rule.fallback_carrier, rule
        
        return None, None
    
    def get_primary_carrier(self, pincode, is_cod=False):
        """Get primary carrier from settings."""
        if self.settings.primary_carrier and self.settings.primary_carrier.status == 'active':
            if self.check_serviceability(self.settings.primary_carrier, pincode, is_cod):
                return self.settings.primary_carrier
        return None
    
    def get_fallback_carrier(self, pincode, is_cod=False):
        """Get any available carrier as fallback."""
        carriers = Carrier.objects.filter(status='active', is_active=True).order_by('-priority')
        
        for carrier in carriers:
            if is_cod and not carrier.supports_cod:
                continue
            if not is_cod and not carrier.supports_prepaid:
                continue
            
            if self.check_serviceability(carrier, pincode, is_cod):
                return carrier
        
        return None
    
    def allocate_carrier(self, order):
        """Allocate the best carrier for an order.
        
        Priority:
        1. Pincode-specific rule (manual mapping)
        2. Channel + Payment type rule
        3. General shipping rules
        4. Primary carrier from settings
        5. Any available carrier (fallback)
        
        Returns:
            tuple: (carrier, assignment_method, rule_used)
        """
        order_data = self.get_order_data(order)
        pincode = order_data['pincode']
        is_cod = order_data['is_cod']
        
        # 1. Check pincode-specific rules (highest priority)
        carrier = self.get_carrier_by_pincode_rule(pincode, is_cod)
        if carrier:
            return carrier, 'pincode_based', None
        
        # 2. Check channel rules
        if order.channel:
            payment_type = 'cod' if is_cod else 'prepaid'
            carrier = self.get_carrier_by_channel_rule(order.channel, payment_type)
            if carrier:
                if self.check_serviceability(carrier, pincode, is_cod):
                    return carrier, 'channel_based', None
        
        # 3. Check general shipping rules
        carrier, rule = self.get_carrier_by_shipping_rule(order_data)
        if carrier:
            return carrier, 'rule_based', rule
        
        # 4. Try primary carrier
        carrier = self.get_primary_carrier(pincode, is_cod)
        if carrier:
            return carrier, 'rule_based', None
        
        # 5. Fallback to any available carrier
        carrier = self.get_fallback_carrier(pincode, is_cod)
        if carrier:
            return carrier, 'rule_based', None
        
        return None, None, None
    
    @transaction.atomic
    def create_shipment(self, order, carrier=None, user=None, force=False):
        """Create a shipment for an order.
        
        Args:
            order: The order to ship
            carrier: Optional carrier to use (for manual override)
            user: User creating the shipment
            force: Force book AWB even if carrier not optimal
            
        Returns:
            tuple: (success, shipment_or_error_message)
        """
        # Check if order already has an active shipment
        existing = Shipment.objects.filter(
            order=order
        ).exclude(status__in=['cancelled', 'rto_delivered']).first()
        
        if existing and not force:
            return False, f"Order already has shipment: {existing.tracking_number}"
        
        # Get order data
        order_data = self.get_order_data(order)
        
        # Allocate carrier if not provided
        if not carrier:
            carrier, assignment_method, rule = self.allocate_carrier(order)
            if not carrier:
                return False, "No suitable carrier found for this order"
        else:
            assignment_method = 'manual'
            rule = None
        
        # Get API and create shipment
        api = CourierAPIRegistry.get_api(carrier)
        result = api.create_shipment(order_data)
        
        if result['success']:
            # Create shipment record
            shipment = Shipment.objects.create(
                order=order,
                carrier=carrier,
                tracking_number=result['tracking_number'],
                awb_number=result['awb_number'],
                status='manifested',
                weight=order_data['weight'],
                length=order_data['length'],
                width=order_data['width'],
                height=order_data['height'],
                shipping_cost=0,  # Can be calculated based on carrier rates
                cod_amount=order_data['cod_amount'],
                is_cod=order_data['is_cod'],
                manifest_date=timezone.now(),
                pickup_address={
                    'name': order_data['pickup_name'],
                    'address': order_data['pickup_address'],
                    'city': order_data['pickup_city'],
                    'state': order_data['pickup_state'],
                    'pincode': order_data['pickup_pincode'],
                    'phone': order_data['pickup_phone']
                },
                delivery_address={
                    'name': order_data['customer_name'],
                    'address': order_data['address'],
                    'city': order_data['city'],
                    'state': order_data['state'],
                    'pincode': order_data['pincode'],
                    'phone': order_data['phone']
                },
                carrier_response=result.get('raw_response', {}),
                label_url=result.get('label_url'),
                assigned_by=user,
                assignment_method=assignment_method,
                rule_used=rule
            )
            
            # Update order with shipment info
            order.awb_number = result['awb_number']
            order.carrier_name = carrier.name
            order.save(update_fields=['awb_number', 'carrier_name'] if hasattr(order, 'awb_number') else [])
            
            return True, shipment
        else:
            return False, result.get('message', 'Failed to create shipment')
    
    def cancel_shipment(self, shipment):
        """Cancel a shipment."""
        api = CourierAPIRegistry.get_api(shipment.carrier)
        result = api.cancel_shipment(shipment.awb_number)
        
        if result['success']:
            shipment.status = 'cancelled'
            shipment.save(update_fields=['status'])
            return True, "Shipment cancelled successfully"
        else:
            return False, result.get('message', 'Failed to cancel shipment')
    
    def update_tracking(self, shipment):
        """Update tracking status for a shipment."""
        from .models import ShipmentTracking
        
        api = CourierAPIRegistry.get_api(shipment.carrier)
        result = api.get_tracking_status(shipment.awb_number)
        
        if result['success']:
            # Update shipment status
            status_mapping = {
                'picked_up': 'picked_up',
                'in_transit': 'in_transit',
                'out_for_delivery': 'out_for_delivery',
                'delivered': 'delivered',
                'rto': 'rto_initiated',
                'returned': 'rto_delivered',
                'cancelled': 'cancelled',
            }
            
            new_status = status_mapping.get(result['status'].lower(), shipment.status)
            if new_status != shipment.status:
                shipment.status = new_status
                shipment.save(update_fields=['status'])
            
            # Add tracking events
            for event in result.get('events', []):
                ShipmentTracking.objects.get_or_create(
                    shipment=shipment,
                    status=event['status'],
                    event_time=event.get('timestamp', timezone.now()),
                    defaults={
                        'location': event.get('location', ''),
                        'status_description': event.get('description', ''),
                        'raw_data': event
                    }
                )
            
            return True, "Tracking updated"
        else:
            return False, result.get('message', 'Failed to fetch tracking')
    
    def bulk_allocate(self, orders, user=None):
        """Allocate carriers to multiple orders.
        
        Returns:
            dict: {'success': count, 'failed': count, 'details': [...]}
        """
        results = {'success': 0, 'failed': 0, 'details': []}
        
        for order in orders:
            success, result = self.create_shipment(order, user=user)
            if success:
                results['success'] += 1
                results['details'].append({
                    'order': order.order_no,
                    'success': True,
                    'awb': result.awb_number,
                    'carrier': result.carrier.name
                })
            else:
                results['failed'] += 1
                results['details'].append({
                    'order': order.order_no,
                    'success': False,
                    'error': result
                })
        
        return results
