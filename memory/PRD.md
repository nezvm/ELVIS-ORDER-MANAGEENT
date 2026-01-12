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

## Core Requirements

### 1. UI/UX Overhaul (✅ COMPLETED - Dec 12, 2025)
- [x] Modern sidebar navigation (black theme)
- [x] Top bar with search, notifications, quick add
- [x] Card-based layouts with #AE1F25 accent color
- [x] Consistent design system across all modules
- [x] Responsive tables with filters and pagination

### 2. Marketing Module

#### 2.1 Leads Management (✅ COMPLETED - Dec 12, 2025)
- [x] Lead model with phone, name, address, segmentation fields
- [x] WIN/LOSS classification based on customer/order matching
- [x] Lead list with filters (match_status, lead_status, state, search)
- [x] Lead detail view with activity timeline
- [x] Lead creation/edit forms
- [x] Stats dashboard (Total, WIN, LOSS, Conversion Rate)
- [x] Google Contacts sync (MOCKED - placeholder implementation)

#### 2.2 WhatsApp Broadcasting (✅ COMPLETED - Dec 12, 2025)
- [x] WhatsApp Provider model (Meta Cloud API focus)
- [x] Provider CRUD with API credentials fields
- [x] Message Template management
- [x] Notification Events configuration
- [x] Message Logs tracking
- [x] WhatsApp dashboard with stats
- [x] Meta Cloud API integration (MOCKED - placeholder)

#### 2.3 Campaigns (✅ COMPLETED - Dec 12, 2025)
- [x] Campaign model with status workflow
- [x] Campaign recipients tracking
- [x] Campaign creation with template/provider selection
- [x] Campaign start/pause functionality
- [x] Conversion tracking with attribution window
- [x] Campaign analytics (sent, delivered, read, failed, conversions)

#### 2.4 Market Insights (✅ COMPLETED - Dec 12, 2025)
- [x] GeoMarketStats model for geo-aggregation
- [x] State-wise performance table
- [x] Hot Markets view (high revenue/order areas)
- [x] Cold Zones view (high leads, low conversion)
- [x] New Markets identification
- [x] Refresh Data functionality

## Technical Architecture

```
/app/
├── elvis_erp/             # Main Django project
├── marketing/             # NEW - Marketing module
│   ├── models.py          # Lead, Campaign, WhatsApp models
│   ├── views.py           # Class-based views
│   ├── urls.py            # URL routing
│   ├── services.py        # Business logic
│   └── forms.py           # Form definitions
├── templates/ui/          # NEW - Modern UI templates
│   └── base.html          # Base template with sidebar
├── integrations/          # Google, Shopify integrations
├── channels_config/       # Dynamic sales channels
├── logistics/             # Shipping and carriers
├── inventory/             # Stock management
└── segmentation/          # Customer segmentation
```

## Database Schema (Marketing)
- **Lead**: Phone, name, email, address, match_status, lead_status, segmentation fields
- **WhatsAppProvider**: Meta Cloud API credentials, status, rate limits
- **WhatsAppTemplate**: Message templates with variables
- **Campaign**: Name, provider, template, status, stats
- **CampaignRecipient**: Per-recipient tracking
- **MessageLog**: Individual message delivery tracking
- **GeoMarketStats**: Aggregated geo metrics

## API Endpoints (Marketing)
- `POST /marketing/api/leads/sync/` - Sync Google contacts
- `POST /marketing/api/lead/<pk>/match/` - Re-match lead
- `POST /marketing/api/lead/<pk>/convert/` - Convert to customer
- `POST /marketing/api/provider/<pk>/test/` - Test provider connection
- `POST /marketing/api/campaign/<pk>/start/` - Start campaign
- `POST /marketing/api/campaign/<pk>/pause/` - Pause campaign
- `POST /marketing/api/insights/refresh/` - Refresh geo stats
- `GET /marketing/api/lead-stats/` - Get lead statistics

## MOCKED Integrations
⚠️ The following integrations are MOCKED with placeholder implementations:
1. **Google Contacts Sync** - Generates mock contacts, syncs to Lead model
2. **Meta Cloud API (WhatsApp)** - Mock provider test, message sending

## Credentials
- **Superuser**: admin / admin123
- **Database**: PostgreSQL (elvis_db, elvis_dbuser)

## What's Completed (Dec 12, 2025)
1. ✅ Modern UI with black sidebar, white content, #AE1F25 accents
2. ✅ Complete Marketing module (Leads, WhatsApp, Campaigns, Insights)
3. ✅ All CRUD operations for marketing entities
4. ✅ Market geo-analytics with Hot/Cold/New market tagging
5. ✅ Frontend testing passed (100% success rate)

## Pending / Backlog (P1)

### Real Integrations
- [ ] Implement actual Google OAuth flow for contacts sync
- [ ] Implement actual Meta Cloud API for WhatsApp
- [ ] Google Contact back-sync (update improved names)

### Shopify Integration
- [ ] Refine Shopify order sync to split WEB PAID / WEB COD channels
- [ ] Implement real Shopify webhook handling

### Logistics
- [ ] Enhance Logistics UI to premium "ClickPost-level" experience
- [ ] Bulk actions for shipment assignment

### UI Polish
- [ ] Install Tailwind via PostCSS (replace CDN)
- [ ] Add favicon and fix 404 static resources
- [ ] Migrate remaining old templates to new UI

## Future Enhancements (P2)
- Lead assignment to sales reps
- WhatsApp inbound reply tracking
- Campaign attribution analytics
- Real-time notification system
