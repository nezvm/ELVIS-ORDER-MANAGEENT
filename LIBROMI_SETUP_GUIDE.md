# Libromi WhatsApp Integration Setup Guide

## Overview
This guide covers setting up WhatsApp order notifications using Libromi Cloud API provider.

## Step 1: Access Libromi Dashboard

1. Go to: https://panel.libromi.cloud/
2. Login with:
   - Username: nizam@elvisbeauty.com
   - Password: sh3GEh6G#dH8889

## Step 2: Get API Credentials

In the Libromi dashboard, navigate to find:

1. **API Token/Key**: 
   - Go to Settings → API & Webhooks → API Tokens
   - Copy your API token or create a new one

2. **Phone Number ID**: 
   - Go to WhatsApp → Connected Numbers
   - Find your connected WhatsApp Business number
   - Copy the Phone Number ID

3. **WABA ID** (WhatsApp Business Account ID):
   - Also available in the WhatsApp settings section

## Step 3: Configure Elvis ERP

Add the following to your `/app/elvis_erp/settings.py`:

```python
# Libromi WhatsApp API Configuration
LIBROMI_API_URL = 'https://graph.facebook.com/v22.0'  # WhatsApp Cloud API
LIBROMI_API_TOKEN = os.environ.get('LIBROMI_API_TOKEN', '')
LIBROMI_PHONE_NUMBER_ID = os.environ.get('LIBROMI_PHONE_NUMBER_ID', '')
LIBROMI_WABA_ID = os.environ.get('LIBROMI_WABA_ID', '')
```

Add to your `.env` file:
```
LIBROMI_API_TOKEN=your_access_token_here
LIBROMI_PHONE_NUMBER_ID=your_phone_number_id
LIBROMI_WABA_ID=your_waba_id
```

## Step 4: Message Templates

Before sending order notifications, you need approved message templates in Libromi:

### Create Templates in Libromi Dashboard:

1. Go to **WhatsApp → Templates → Create Template**

2. **Order Confirmation Template**:
   - Name: `order_confirmation`
   - Category: `UTILITY`
   - Language: `en`
   - Header: None or Image
   - Body: 
     ```
     Hello {{1}}! 🛍️
     
     Your order #{{2}} has been confirmed!
     
     Items: {{3}}
     Total: ₹{{4}}
     
     We'll notify you when it ships. Thank you for shopping with Elvis!
     ```
   - Footer: `Elvis Beauty`
   - Buttons: Optional - Track Order URL

3. **Shipping Notification Template**:
   - Name: `order_shipped`
   - Category: `UTILITY`
   - Body:
     ```
     Hi {{1}}! 📦
     
     Great news! Your order #{{2}} has been shipped.
     
     Tracking ID: {{3}}
     Courier: {{4}}
     
     Track here: {{5}}
     ```

4. **Delivery Confirmation Template**:
   - Name: `order_delivered`
   - Category: `UTILITY`
   - Body:
     ```
     Hello {{1}}! ✅
     
     Your order #{{2}} has been delivered!
     
     We hope you love your purchase. If you have any questions, reply to this message.
     
     Thank you for choosing Elvis Beauty! ❤️
     ```

5. **Abandoned Cart Template**:
   - Name: `abandoned_cart`
   - Category: `MARKETING`
   - Body:
     ```
     Hi {{1}}! 👋
     
     You left some amazing items in your cart:
     {{2}}
     
     Complete your order now and enjoy free shipping on orders above ₹999!
     
     Shop now: {{3}}
     ```

## Step 5: API Usage

### Send Template Message (Recommended for Notifications)

```python
import requests

def send_whatsapp_template(phone_number, template_name, components):
    """
    Send a WhatsApp template message via Libromi/Cloud API.
    
    Args:
        phone_number: Customer phone (with country code, no +)
        template_name: Approved template name
        components: List of template parameter components
    """
    url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": "en"},
            "components": components
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    return response.json()

# Example: Send order confirmation
components = [
    {
        "type": "body",
        "parameters": [
            {"type": "text", "text": "John"},           # {{1}} - Customer name
            {"type": "text", "text": "ORD-12345"},      # {{2}} - Order number
            {"type": "text", "text": "Lipstick x2"},    # {{3}} - Items
            {"type": "text", "text": "1,499"}           # {{4}} - Total
        ]
    }
]

send_whatsapp_template("919876543210", "order_confirmation", components)
```

### Send Session Message (Within 24-hour window)

```python
def send_whatsapp_text(phone_number, message):
    """Send a text message (only within 24h of customer message)."""
    url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
    
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "text",
        "text": {"body": message}
    }
    
    response = requests.post(url, headers=headers, json=payload)
    return response.json()
```

## Step 6: Webhook Configuration (Already Done)

Your Elvis ERP already receives webhooks at `/webhooks/whatsapp/`. Just ensure Libromi is configured to send webhooks to your domain.

In Libromi Dashboard:
1. Go to **Settings → Webhooks**
2. Add webhook URL: `https://erp.pixelbytz.com/webhooks/whatsapp/`
3. Subscribe to: `messages`

## Common Issues

### Template Not Approved
- Templates need Meta approval (1-24 hours)
- Marketing templates may take longer
- Use UTILITY category for transactional messages

### Phone Number Format
- Always use international format without +
- Example: `919876543210` (91 = India country code)

### Rate Limits
- New accounts: 250 messages/day
- After verification: 1000+/day
- Business verified: Unlimited (fair use)

## Testing

Use the admin panel or Django shell to test:

```python
from notifications.whatsapp import WhatsAppNotificationService

# Test send
result = WhatsAppNotificationService.send_order_confirmation(
    order_id='ORD-TEST-001',
    customer_phone='919876543210',
    customer_name='Test User',
    items='Test Product x1',
    total='999'
)
print(result)
```
