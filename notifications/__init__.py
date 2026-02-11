"""
WhatsApp Notification Service using Libromi (WhatsApp Cloud API).

This service handles sending order notifications via WhatsApp using
the WhatsApp Cloud API through Libromi as the provider.
"""
import logging
import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class WhatsAppNotificationService:
    """Service for sending WhatsApp notifications via Libromi/Cloud API."""
    
    # WhatsApp Cloud API base URL
    BASE_URL = "https://graph.facebook.com/v22.0"
    
    # Template names (must match approved templates in Libromi)
    TEMPLATES = {
        'order_confirmation': 'order_confirmation',
        'order_shipped': 'order_shipped',
        'order_delivered': 'order_delivered',
        'abandoned_cart': 'abandoned_cart',
        'payment_reminder': 'payment_reminder',
    }
    
    @classmethod
    def _get_headers(cls):
        """Get authorization headers for API requests."""
        token = getattr(settings, 'LIBROMI_API_TOKEN', '')
        if not token:
            raise ValueError("LIBROMI_API_TOKEN not configured in settings")
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    @classmethod
    def _get_phone_number_id(cls):
        """Get the WhatsApp Phone Number ID."""
        phone_id = getattr(settings, 'LIBROMI_PHONE_NUMBER_ID', '')
        if not phone_id:
            raise ValueError("LIBROMI_PHONE_NUMBER_ID not configured in settings")
        return phone_id
    
    @classmethod
    def _normalize_phone(cls, phone):
        """
        Normalize phone number to international format without +.
        
        Examples:
            +91 98765 43210 -> 919876543210
            9876543210 -> 919876543210 (assumes India)
            919876543210 -> 919876543210
        """
        import re
        # Remove all non-digit characters
        phone = re.sub(r'\D', '', phone)
        
        # If 10 digits, assume India (+91)
        if len(phone) == 10:
            phone = '91' + phone
        
        return phone
    
    @classmethod
    def send_template_message(cls, phone_number, template_name, parameters, language='en'):
        """
        Send a WhatsApp template message.
        
        Args:
            phone_number: Customer phone (any format, will be normalized)
            template_name: Name of the approved template
            parameters: List of parameter values for the template
            language: Template language code (default: 'en')
        
        Returns:
            dict: API response with message_id on success
        """
        try:
            phone = cls._normalize_phone(phone_number)
            phone_id = cls._get_phone_number_id()
            
            url = f"{cls.BASE_URL}/{phone_id}/messages"
            
            # Build components with parameters
            components = []
            if parameters:
                body_params = [{"type": "text", "text": str(p)} for p in parameters]
                components.append({
                    "type": "body",
                    "parameters": body_params
                })
            
            payload = {
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": language},
                    "components": components
                }
            }
            
            logger.info(f"Sending WhatsApp template '{template_name}' to {phone}")
            
            response = requests.post(url, headers=cls._get_headers(), json=payload, timeout=30)
            result = response.json()
            
            if response.status_code == 200 and result.get('messages'):
                message_id = result['messages'][0].get('id')
                logger.info(f"WhatsApp message sent successfully: {message_id}")
                return {'success': True, 'message_id': message_id, 'response': result}
            else:
                logger.error(f"WhatsApp API error: {result}")
                return {'success': False, 'error': result.get('error', result)}
        
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            return {'success': False, 'error': str(e)}
        except requests.RequestException as e:
            logger.error(f"Request error sending WhatsApp: {e}")
            return {'success': False, 'error': str(e)}
        except Exception as e:
            logger.error(f"Error sending WhatsApp: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    @classmethod
    def send_text_message(cls, phone_number, message):
        """
        Send a text message (only works within 24h customer service window).
        
        Args:
            phone_number: Customer phone
            message: Text message to send
        
        Returns:
            dict: API response
        """
        try:
            phone = cls._normalize_phone(phone_number)
            phone_id = cls._get_phone_number_id()
            
            url = f"{cls.BASE_URL}/{phone_id}/messages"
            
            payload = {
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "text",
                "text": {"body": message}
            }
            
            logger.info(f"Sending WhatsApp text to {phone}")
            
            response = requests.post(url, headers=cls._get_headers(), json=payload, timeout=30)
            result = response.json()
            
            if response.status_code == 200 and result.get('messages'):
                return {'success': True, 'message_id': result['messages'][0].get('id')}
            else:
                return {'success': False, 'error': result.get('error', result)}
        
        except Exception as e:
            logger.error(f"Error sending WhatsApp text: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    # =========================================================================
    # Order Notification Methods
    # =========================================================================
    
    @classmethod
    def send_order_confirmation(cls, order_id, customer_phone, customer_name, items, total):
        """
        Send order confirmation notification.
        
        Template: order_confirmation
        Parameters: {{1}}=name, {{2}}=order_id, {{3}}=items, {{4}}=total
        """
        return cls.send_template_message(
            phone_number=customer_phone,
            template_name=cls.TEMPLATES['order_confirmation'],
            parameters=[customer_name, order_id, items, total]
        )
    
    @classmethod
    def send_order_shipped(cls, order_id, customer_phone, customer_name, tracking_id, courier, tracking_url):
        """
        Send shipping notification.
        
        Template: order_shipped
        Parameters: {{1}}=name, {{2}}=order_id, {{3}}=tracking_id, {{4}}=courier, {{5}}=tracking_url
        """
        return cls.send_template_message(
            phone_number=customer_phone,
            template_name=cls.TEMPLATES['order_shipped'],
            parameters=[customer_name, order_id, tracking_id, courier, tracking_url]
        )
    
    @classmethod
    def send_order_delivered(cls, order_id, customer_phone, customer_name):
        """
        Send delivery confirmation notification.
        
        Template: order_delivered
        Parameters: {{1}}=name, {{2}}=order_id
        """
        return cls.send_template_message(
            phone_number=customer_phone,
            template_name=cls.TEMPLATES['order_delivered'],
            parameters=[customer_name, order_id]
        )
    
    @classmethod
    def send_abandoned_cart_reminder(cls, customer_phone, customer_name, cart_items, shop_url):
        """
        Send abandoned cart reminder.
        
        Template: abandoned_cart
        Parameters: {{1}}=name, {{2}}=items, {{3}}=shop_url
        """
        return cls.send_template_message(
            phone_number=customer_phone,
            template_name=cls.TEMPLATES['abandoned_cart'],
            parameters=[customer_name, cart_items, shop_url]
        )
    
    @classmethod
    def send_payment_reminder(cls, order_id, customer_phone, customer_name, amount, payment_link):
        """
        Send payment reminder for COD or pending orders.
        
        Template: payment_reminder
        Parameters: {{1}}=name, {{2}}=order_id, {{3}}=amount, {{4}}=payment_link
        """
        return cls.send_template_message(
            phone_number=customer_phone,
            template_name=cls.TEMPLATES['payment_reminder'],
            parameters=[customer_name, order_id, amount, payment_link]
        )


class NotificationLog:
    """Helper to log notifications to database."""
    
    @staticmethod
    def log_notification(notification_type, recipient_phone, order_id=None, 
                        status='sent', message_id=None, error=None):
        """Log notification to database for tracking."""
        try:
            from orders.models import Order, OrderActivity
            
            if order_id:
                order = Order.objects.filter(order_id=order_id).first()
                if order:
                    OrderActivity.objects.create(
                        order=order,
                        activity_type='notification_sent',
                        description=f"WhatsApp {notification_type} sent to {recipient_phone}",
                        metadata={
                            'notification_type': notification_type,
                            'recipient': recipient_phone,
                            'status': status,
                            'message_id': message_id,
                            'error': error,
                            'timestamp': timezone.now().isoformat()
                        }
                    )
        except Exception as e:
            logger.error(f"Error logging notification: {e}")
