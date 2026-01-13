# Elvis-Manager ERP - Architecture Documentation

## System Overview

Elvis-Manager is a modular Django ERP system designed for order management, logistics, inventory, customer segmentation, and marketing. The architecture follows a **modular overlay pattern** where new features are added as separate Django apps that reference (but don't modify) existing core models.

---

## Architecture Diagram (Text-Based)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              ELVIS-MANAGER ERP                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                         PRESENTATION LAYER                                │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐          │   │
│  │  │  Django    │  │  REST API  │  │  Admin     │  │  Webhooks  │          │   │
│  │  │  Templates │  │  (DRF)     │  │  Interface │  │  Endpoints │          │   │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘          │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                           │
│  ┌───────────────────────────────────┼──────────────────────────────────────┐   │
│  │                    BUSINESS LOGIC LAYER (Django Apps)                     │   │
│  │                                   │                                       │   │
│  │  ┌─────────────┐  ┌──────────────┴──────────────┐  ┌─────────────┐       │   │
│  │  │   CORE      │  │         MASTER               │  │  ACCOUNTS   │       │   │
│  │  │   --------  │  │         ------               │  │  ---------  │       │   │
│  │  │   Settings  │  │  Account, Channel, Customer  │  │  User       │       │   │
│  │  │   BaseModel │  │  Product, Order, OrderItem   │  │  Auth       │       │   │
│  │  │   Mixins    │◄─┤  Vendor, Purchase            │  │             │       │   │
│  │  └─────────────┘  └──────────────────────────────┘  └─────────────┘       │   │
│  │         ▲                        ▲                          ▲              │   │
│  │         │         ┌──────────────┴──────────────┐           │              │   │
│  │         │         │                             │           │              │   │
│  │  ┌──────┴─────────┴──┐  ┌────────────────┐  ┌──┴───────────────┐          │   │
│  │  │  CHANNELS_CONFIG  │  │   LOGISTICS    │  │    INVENTORY      │          │   │
│  │  │  ---------------  │  │   ----------   │  │    -----------    │          │   │
│  │  │  DynamicChannel   │  │   Carrier      │  │    Warehouse      │          │   │
│  │  │  ChannelFormField │  │   Credential   │  │    StockLevel     │          │   │
│  │  │  UTRRecord        │  │   ShippingRule │  │    StockMovement  │          │   │
│  │  └───────────────────┘  │   Shipment     │  │    StockTransfer  │          │   │
│  │                         │   NDRRecord    │  │    ReorderRule    │          │   │
│  │                         └────────────────┘  └───────────────────┘          │   │
│  │                                                                            │   │
│  │  ┌───────────────────┐  ┌────────────────┐  ┌───────────────────┐          │   │
│  │  │   SEGMENTATION    │  │   MARKETING    │  │   INTEGRATIONS    │          │   │
│  │  │   ------------    │  │   ----------   │  │   -------------   │          │   │
│  │  │   CustomerProfile │  │   Lead         │  │   IntegrationCfg  │          │   │
│  │  │   CustomerSegment │  │   Campaign     │  │   ShopifyStore    │          │   │
│  │  │   CohortAnalysis  │  │   WhatsApp     │  │   GoogleWorkspace │          │   │
│  │  │   SegmentExport   │  │   GeoStats     │  │   WebhookEndpoint │          │   │
│  │  └───────────────────┘  └────────────────┘  └───────────────────┘          │   │
│  └────────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                           │
│  ┌───────────────────────────────────┼──────────────────────────────────────┐   │
│  │                        DATA LAYER                                         │   │
│  │  ┌─────────────┐  ┌───────────────┴───────────────┐  ┌─────────────┐      │   │
│  │  │   SQLite    │  │       Feature Flags           │  │   Redis     │      │   │
│  │  │   (Dev)     │  │       (Settings-based)        │  │   (Celery)  │      │   │
│  │  │   PostgreSQL│  └───────────────────────────────┘  │             │      │   │
│  │  │   (Prod)    │                                     │             │      │   │
│  │  └─────────────┘                                     └─────────────┘      │   │
│  └────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────────┐  │
│  │                    EXTERNAL INTEGRATIONS                                    │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │  │
│  │  │Delhivery │  │ BlueDart │  │   DTDC   │  │ Shopify  │  │  Google  │      │  │
│  │  │   API    │  │   API    │  │   API    │  │   API    │  │ Contacts │      │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │  │
│  └────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Module Relationships

### Core Dependencies

| Module | Depends On | Purpose |
|--------|------------|----------|
| `core` | None | Base models, mixins, utilities |
| `accounts` | `core` | User authentication & management |
| `master` | `core`, `accounts` | Core business entities (Orders, Customers, Products) |
| `channels_config` | `core`, `master`, `accounts` | Dynamic channel configuration |
| `logistics` | `core`, `master`, `accounts` | Shipping & carrier management |
| `inventory` | `core`, `master`, `accounts` | Warehouse & stock management |
| `segmentation` | `core`, `master`, `accounts` | Customer profiling & segmentation |
| `marketing` | `core`, `master`, `accounts` | Leads, campaigns, market insights |
| `integrations` | `core`, `master`, `accounts`, `channels_config` | External service connections |

---

## Feature Toggle System

All new modules can be enabled/disabled via `settings.py`:

```python
# Feature Flags (in elvis_erp/settings.py)
FEATURE_FLAGS = {
    'ENABLE_LOGISTICS_MODULE': True,      # Carrier management, shipping rules
    'ENABLE_INVENTORY_MODULE': True,      # Warehouse, stock levels
    'ENABLE_SEGMENTATION_MODULE': True,   # Customer profiles, segments
    'ENABLE_MARKETING_MODULE': True,      # Leads, campaigns
    'ENABLE_INTEGRATIONS_MODULE': True,   # Shopify, Google, etc.
    'ENABLE_DYNAMIC_CHANNELS': True,      # DynamicChannel instead of static
    'USE_LEGACY_SHIPPING': False,         # Fallback to courier_partner.py
}
```

---

## Data Flow Patterns

### 1. Order Creation Flow
```
User Input → Channel Selection → Customer Lookup → Product Selection
     ↓
Order.save() → Generate order_no → Create OrderItems
     ↓
[If ENABLE_LOGISTICS_MODULE]
     → ShippingRuleEngine.allocate_carrier(order)
     → Shipment.create()
     → CarrierAPI.book_shipment()
```

### 2. Inventory Update Flow
```
[If ENABLE_INVENTORY_MODULE]
Order Shipped → Signal → StockMovement.create(type='sale')
     ↓
StockLevel.quantity -= order_qty
     ↓
[If quantity < reorder_point]
     → InventoryAlert.create(type='low_stock')
```

### 3. Customer Segmentation Flow
```
[If ENABLE_SEGMENTATION_MODULE]
Nightly Celery Task → SegmentationService.compute_all_profiles()
     ↓
For each Customer:
     → Aggregate orders, revenue, frequency
     → Assign value_tier, lifecycle_stage
     → Update CustomerProfile
     ↓
SegmentationService.assign_segments()
     → Apply segment criteria
     → Create CustomerSegmentMembership
```

---

## Credential Management

### Before (Hardcoded in `core/courier_partner.py`)
```python
# ❌ BAD - Hardcoded tokens
DELHIVERY_API_TOKEN = "5cacd11fe65085f5f87966d84a79c506400c7c5e"
```

### After (Stored in `logistics.CarrierCredential`)
```python
# ✅ GOOD - Database-stored credentials
from logistics.models import CarrierCredential

def get_carrier_credentials(carrier_code, environment='production'):
    return CarrierCredential.objects.get(
        carrier__code=carrier_code,
        environment=environment,
        is_active=True
    )
```

---

## API Contracts

### Internal API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|----------|
| `/api/orders/` | GET, POST | Order CRUD |
| `/api/customers/` | GET, POST | Customer CRUD |
| `/api/products/` | GET, POST | Product CRUD |
| `/api/logistics/carriers/` | GET | List carriers |
| `/api/logistics/shipments/` | GET, POST | Shipment management |
| `/api/inventory/stock/` | GET | Stock levels |
| `/api/segmentation/profiles/` | GET | Customer profiles |
| `/api/marketing/leads/` | GET, POST | Lead management |

### Webhook Endpoints

| Endpoint | Provider | Purpose |
|----------|----------|----------|
| `/webhooks/shopify/orders/` | Shopify | Order sync |
| `/webhooks/shopify/checkouts/` | Shopify | Abandoned cart sync |
| `/webhooks/carriers/{code}/` | Carriers | Tracking updates |

---

## Benefits of Modular Architecture

1. **Non-destructive upgrades** - New features added without modifying existing models
2. **Feature toggles** - Enable/disable modules per deployment
3. **Credential security** - API tokens stored in database, not code
4. **Scalability** - Each module can be scaled independently
5. **Testability** - Modules can be tested in isolation
6. **Backward compatibility** - Legacy code continues to work when modules disabled

---

## Optional/Deferrable Modules

| Module | Priority | Can Defer Until |
|--------|----------|------------------|
| `segmentation` | Medium | Customer base > 1000 |
| `marketing` | Medium | Need campaign management |
| `inventory` | High | Multi-warehouse operations |
| `integrations` | High | Shopify/external sync needed |
| `channels_config` | Low | Dynamic channel creation needed |

---

## Operational Overhead

### Required Configuration
1. **Carriers** - Add carriers and credentials via admin
2. **Warehouses** - Configure warehouse locations
3. **Shipping Rules** - Set up carrier allocation rules
4. **Segments** - Define customer segment criteria

### Background Tasks (Celery)
1. `compute_customer_profiles` - Daily at 2 AM
2. `sync_shopify_orders` - Every 15 minutes
3. `update_tracking_status` - Every 30 minutes
4. `send_campaign_messages` - As scheduled

---

*Last Updated: January 2025*
