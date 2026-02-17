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

### Phase 5: Meta CAPI Integration (Future)
- Send conversions to Meta for ROAS tracking
- Ad spend sync

---

## What's Been Implemented (February 2026)

### Wabis WhatsApp BSP Integration
- **Webhook**: `/webhooks/wabis/` - GET verification, POST message processing
- **Models**: WabisCustomer, WabisMessage, WabisNumber, WabisWebhookLog
- **Services**: Customer deduplication, ad attribution extraction
- **UI**: Dashboard at `/integrations/wabis/`

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

### Celery Tasks
- `sync_lead_statuses` - Daily at 02:00 IST
- `generate_lead_daily_stats` - Daily at 02:15 IST

---

## Prioritized Backlog

### P0 (Critical)
- [x] Wabis webhook integration
- [x] Shopify webhook integration
- [x] Lead deduplication
- [x] Dashboard with metrics

### P1 (High Priority)
- [ ] Meta Conversions API (CAPI) integration for ROAS
- [ ] Meta Ads API for ad spend sync
- [ ] WhatsApp message templates for recovery campaigns

### P2 (Medium Priority)
- [ ] Advanced analytics and reporting
- [ ] Custom date range filters on dashboard
- [ ] Export leads to CSV
- [ ] Bulk lead operations

### P3 (Low Priority)
- [ ] Mobile responsive optimizations
- [ ] Email notifications for high-value leads
- [ ] Lead scoring algorithm

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
│   ├── wabis/          # Wabis WhatsApp BSP
│   ├── shopify/        # Shopify webhooks
│   └── whatsapp/       # Legacy Meta API (deprecated)
├── marketing/          # Leads, campaigns, analytics
└── templates/          # Django templates
```

### Key Models
- `Lead` (marketing) - Universal lead model
- `WabisCustomer`, `WabisMessage`, `WabisNumber` (integrations.wabis)
- `ShopifyOrder`, `ShopifyAbandonedCheckout` (integrations)

### API Endpoints
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/webhooks/wabis/` | GET/POST | Wabis webhook |
| `/webhooks/shopify/orders/` | POST | Shopify orders |
| `/webhooks/shopify/checkouts/` | POST | Abandoned checkouts |
| `/webhooks/shopify/fulfillments/` | POST | Fulfillment updates |
| `/marketing/dashboard/` | GET | Daily insights |
| `/marketing/leads/` | GET | Leads list |

---

## Test Credentials
- **Admin Login**: admin / admin123
- **Wabis Verify Token**: elvis_wabis_verify_2024

## Test Report
- Latest: `/app/test_reports/iteration_4.json`
- Status: 100% backend tests passed, 100% frontend tests passed
