import json
from django.test import TestCase, Client
from django.urls import reverse
from django.conf import settings

from .models import (
    WhatsAppCustomer, 
    WhatsAppNumberConfig, 
    WhatsAppCustomerChannel, 
    WhatsAppMessage,
    WhatsAppWebhookLog
)
from marketing.models import Lead


class WhatsAppWebhookVerificationTest(TestCase):
    """Test webhook verification endpoint."""
    
    def setUp(self):
        self.client = Client()
        self.verify_token = getattr(settings, 'WA_VERIFY_TOKEN', 'elvis_whatsapp_verify_2024')
    
    def test_webhook_verification_success(self):
        """Test successful webhook verification."""
        response = self.client.get('/webhooks/whatsapp/', {
            'hub.mode': 'subscribe',
            'hub.verify_token': self.verify_token,
            'hub.challenge': 'test_challenge_12345'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), 'test_challenge_12345')
    
    def test_webhook_verification_wrong_token(self):
        """Test webhook verification with wrong token."""
        response = self.client.get('/webhooks/whatsapp/', {
            'hub.mode': 'subscribe',
            'hub.verify_token': 'wrong_token',
            'hub.challenge': 'test_challenge_12345'
        })
        self.assertEqual(response.status_code, 403)
    
    def test_webhook_verification_wrong_mode(self):
        """Test webhook verification with wrong mode."""
        response = self.client.get('/webhooks/whatsapp/', {
            'hub.mode': 'wrong_mode',
            'hub.verify_token': self.verify_token,
            'hub.challenge': 'test_challenge_12345'
        })
        self.assertEqual(response.status_code, 403)


class WhatsAppDeduplicationTest(TestCase):
    """Test global customer deduplication."""
    
    def setUp(self):
        self.client = Client()
    
    def _send_message(self, wa_id, phone_number_id, message_id, body="Test message"):
        """Helper to send a webhook message."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "123456789",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "919876543210",
                            "phone_number_id": phone_number_id
                        },
                        "contacts": [{
                            "profile": {"name": f"Customer {wa_id[-4:]}"},
                            "wa_id": wa_id
                        }],
                        "messages": [{
                            "from": wa_id,
                            "id": message_id,
                            "timestamp": "1707580800",
                            "type": "text",
                            "text": {"body": body}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        return self.client.post(
            '/webhooks/whatsapp/',
            data=json.dumps(payload),
            content_type='application/json'
        )
    
    def test_same_customer_multiple_numbers_creates_one_customer(self):
        """Test that same wa_id contacting different numbers creates 1 Customer."""
        wa_id = "919111111111"
        
        # Send message to first number
        response = self._send_message(wa_id, "phone_001", "msg_001")
        self.assertEqual(response.status_code, 200)
        
        # Send message to second number
        response = self._send_message(wa_id, "phone_002", "msg_002")
        self.assertEqual(response.status_code, 200)
        
        # Should have only 1 customer
        customers = WhatsAppCustomer.objects.filter(wa_id=wa_id)
        self.assertEqual(customers.count(), 1)
        
        # Should have 2 customer channels
        channels = WhatsAppCustomerChannel.objects.filter(customer__wa_id=wa_id)
        self.assertEqual(channels.count(), 2)
        
        # Verify channel phone_number_ids
        channel_numbers = set(channels.values_list('phone_number_id', flat=True))
        self.assertEqual(channel_numbers, {'phone_001', 'phone_002'})
    
    def test_different_customers_create_separate_records(self):
        """Test that different wa_ids create separate Customer records."""
        # Send messages from two different customers
        self._send_message("919222222222", "phone_001", "msg_003")
        self._send_message("919333333333", "phone_001", "msg_004")
        
        # Should have 2 customers
        self.assertEqual(WhatsAppCustomer.objects.count(), 2)
    
    def test_message_deduplication(self):
        """Test that same message_id is not processed twice."""
        wa_id = "919444444444"
        message_id = "msg_duplicate"
        
        # Send same message twice
        self._send_message(wa_id, "phone_001", message_id)
        self._send_message(wa_id, "phone_001", message_id)
        
        # Should have only 1 message
        messages = WhatsAppMessage.objects.filter(message_id=message_id)
        self.assertEqual(messages.count(), 1)


class WhatsAppMessageInsertTest(TestCase):
    """Test message storage."""
    
    def setUp(self):
        self.client = Client()
    
    def test_message_stored_correctly(self):
        """Test that message content is stored correctly."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "123456789",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "919876543210",
                            "phone_number_id": "phone_test"
                        },
                        "contacts": [{
                            "profile": {"name": "Message Test User"},
                            "wa_id": "919555555555"
                        }],
                        "messages": [{
                            "from": "919555555555",
                            "id": "msg_content_test",
                            "timestamp": "1707580800",
                            "type": "text",
                            "text": {"body": "This is a test message with special chars: @#$%"}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        
        response = self.client.post(
            '/webhooks/whatsapp/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        # Verify message was stored
        message = WhatsAppMessage.objects.get(message_id="msg_content_test")
        self.assertEqual(message.body, "This is a test message with special chars: @#$%")
        self.assertEqual(message.msg_type, "text")
        self.assertEqual(message.direction, "inbound")
        self.assertEqual(message.phone_number_id, "phone_test")


class WhatsAppLeadCreationTest(TestCase):
    """Test Lead creation from WhatsApp messages."""
    
    def setUp(self):
        self.client = Client()
    
    def test_lead_created_for_new_customer(self):
        """Test that a Lead record is created for new WhatsApp customer."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "123456789",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "919876543210",
                            "phone_number_id": "phone_lead_test"
                        },
                        "contacts": [{
                            "profile": {"name": "Lead Test Customer"},
                            "wa_id": "919666666666"
                        }],
                        "messages": [{
                            "from": "919666666666",
                            "id": "msg_lead_test",
                            "timestamp": "1707580800",
                            "type": "text",
                            "text": {"body": "I want to buy something"}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        
        response = self.client.post(
            '/webhooks/whatsapp/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        # Verify Lead was created
        lead = Lead.objects.filter(phone_no="+919666666666").first()
        self.assertIsNotNone(lead)
        self.assertEqual(lead.name, "Lead Test Customer")
        self.assertEqual(lead.lead_source, "whatsapp_inbound")
        
        # Verify customer is linked to lead
        customer = WhatsAppCustomer.objects.get(wa_id="919666666666")
        self.assertEqual(customer.linked_lead, lead)


class WhatsAppAdAttributionTest(TestCase):
    """Test ad attribution tracking."""
    
    def setUp(self):
        self.client = Client()
    
    def test_ctwa_ad_attribution(self):
        """Test Click-to-WhatsApp ad attribution is captured."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "123456789",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "919876543210",
                            "phone_number_id": "phone_ad_test"
                        },
                        "contacts": [{
                            "profile": {"name": "Ad Attribution Customer"},
                            "wa_id": "919777777777"
                        }],
                        "messages": [{
                            "from": "919777777777",
                            "id": "msg_ad_attribution",
                            "timestamp": "1707580800",
                            "type": "text",
                            "text": {"body": "From your Facebook ad"},
                            "referral": {
                                "source_url": "https://fb.me/test_ad",
                                "source_type": "ad",
                                "source_id": "creative_123",
                                "headline": "Test Ad Headline",
                                "body": "Test Ad Body",
                                "ctwa_clid": "click_tracking_xyz"
                            }
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        
        response = self.client.post(
            '/webhooks/whatsapp/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        # Verify customer has ad attribution
        customer = WhatsAppCustomer.objects.get(wa_id="919777777777")
        self.assertTrue(customer.is_from_ad)
        self.assertEqual(customer.attribution_source, "ctwa_ad")
        self.assertEqual(customer.meta_ad_headline, "Test Ad Headline")
        self.assertEqual(customer.meta_ctwa_clid, "click_tracking_xyz")
        
        # Verify Lead has ad tags
        lead = Lead.objects.filter(phone_no="+919777777777").first()
        self.assertIsNotNone(lead)
        self.assertEqual(lead.lead_source, "whatsapp_ctwa_ad")
        self.assertIn("from_ad", lead.tags)
        self.assertIn("ctwa", lead.tags)
