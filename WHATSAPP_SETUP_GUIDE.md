# WhatsApp Business Platform Setup Guide (2025-2026)

## Complete Step-by-Step Instructions for Meta WhatsApp Cloud API

This guide will help you configure WhatsApp webhook to receive leads in Elvis ERP.

---

## OPTION A: New Setup (No existing WhatsApp Business App)

### Step 1: Create Meta Developer Account

1. Go to **https://developers.facebook.com/**
2. Click **"Get Started"** or **"Log In"** (use your Facebook account)
3. Accept the Terms of Service
4. Verify your account if prompted

### Step 2: Create a New App

1. Go to **https://developers.facebook.com/apps/**
2. Click **"Create App"**
3. Select **"Other"** as the use case → Click **Next**
4. Select **"Business"** as app type → Click **Next**
5. Enter:
   - **App Name**: e.g., "Elvis WhatsApp Leads"
   - **App Contact Email**: Your email
   - **Business Account**: Select existing or create new
6. Click **"Create App"**

### Step 3: Add WhatsApp Product

1. In your app dashboard, scroll down to **"Add products to your app"**
2. Find **"WhatsApp"** card
3. Click **"Set Up"** button on WhatsApp card
4. You'll be redirected to WhatsApp setup

### Step 4: WhatsApp Business Account Setup

1. Select or create a **Meta Business Portfolio** (Business Manager account)
2. Create a new **WhatsApp Business Account (WABA)** or select existing
3. Add a phone number:
   - Enter phone number (must NOT be linked to any WhatsApp account)
   - Choose verification method (SMS or Voice Call)
   - Enter the 6-digit code you receive
4. Set your **Business Display Name**

### Step 5: Configure Webhook

1. In left sidebar, click **WhatsApp** → **Configuration**
2. Scroll to **"Webhook"** section
3. Click **"Edit"** button
4. Enter:
   - **Callback URL**: `https://YOUR-DOMAIN.com/webhooks/whatsapp/`
   - **Verify Token**: `elvis_whatsapp_verify_2024`
5. Click **"Verify and Save"**
6. After verification succeeds, find **"Webhook fields"** section
7. Click **"Manage"**
8. Find **"messages"** field and toggle **Subscribe** to ON

### Step 6: Subscribe App to WABA

Run this command (or use Graph API Explorer):

```bash
curl -X POST 'https://graph.facebook.com/v19.0/YOUR_WABA_ID/subscribed_apps' \
  -H 'Authorization: Bearer YOUR_ACCESS_TOKEN'
```

Or in Graph API Explorer:
1. Go to https://developers.facebook.com/tools/explorer/
2. Select your app
3. Add permission: `whatsapp_business_management`
4. POST to: `YOUR_WABA_ID/subscribed_apps`

---

## OPTION B: Coexistence Mode (Keep using WhatsApp Business App)

If you already use WhatsApp Business App on your phone and want to ALSO receive webhooks:

### Step 1: Update WhatsApp Business App

- Ensure you have **WhatsApp Business App version 2.24.17 or higher**
- Update from App Store (iOS) or Play Store (Android)

### Step 2: Start Embedded Signup

1. Go to **https://business.facebook.com/**
2. Navigate to **Settings** → **WhatsApp accounts**
3. Click **"Add WhatsApp phone number"**
4. Select **"Use existing WhatsApp Business App number"**
5. Choose **"WhatsApp Coexistence"** option

### Step 3: Scan QR Code

1. A **QR code** will appear on screen
2. On your phone, open **WhatsApp Business App**
3. Go to **Settings** → **Linked Devices** → **Link a Device**
4. Scan the QR code shown on computer
5. Confirm the connection

### Step 4: Configure Webhook (Same as Option A, Step 5)

1. Go to **https://developers.facebook.com/apps/** → Select your app
2. Click **WhatsApp** → **Configuration**
3. Configure webhook as described above

---

## WHERE TO FIND THINGS IN META DASHBOARD

### Finding WhatsApp Configuration:

```
developers.facebook.com/apps/
    └── [Your App Name]
        └── Left Sidebar:
            └── WhatsApp (Green icon)
                ├── Quickstart
                ├── API Setup
                ├── Configuration  ← WEBHOOK IS HERE
                └── ...
```

### The Configuration Page Contains:

1. **API Version** - Current Graph API version
2. **Phone numbers** - List of connected numbers
3. **Webhook** - Callback URL and Verify Token settings
4. **Webhook fields** - Subscribe to `messages`, `message_template_status_update`, etc.

### NOT HERE (Common Mistake):

❌ Facebook Login → Webhooks (Shows about, birthday, email - WRONG)
❌ Instagram → Webhooks (Shows comments, mentions - WRONG)
✅ WhatsApp → Configuration → Webhook (Shows messages - CORRECT)

---

## TESTING YOUR WEBHOOK

### Test 1: Verification (GET Request)

```bash
curl "https://YOUR-DOMAIN.com/webhooks/whatsapp/?hub.mode=subscribe&hub.verify_token=elvis_whatsapp_verify_2024&hub.challenge=test123"
```

Expected response: `test123`

### Test 2: Message Reception (POST Request)

```bash
curl -X POST "https://YOUR-DOMAIN.com/webhooks/whatsapp/" \
  -H "Content-Type: application/json" \
  -d '{
    "object": "whatsapp_business_account",
    "entry": [{
      "id": "123456789",
      "changes": [{
        "value": {
          "messaging_product": "whatsapp",
          "metadata": {
            "display_phone_number": "919876543210",
            "phone_number_id": "test_phone"
          },
          "contacts": [{"profile": {"name": "Test"}, "wa_id": "919999888877"}],
          "messages": [{
            "from": "919999888877",
            "id": "msg_test_001",
            "timestamp": "1707590000",
            "type": "text",
            "text": {"body": "Hello!"}
          }]
        },
        "field": "messages"
      }]
    }]
  }'
```

Expected response: `OK`

---

## TROUBLESHOOTING

### "Webhook verification failed"

1. Ensure your server is publicly accessible (HTTPS required)
2. Check `WA_VERIFY_TOKEN` matches exactly
3. Verify your endpoint returns `hub.challenge` value with 200 status

### "messages field not visible"

1. You're in the wrong section - must be under **WhatsApp → Configuration**
2. NOT under Facebook Login or Instagram webhooks

### "No events received"

1. Ensure you clicked **Subscribe** for `messages` field
2. Run the subscription API call to link app to WABA
3. Send a test message to your WhatsApp Business number

### Using ngrok for local testing

```bash
# Start ngrok tunnel
ngrok http 8001

# Use the HTTPS URL as your callback URL
# Example: https://abc123.ngrok.io/webhooks/whatsapp/
```

---

## GETTING ACCESS TOKENS

### Temporary Token (for testing):

1. Go to **WhatsApp → API Setup**
2. Copy the **Temporary access token** (expires in 24 hours)

### Permanent Token (for production):

1. Go to **Business Settings** → **System Users**
2. Create a System User with Admin role
3. Add the WhatsApp WABA asset
4. Generate a permanent access token

---

## SUPPORTED COUNTRIES FOR COEXISTENCE

Coexistence mode is supported in most countries including:
- United States, Canada
- India, Pakistan, Bangladesh
- United Kingdom, Germany, France
- Brazil, Mexico, Argentina
- UAE, Saudi Arabia
- And many more...

**NOT supported** in: Australia (+61), Japan (+81), Nigeria (+234), and some others.

---

## QUICK LINKS

- Meta for Developers: https://developers.facebook.com/
- App Dashboard: https://developers.facebook.com/apps/
- Graph API Explorer: https://developers.facebook.com/tools/explorer/
- WhatsApp Business API Docs: https://developers.facebook.com/docs/whatsapp/
- Business Manager: https://business.facebook.com/

---

## YOUR ELVIS WEBHOOK DETAILS

**Callback URL:** `https://YOUR-DEPLOYED-DOMAIN.com/webhooks/whatsapp/`

**Verify Token:** `elvis_whatsapp_verify_2024`

**Subscribed Events:** `messages`

After setup, leads will automatically appear in:
- Marketing → WhatsApp Leads
- Marketing → All Leads
