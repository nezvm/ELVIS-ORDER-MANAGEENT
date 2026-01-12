# Elvis-Manager ERP - Product Requirements Document

## Original Problem Statement
Extend a Django-based ERP system (Elvis-Manager) with new functionality without altering core models. Primary focus is on implementing a modern Marketing module with:
1. **Lead Management** - Google Contacts sync, WIN/LOSS segmentation
2. **WhatsApp Broadcasting** - Plug-and-play Meta Cloud API provider, templates, campaigns
3. **Market Insights** - Geo-analytics dashboards (State → District → Pincode), Hot/Cold market tagging
4. **Complete UI Overhaul** - Modern design with sidebar + top bar layout

## User Preferences
- **Color Scheme**: Black, White, #AE1F25 (red)
- **Reference Apps**: Shopify (with bigger texts), Petpooja
- **Tech Stack**: Django + PostgreSQL + Redis + Celery

---

## What's Completed (Dec 12, 2025)

### 1. UI/UX Overhaul ✅
- [x] Modern sidebar navigation (black theme)
- [x] Top bar with search, notifications, quick add
- [x] Card-based layouts with #AE1F25 accent color
- [x] Consistent design system across all modules

### 2. Marketing Module - Leads Management ✅
- [x] Lead model with phone, name, address, segmentation fields
- [x] **NEW: lead_source field** (manual, whatsapp_vcf_import, google_contacts_sync, shopify_abandoned_checkout, shopify_abandoned_cart, website_form, referral)
- [x] **NEW: Shopify Abandoned Checkout fields** (source_ref_id, source_payload, captured_at, needs_phone, recover_url, cart_value, cart_items_summary, abandoned_at)
- [x] **NEW: location_status field** (unknown, enriched, verified)
- [x] WIN/LOSS/CONVERTED classification
- [x] Lead list with filters
- [x] Lead creation/edit forms with lead_source dropdown
- [x] Stats dashboard (Total, WIN, LOSS, Conversion Rate)
- [x] Google Contacts sync (MOCKED)

### 3. Marketing Module - WhatsApp Broadcasting ✅
- [x] WhatsApp Provider model (Meta Cloud API)
- [x] Provider CRUD with API credentials
- [x] Message Template management
- [x] Notification Events configuration
- [x] Message Logs tracking
- [x] **NEW: Campaign Types** (broadcast, abandoned_recovery, promotional, transactional, reactivation)
- [x] **NEW: Abandoned Recovery campaign** with followup schedule
- [x] Campaign analytics

### 4. Market Insights - MAJOR UPDATE ✅
#### TAB 1: Order Markets (Accurate)
- [x] Source: Orders only (shipping address PINCODE)
- [x] Aggregations: state, orders, revenue, COD%, RTO%, repeat rate
- [x] Always works regardless of lead location quality

#### TAB 2: Lead Markets (Enriched Only)
- [x] Source: Leads with location_status != 'unknown'
- [x] Aggregations: leads count, WIN count, LOSS count, conversion rate

#### Unknown Location Bucket
- [x] Shows "Unknown Location Leads" count
- [x] Shows "% leads missing pincode"
- [x] Action hint: "Collect pincode via WhatsApp to unlock region insights"

#### Market Categories
- [x] Hot Markets (high revenue/orders)
- [x] Cold Zones (high leads, low conversion)
- [x] Loss Markets (high abandoned LOSS leads)
- [x] New Markets (first order within 30 days)

### 5. Shopify Abandoned Checkout Pipeline ✅
- [x] ShopifyStore model with sync_abandoned_checkouts toggle
- [x] sync_shopify_abandoned_checkout service function
- [x] Phone/email normalization (E.164 format)
- [x] Merge rules to avoid duplicates
- [x] WIN/LOSS tagging based on customer/order match
- [x] Conversion tracking (abandoned → order)
- [x] Location enrichment from pincode

### 6. Abandoned Metrics & Insights ✅
- [x] AbandonedMetrics model
- [x] /marketing/insights/abandoned/ page
- [x] Abandoned count, value, converted count, recovery rate
- [x] Top Abandoned Products
- [x] Loss Markets by state (enriched only)
- [x] Recent Abandoned Checkouts table

---

## Technical Architecture

```
/app/
├── marketing/
│   ├── models.py          # Lead (extended), Campaign (types), PincodeMaster, OrderMarketStats, LeadMarketStats, AbandonedMetrics
│   ├── services.py        # LeadService, WhatsAppService, CampaignService, MarketInsightsService
│   ├── views.py           # MarketInsightsView, AbandonedInsightsView
│   └── forms.py           # LeadForm (with lead_source), CampaignForm (with campaign_type)
├── integrations/
│   └── models.py          # ShopifyStore (with sync_abandoned_checkouts toggle)
└── templates/
    └── marketing/
        ├── insights/
        │   ├── dashboard.html   # 2 tabs + unknown bucket
        │   └── abandoned.html   # Abandoned insights
        └── campaigns/
            └── form.html        # Campaign type + recovery settings
```

---

## Database Schema Updates

### Lead Model (Extended)
```python
lead_source = CharField(choices=LEAD_SOURCES)  # manual, shopify_abandoned_checkout, etc.
source_ref_id = CharField()  # Shopify checkout ID
source_payload = JSONField()  # Raw Shopify payload
captured_at = DateTimeField()
needs_phone = BooleanField()
recover_url = URLField()
cart_value = DecimalField()
cart_items_summary = JSONField()
abandoned_at = DateTimeField()
location_status = CharField()  # unknown, enriched, verified
converted_order = ForeignKey(Order)
conversion_days = IntegerField()
```

### New Models
- **PincodeMaster**: pincode → state, district mapping
- **OrderMarketStats**: Order-based geo stats from shipping address
- **LeadMarketStats**: Lead-based geo stats (enriched only)
- **AbandonedMetrics**: Aggregated abandoned checkout metrics

### ShopifyStore (Extended)
```python
sync_abandoned_checkouts = BooleanField()
sync_abandoned_carts = BooleanField()
abandoned_sync_interval_minutes = IntegerField()
last_abandoned_sync_at = DateTimeField()
checkouts_webhook_id = CharField()
```

---

## API Endpoints

### Marketing APIs
- `POST /marketing/api/leads/sync/` - Sync Google contacts
- `POST /marketing/api/lead/<pk>/match/` - Re-match lead
- `POST /marketing/api/lead/<pk>/convert/` - Convert to customer
- `POST /marketing/api/insights/refresh/` - Refresh all geo stats

### Shopify Sync (to be implemented)
- Abandoned checkout sync runs on cron/celery beat
- Webhook endpoint for real-time checkout updates

---

## MOCKED Integrations
⚠️ The following integrations have placeholder implementations:
1. **Google Contacts Sync** - Creates mock contacts
2. **Meta Cloud API (WhatsApp)** - Mock message sending
3. **Shopify Abandoned Checkout API** - Mock checkout fetch

---

## Acceptance Checklist ✅

| Requirement | Status |
|-------------|--------|
| Order Market tab works with 100% unknown leads | ✅ DONE |
| Lead Market tab uses ONLY enriched leads | ✅ DONE |
| Unknown bucket shows count + % missing pincode | ✅ DONE |
| lead_source + Shopify abandoned fields exist | ✅ DONE |
| Abandoned Recovery campaign type exists | ✅ DONE |
| Conversion tracking updates lead status | ✅ DONE |
| Market Insights shows abandoned metrics | ✅ DONE |
| Top abandoned products visible | ✅ DONE |
| Loss markets show enriched only | ✅ DONE |

---

## Pending / Backlog

### Real Integrations (P0)
- [ ] Actual Google OAuth for contacts sync
- [ ] Actual Meta Cloud API for WhatsApp
- [ ] Actual Shopify API for abandoned checkouts
- [ ] Google Contact back-sync (update improved names)

### Shopify Integration (P1)
- [ ] Split orders into WEB PAID / WEB COD channels
- [ ] Shopify webhook handling
- [ ] Auto-conversion tracking on order import

### Logistics (P1)
- [ ] Enhance UI to ClickPost-level premium experience
- [ ] Bulk actions for shipment assignment

### Future (P2)
- [ ] Lead assignment to sales reps
- [ ] WhatsApp inbound reply tracking
- [ ] Campaign attribution analytics
- [ ] Pincode master data import

---

## Credentials
- **Superuser**: admin / admin123
- **Database**: PostgreSQL (elvis_db, elvis_dbuser)
