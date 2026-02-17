# Elvis ERP - Lead Management System PRD

## Original Problem Statement
Build a comprehensive lead management system within the existing Django ERP with:
1. **WhatsApp Integration via Wabis BSP** - Webhooks, customer deduplication, lead attribution
2. **Shopify Integration** - Orders, abandoned checkouts, recovery tracking, COD/Prepaid segmentation
3. **Revamped Leads UI** - Tabs (All Leads, WhatsApp Leads, Shopify Leads, Other Leads)
4. **Daily Insights Dashboard** - Key metrics and analytics

## User Personas
- **E-commerce Business Owner**: Needs to track leads from WhatsApp and Shopify
- **Marketing Manager**: Needs conversion metrics and ROAS tracking
- **Customer Support**: Needs to view customer history across channels

## Core Requirements
### Phase 1: Wabis WhatsApp BSP Integration ✅
- Webhook endpoint for message intake `/webhooks/wabis/`
- Customer deduplication by phone number
- Lead attribution (organic vs ad)
- Admin dashboard for number management
- **UI Configuration Page** at `/integrations/wabis/config/`

### Phase 2: Shopify Integration ✅
- Webhook endpoints for orders, checkouts, fulfillments
- Abandoned checkout tracking and recovery
- COD vs Prepaid order segmentation
- Lead creation from Shopify events

### Phase 3: Universal Lead Logic ✅
- 7-day matching window for lead conversion
- Celery job at 02:00 IST for status updates
- Late conversion detection

### Phase 4: Frontend Revamp ✅
- Tab-based Leads UI (All, WhatsApp, Shopify, Other)
- Sub-tabs for source-specific views
- Daily Insights Dashboard with key metrics

### Phase 5: Cleanup Old Meta Cloud API ✅ (Feb 17, 2026)
- Removed old `/integrations/whatsapp/` UI (now redirects to Wabis)
- Removed old Lead Performance Dashboard (now redirects to Marketing Dashboard)
- Updated sidebar navigation to use Wabis
- Kept webhook endpoint for backward compatibility

### Phase 6: Wabis API Pull Integration ✅ (Feb 17, 2026)
- Created `WabisAPIClient` for Wabis REST API
- UI-based configuration (no environment variables required)
- Test Connection button
- Sync Subscribers button
- Step-by-step setup instructions in UI

### Phase 7: Multi-Number Wabis Support ✅ (Feb 17, 2026)
- `WabisNumber` model now stores `wabis_bot_id` for each number
- UI for managing Bot IDs: `/integrations/wabis/numbers/`
- Edit Bot ID modal for individual numbers
- Sync iterates through all numbers with configured Bot IDs
- API correctly uses Wabis format: `{status: '1', message: [...]}`

### Phase 8: Meta CAPI Integration (Future)
- Send conversions to Meta for ROAS tracking
- Ad spend sync

---

## What's Been Implemented (February 2026)

### Wabis WhatsApp BSP Integration
- **Webhook**: `/webhooks/wabis/` - GET verification, POST message processing
- **API Client**: Full REST API client for Wabis
- **Configuration UI**: `/integrations/wabis/config/` - Enter API Token & Bot ID
- **Models**: WabisCustomer, WabisMessage, WabisNumber, WabisWebhookLog, WabisSyncLog, WabisConfig
- **Services**: Customer deduplication, ad attribution extraction, subscriber sync
- **Dashboard**: `/integrations/wabis/`

### Shopify Integration
- **Webhooks**:
  - `/webhooks/shopify/orders/` - Order creation/updates
  - `/webhooks/shopify/checkouts/` - Abandoned checkout tracking
  - `/webhooks/shopify/fulfillments/` - Fulfillment updates
- **Models**: ShopifyAbandonedCheckout, ShopifyWebhookLog
- **Services**: Lead creation, checkout recovery detection

### Lead Management UI
- **Dashboard**: `/marketing/dashboard/` - Daily insights
- **Leads List**: `/marketing/leads/` - Tab-based filtering
- **Tabs**: All Leads, WhatsApp Leads, Shopify Leads, Other Leads
- **Sub-tabs**: Organic/Ads for WhatsApp, Orders/Checkouts for Shopify

---

## Wabis Setup Instructions

### Step 1: Get API Token
1. Go to [bot.wabis.in/api/developer/console](https://bot.wabis.in/api/developer/console)
2. Login with your Wabis account
3. Copy the API Token (format: `18091|phcZz1un...`)

### Step 2: Get WhatsApp Bot ID
1. Go to [bot.wabis.in](https://bot.wabis.in)
2. Navigate to Bot Manager
3. Select your WhatsApp Bot
4. Find Bot ID in URL: `bot.wabis.in/whatsapp/[BOT_ID]/...`

### Step 3: Configure in ERP
1. Go to `/integrations/wabis/config/`
2. Enter API Token and Bot ID
3. Click "Test Connection"
4. Click "Save Configuration"
5. Click "Sync Subscribers Now" to import leads

### Step 4: Configure Webhook (Optional)
For real-time updates:
1. Go to Wabis → Bot Manager → Out-bound Webhook
2. Create new webhook with URL: `https://your-domain.com/webhooks/wabis/`
3. Select trigger events (new message, new contact, etc.)

---

## Technical Architecture

### Backend (Django)
- **Framework**: Django 4.x with Celery
- **Database**: PostgreSQL
- **Server**: Uvicorn (ASGI)

### Apps Structure
```
/app/
├── elvis_erp/          # Main Django project
├── integrations/       # 3rd-party integrations
│   ├── wabis/          # Wabis WhatsApp BSP (ACTIVE)
│   │   ├── api_client.py  # Wabis API client
│   │   ├── models.py      # WabisConfig, WabisCustomer, etc.
│   │   └── views.py       # Dashboard, Config, Sync
│   ├── shopify/        # Shopify webhooks (ACTIVE)
│   └── whatsapp/       # Legacy Meta API (DEPRECATED - redirects to wabis)
├── marketing/          # Leads, campaigns, analytics
└── templates/          # Django templates
```

### Key API Endpoints
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/integrations/wabis/config/` | GET | Configuration page |
| `/integrations/wabis/numbers/` | GET | Number management page |
| `/integrations/wabis/numbers/<pk>/update-bot-id/` | POST | Update Bot ID for a number |
| `/integrations/wabis/api/save-config/` | POST | Save API credentials |
| `/integrations/wabis/api/test-connection/` | POST | Test API connection |
| `/integrations/wabis/api/trigger-sync/` | POST | Sync subscribers from all numbers |
| `/webhooks/wabis/` | GET/POST | Wabis webhook |
| `/webhooks/shopify/orders/` | POST | Shopify orders |

---

## Test Credentials
- **Admin Login**: admin / admin123
- **Wabis Verify Token**: elvis_wabis_verify_2024
- **Wabis Developer Console**: bot.wabis.in/api/developer/console (wowdeskdown@gmail.com)

## Test Report
- Latest: `/app/test_reports/iteration_5.json`
- Status: 100% backend tests passed (31 tests: 20 Wabis API + 11 webhooks)
