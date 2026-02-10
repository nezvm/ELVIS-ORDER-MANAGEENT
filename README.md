# Elvis ERP - Order Management System

## WhatsApp Lead Auto-Save Integration

This system automatically captures leads from WhatsApp Business Platform using official webhook-based integration. It supports multiple WhatsApp Business numbers and provides global deduplication of contacts.

### Features

- **Webhook-based Ingestion**: Official Meta WhatsApp Business Platform integration (no scraping)
- **Multi-Number Support**: Connect unlimited WhatsApp Business numbers without code changes
- **Global Deduplication**: Same customer contacting multiple sales numbers = 1 Customer record
- **Ad Attribution Tracking**: Automatically captures Click-to-WhatsApp (CTWA) ad data
- **Lead Source Tagging**: Distinguishes between Organic vs Ad-sourced leads
- **Unified Lead Management**: WhatsApp leads appear in main Marketing > Leads section

### Setup Instructions

#### 1. Environment Variables

Add these to your `.env` file:

```bash
# Required: Webhook verification token (must match Meta App config)
WA_VERIFY_TOKEN=elvis_whatsapp_verify_2024

# Optional: For signature verification (recommended for production)
WA_APP_SECRET=your_app_secret_here

# Optional: For outbound messages
META_ACCESS_TOKEN=your_access_token_here
```

#### 2. Meta for Developers Setup

1. Go to [Meta for Developers](https://developers.facebook.com/apps) 
2. Create a new app or select existing app
3. Add **WhatsApp** product
4. Configure Webhook:
   - **Callback URL**: `https://your-domain.com/webhooks/whatsapp/`
   - **Verify Token**: Same as `WA_VERIFY_TOKEN` in your .env
   - **Subscribed Fields**: `messages`

#### 3. Connect WhatsApp Business Numbers (Coexistence Mode)

For each WhatsApp Business phone you want to connect:

1. Open **WhatsApp Business** app on the phone
2. Go to **Settings** → **Linked Devices**
3. Tap **Link a device**
4. Select **Connect to Business Platform** (Beta)
5. Scan the QR code shown in Meta Business Suite

> **Note**: Coexistence mode allows you to continue using WhatsApp Business mobile app normally while leads are auto-captured.

### How It Works

#### Data Flow

```
Customer sends message → Meta Webhook → ELVIS → Upsert Customer → Create Lead
                                             ↓
                                       Create Message
                                             ↓
                                  Track Channel (touchpoint)
```

#### Deduplication Logic

1. **Customer Level**: Unique by `wa_id` (customer's WhatsApp number)
   - If same customer messages multiple sales numbers → 1 Customer record
   
2. **Channel Level**: Unique by `(customer, phone_number_id)`
   - Tracks which sales numbers the customer has contacted
   
3. **Message Level**: Unique by `message_id` (Meta's message ID)
   - Prevents duplicate processing on webhook retries

#### Ad Attribution

When a customer messages from a Click-to-WhatsApp ad, the system captures:
- Ad headline and body text
- Source URL and type
- Click tracking ID (ctwa_clid)
- Campaign/creative IDs

This data is stored on both the WhatsApp Customer and the linked Lead record.

### Admin Interface

Access the Django admin at `/admin/` to manage:

- **WhatsApp Customers**: View/edit customer records
- **WhatsApp Messages**: View message history
- **WhatsApp Number Configs**: View connected numbers
- **Webhook Logs**: Debug webhook activity

### UI Pages

- **Marketing > All Leads**: Unified lead list (includes WhatsApp leads)
- **Marketing > WhatsApp Leads**: WhatsApp-specific lead list
- **Settings > Integrations > WhatsApp Setup**: Connection setup page

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/webhooks/whatsapp/` | GET | Meta webhook verification |
| `/webhooks/whatsapp/` | POST | Receive messages from Meta |
| `/integrations/whatsapp/` | GET | WhatsApp dashboard (auth required) |
| `/integrations/whatsapp/customers/` | GET | Customer list (auth required) |
| `/integrations/whatsapp/customer/<uuid>/` | GET | Customer detail (auth required) |

### Models

```
WhatsAppCustomer (wa_id unique)
├── profile_name, first_seen, last_seen
├── is_from_ad, attribution_source
├── meta_ad_* fields (ad tracking)
├── assigned_sales_user (FK)
├── linked_lead (FK to Lead)
└── linked_customer (FK to Customer)

WhatsAppCustomerChannel (customer + phone_number_id unique)
├── customer (FK)
├── phone_number_id
├── first_contact_at, last_contact_at
└── message_count

WhatsAppMessage (message_id unique)
├── customer (FK)
├── phone_number_id
├── direction, msg_type, body
├── timestamp_utc
└── raw_payload

WhatsAppNumberConfig (phone_number_id unique)
├── display_phone_number, name
├── last_webhook_at, webhook_count
└── total_messages_received, total_customers
```

### Testing

Run the WhatsApp integration tests:

```bash
python manage.py test integrations.whatsapp.tests -v 2
```

### Deployment Notes

- Webhook must be accessible via HTTPS
- For development, use ngrok or similar tunnel
- Ensure `WA_VERIFY_TOKEN` matches between `.env` and Meta App config
- Always return HTTP 200 to webhook POSTs to prevent retry storms

### Troubleshooting

**Webhook verification fails:**
- Check `WA_VERIFY_TOKEN` matches in both places
- Ensure URL is accessible from internet

**Messages not appearing:**
- Check `/admin/whatsapp/whatsappwebhooklog/` for errors
- Verify webhook subscription includes `messages` field

**Duplicate customers:**
- Check `wa_id` format consistency (should be without +)
- Review webhook logs for processing errors
