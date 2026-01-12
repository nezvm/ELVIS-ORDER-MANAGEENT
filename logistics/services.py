from master.models import Order
from .models import Carrier, ShippingRule, CarrierRate
import uuid
import random
from decimal import Decimal


class CarrierAllocationService:
    """Service for intelligent carrier allocation."""
    
    def allocate_by_rules(self, order):
        """Allocate carrier based on configured rules."""
        # Build order data for rule evaluation
        order_data = {
            'state': order.customer.state if order.customer else '',
            'city': order.customer.city if order.customer else '',
            'pincode': order.customer.pincode if order.customer else '',
            'total_amount': float(order.total_amount),
            'is_cod': order.cod_charge > 0,
            'channel': order.channel.channel_type if order.channel else '',
            'weight': 0.5,  # Default weight
        }
        
        # Get active rules ordered by priority
        rules = ShippingRule.objects.filter(is_active=True).order_by('-priority')
        
        for rule in rules:
            if rule.evaluate(order_data):
                carrier = rule.assigned_carrier
                if carrier.is_active and carrier.status == 'active':
                    return carrier, rule
                elif rule.fallback_carrier and rule.fallback_carrier.is_active:
                    return rule.fallback_carrier, rule
        
        # No rule matched, return default carrier (highest priority)
        default_carrier = Carrier.objects.filter(is_active=True, status='active').order_by('-priority').first()
        return default_carrier, None
    
    def allocate_by_performance(self, order):
        """Allocate carrier based on performance metrics."""
        # Get carriers that can service this order
        is_cod = order.cod_charge > 0
        
        carriers = Carrier.objects.filter(
            is_active=True,
            status='active'
        )
        
        if is_cod:
            carriers = carriers.filter(supports_cod=True)
        
        if not carriers.exists():
            return None
        
        # Score carriers based on performance
        scored_carriers = []
        for carrier in carriers:
            score = 0
            
            # Success rate (higher is better)
            score += float(carrier.success_rate) * 0.4
            
            # SLA adherence (higher is better)
            score += float(carrier.sla_adherence_rate) * 0.3
            
            # Delivery speed (lower days is better, invert for scoring)
            if carrier.avg_delivery_days > 0:
                score += (10 - min(float(carrier.avg_delivery_days), 10)) * 0.2
            
            # Priority boost
            score += carrier.priority * 0.1
            
            scored_carriers.append((carrier, score))
        
        # Sort by score descending
        scored_carriers.sort(key=lambda x: x[1], reverse=True)
        
        return scored_carriers[0][0] if scored_carriers else None
    
    def get_rate_estimate(self, carrier, order, weight=0.5):
        """Get shipping rate estimate."""
        is_cod = order.cod_charge > 0
        state = order.customer.state if order.customer else ''
        
        # Try to find zone-specific rate
        rate = CarrierRate.objects.filter(
            carrier=carrier,
            is_active=True,
            is_cod=is_cod,
            min_weight__lte=weight,
            max_weight__gte=weight
        ).first()
        
        if rate:
            return rate.calculate_rate(weight, is_cod)
        
        # Return default estimate
        return Decimal('50.00') if not is_cod else Decimal('80.00')


class MockCarrierService:
    """Mock carrier integration service for placeholder functionality."""
    
    def create_shipment(self, order, carrier):
        """Create a mock shipment with carrier."""
        tracking_number = f"{carrier.code.upper()}{uuid.uuid4().hex[:10].upper()}"
        
        return {
            'success': True,
            'tracking_number': tracking_number,
            'awb_number': f"AWB{random.randint(100000000, 999999999)}",
            'weight': 0.5,
            'shipping_cost': float(random.randint(40, 100)),
            'label_url': f"/mock/labels/{tracking_number}.pdf",
            'estimated_delivery': '3-5 business days',
            'carrier_response': {
                'status': 'success',
                'message': 'Shipment created successfully (MOCK)',
                'carrier_id': str(carrier.id)
            }
        }
    
    def cancel_shipment(self, shipment):
        """Cancel a mock shipment."""
        return {
            'success': True,
            'message': 'Shipment cancelled successfully (MOCK)'
        }
    
    def track_shipment(self, shipment):
        """Get mock tracking information."""
        statuses = ['manifested', 'picked_up', 'in_transit', 'out_for_delivery']
        
        return {
            'success': True,
            'current_status': random.choice(statuses),
            'events': [
                {
                    'status': 'Shipment Created',
                    'location': 'Origin Hub',
                    'timestamp': '2025-01-12T10:00:00Z'
                },
                {
                    'status': 'Picked Up',
                    'location': 'Origin Hub',
                    'timestamp': '2025-01-12T14:00:00Z'
                }
            ]
        }
    
    def get_rates(self, carrier, origin_pincode, destination_pincode, weight):
        """Get mock shipping rates."""
        base_rate = 40 + (weight * 10)
        
        return {
            'success': True,
            'rates': [
                {
                    'service': 'Standard',
                    'rate': base_rate,
                    'estimated_days': '4-6'
                },
                {
                    'service': 'Express',
                    'rate': base_rate * 1.5,
                    'estimated_days': '2-3'
                }
            ]
        }
