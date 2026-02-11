"""
WhatsApp Notification Service for Elvis ERP.

Usage:
    from notifications.whatsapp import WhatsAppNotificationService
    
    # Send order confirmation
    result = WhatsAppNotificationService.send_order_confirmation(
        order_id='ORD-12345',
        customer_phone='+91 98765 43210',
        customer_name='John Doe',
        items='Lipstick x2, Foundation x1',
        total='1,499'
    )
    
    # Send shipping notification
    result = WhatsAppNotificationService.send_order_shipped(
        order_id='ORD-12345',
        customer_phone='+91 98765 43210',
        customer_name='John Doe',
        tracking_id='SHIP123456',
        courier='Delhivery',
        tracking_url='https://track.delhivery.com/SHIP123456'
    )
"""

from notifications import WhatsAppNotificationService, NotificationLog

__all__ = ['WhatsAppNotificationService', 'NotificationLog']
