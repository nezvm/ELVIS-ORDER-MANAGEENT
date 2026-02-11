# Elvis-Manager ERP - Product Requirements Document

## Overview
Elvis-Manager is a modular Django ERP system for order management, logistics, inventory tracking, customer segmentation, and marketing. The system follows a **modular overlay architecture** where new features are added as separate Django apps without modifying existing core models.

## Architecture Summary

### Module Structure
```
/app/
├── accounts/           # User authentication & management
├── core/               # Base models, mixins, utilities, feature flags
├── master/             # Core business entities (Orders, Customers, Products, Vendors)
├── channels_config/    # Dynamic channel configuration
├── logistics/          # Shipping, carriers, NDR management
├── inventory/          # Warehouse, stock levels, movements
├── segmentation/       # Customer profiles, segments, cohort analysis
├── marketing/          # Leads, campaigns, market insights
├── integrations/       # Shopify, Google Workspace, webhooks
├── elvis_erp/          # Django project settings
└── templates/          # UI templates (refined design)
```

### Feature Flags
All modules can be enabled/disabled via `elvis_erp/settings.py`:
- `ENABLE_LOGISTICS_MODULE` - Carrier management, shipping rules, NDR
- `ENABLE_INVENTORY_MODULE` - Warehouse, stock levels, movements
- `ENABLE_SEGMENTATION_MODULE` - Customer profiles, segments, cohorts
- `ENABLE_MARKETING_MODULE` - Leads, campaigns, market insights
- `ENABLE_INTEGRATIONS_MODULE` - Shopify, Google, webhooks
- `ENABLE_DYNAMIC_CHANNELS` - Dynamic channel configuration
- `USE_LEGACY_SHIPPING` - Fallback to old courier_partner.py

### Credential Management
API credentials stored in database (`CarrierCredential` model) instead of hardcoded values:
- Delhivery, BlueDart, TPC, DTDC configurations
- Environment variable fallback for legacy support
- Admin panel for credential management

## Key Models

### Core/Master
- `Account` - Financial accounts
- `Channel` - Sales channels (WhatsApp, Swiggy, etc.)
- `Product` - Products with stock calculation
- `Customer` - Customer data with addresses
- `Order` - Orders with tracking, shipping status
- `OrderItem` - Line items in orders
- `CourierPartner` - Shipping carriers (legacy)
- `Vendor` - Suppliers for purchase orders
- `Purchase` - Purchase orders from vendors

### Logistics
- `Carrier` - Shipping carriers with credentials
- `CarrierCredential` - API credentials per environment
- `ShippingRule` - Automatic carrier allocation rules
- `Shipment` - Individual shipments with tracking
- `NDRRecord` - Non-delivery reports

### Inventory
- `Warehouse` - Physical warehouse locations
- `StockLevel` - Product stock per warehouse
- `StockMovement` - Stock in/out records
- `StockTransfer` - Inter-warehouse transfers

### Segmentation
- `CustomerProfile` - Aggregated customer data
- `CustomerSegment` - Customer groupings
- `CohortAnalysis` - Customer cohort tracking

### Marketing
- `Lead` - Sales leads
- `Campaign` - Marketing campaigns
- `GeoMarketStats` - Geographic market data

## API Endpoints

### Main Application Routes
| URL | View | Purpose |
|-----|------|---------|
| `/` | Dashboard | Main dashboard |
| `/master/orders/` | OrderListView | Order management |
| `/master/customers/` | CustomerListView | Customer management |
| `/master/products/` | ProductListView | Product management |
| `/master/accounts/` | AccountListView | Account management |

### Logistics
| URL | View | Purpose |
|-----|------|---------|
| `/logistics/panel/` | LogisticsPanel | Logistics overview |
| `/logistics/carriers/` | CarrierListView | Carrier management |
| `/logistics/ndr/` | NDRListView | NDR management |
| `/logistics/rules/` | ShippingRuleListView | Shipping rules |
| `/logistics/shipments/` | ShipmentListView | Shipment tracking |

### Inventory
| URL | View | Purpose |
|-----|------|---------|
| `/inventory/` | InventoryDashboard | Inventory overview |
| `/inventory/warehouses/` | WarehouseListView | Warehouse management |
| `/inventory/stock/` | StockLevelListView | Stock levels |
| `/inventory/movements/` | StockMovementListView | Stock movements |
| `/inventory/transfers/` | StockTransferListView | Transfers |

### Segmentation
| URL | View | Purpose |
|-----|------|---------|
| `/segmentation/` | SegmentationDashboard | Overview & metrics |
| `/segmentation/profiles/` | CustomerProfileListView | Customer profiles |
| `/segmentation/segments/` | CustomerSegmentListView | Segments |
| `/segmentation/cohorts/` | CohortAnalysisView | Cohort analysis |

### User Management
| URL | View | Purpose |
|-----|------|---------|
| `/accounts/login/` | LoginView | User login |
| `/accounts/users/` | UserListView | User management |

## Admin Panel
Access at `/admin/` with enhanced management for:
- Carrier credentials (with masking)
- Shipping rules (JSON conditions editor)
- Customer segments
- All core models

## Authentication
- Django session-based authentication
- Default admin: `admin` / `admin123`
- CSRF protection enabled

## Benefits of Architecture
1. **Non-destructive upgrades** - New features don't modify existing models
2. **Feature toggles** - Enable/disable modules per deployment
3. **Credential security** - API tokens in database, not code
4. **Backward compatibility** - Legacy code works when modules disabled
5. **Scalability** - Modules can be scaled independently

## Status
- **Backend**: ✅ All 16+ endpoints working (100% success rate)
- **Frontend**: ✅ All templates implemented with refined UI
- **Admin Panel**: ✅ Enhanced with credential management
- **Testing**: ✅ Comprehensive backend tests passing
- **WhatsApp Integration**: ✅ Complete with Direct Import feature

---

## WhatsApp Integration Module

### Overview
The WhatsApp integration module (`integrations/whatsapp/`) enables automated lead capture from WhatsApp Business numbers via Meta Cloud API webhooks.

### Key Features
1. **Webhook Processing** - Receives and processes incoming WhatsApp messages
2. **Lead Attribution** - Tags leads as "Ad" (from Click-to-WhatsApp ads) or "Organic/Direct"
3. **Customer Deduplication** - Single customer record across multiple business numbers
4. **Direct Import** - Import existing WhatsApp numbers by Phone Number ID (bypasses Embedded Signup)

### Models
| Model | Purpose |
|-------|---------|
| `WhatsAppCustomer` | Global customer record with attribution data |
| `WhatsAppNumberConfig` | Business number configuration (stores imported numbers) |
| `WhatsAppConnectedNumber` | Connected numbers with WABA credentials |
| `WhatsAppCustomerChannel` | Tracks which numbers a customer contacted |
| `WhatsAppMessage` | Message history |
| `WhatsAppWebhookLog` | Webhook audit log |

### API Endpoints
| URL | Method | Purpose |
|-----|--------|---------|
| `/webhooks/whatsapp/` | GET | Meta webhook verification |
| `/webhooks/whatsapp/` | POST | Receive incoming messages |
| `/integrations/whatsapp/` | GET | Dashboard & setup page |
| `/integrations/whatsapp/import/` | GET | Import numbers UI |
| `/integrations/whatsapp/import-number/` | POST | Import single number API |
| `/integrations/whatsapp/customers/` | GET | WhatsApp leads list |
| `/integrations/whatsapp/customer/<uuid>/` | GET | Lead detail view |

### Imported Numbers (Elvis Co Portfolio)
All 12 WhatsApp Business numbers have been imported:
- Sales 1-12 with Phone Number IDs from user's Meta Business Portfolio
- WABA ID: 946871127168555

### Configuration
- Verify Token: `elvis_whatsapp_verify_2024` (in settings.py `WA_VERIFY_TOKEN`)
- Webhook URL: `{APP_URL}/webhooks/whatsapp/`

### Attribution Logic
Messages from Click-to-WhatsApp ads include `referral` data in webhook payload:
- `source_type: "ad"` → Tagged as `ctwa_ad`, `is_from_ad=True`
- No referral data → Tagged as `organic`

*Last Updated: February 2025*
