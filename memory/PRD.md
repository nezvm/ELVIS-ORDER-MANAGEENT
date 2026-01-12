# Elvis-Manager ERP - Product Requirements Document

## Original Problem Statement
Build a comprehensive ERP system for Elvis brand management with:
- Modern unified UI/UX theme
- Marketing module (Leads, WhatsApp, Campaigns, Market Insights)
- Shopify abandoned cart recovery
- Quick Order Entry for mass entry
- Business Day logic (IST 8PM-8PM)
- Finance module (Accounts, Remittances, Expenses, Ledger)
- Users & Roles with permission management

## Tech Stack
- **Backend:** Django 4.x, Django REST Framework
- **Database:** SQLite (development), PostgreSQL (production)
- **Frontend:** Django Template Language + Tailwind CSS (CDN)
- **Async:** Celery + Redis

---

## What's Completed (Jan 12, 2026)

### 0. UI Theme Unification (100% Complete) ✅
- [x] All templates migrated to extend `ui/base.html`
- [x] Black sidebar with Elvis branding and primary color #AE1F25
- [x] White top bar with search, notifications, Quick Add button
- [x] Registration/auth templates use dedicated `registration_base.html`
- [x] Error pages (400, 401, 403, 404, 500, 503) updated
- [x] Old base templates removed

### 1. Quick Order Entry (100% Complete) ✅
**Route:** `/master/orders/quick-entry/`
- [x] Channel cards with today's stats (count + amount)
- [x] One-click channel switching without data loss
- [x] Customer phone lookup with auto-fill
- [x] Pincode → City/State auto-fill
- [x] Product search with typeahead
- [x] Items grid with inline qty/price editing
- [x] Real-time subtotal/total calculation
- [x] Keyboard shortcuts:
  - Ctrl+Enter: Save Order
  - Alt+N: Save & New
  - Alt+C: Focus channel cards
  - Arrow keys: Navigate channels
  - Enter: Add new item row
- [x] "Keep channel on Save & New" toggle
- [x] Business Day indicator (IST 8PM-8PM)
- [x] No "Order Date" field - uses created_at

### 2. CTA Consistency (100% Complete) ✅
- [x] Orders: Quick Entry + New Order buttons
- [x] Customers: + Add Customer button
- [x] Products: + Add Product button
- [x] Empty states have centered Add buttons

### 3. Marketing Module ✅
- [x] Leads management with sync status
- [x] WhatsApp page (placeholder)
- [x] Campaigns page (placeholder)
- [x] Market Insights with geo-intelligence tabs

### 4. Shopify Abandoned Cart Feature ✅ (MOCKED)
- [x] Lead model extended for abandoned carts
- [x] Merge logic for duplicate leads
- [x] Conversion tracking
- [x] Dashboard metrics

---

## In Progress / Pending

### Phase 2: Business Day Logic (P0) - NOT STARTED
- [ ] BusinessDay model (`date`, `is_closed`, `closed_by`, `closed_at`)
- [ ] Business Day selector on Orders/Finance pages
- [ ] Utility: `get_business_day_range(date)` → IST 8PM-8PM
- [ ] "Day Close" action to lock totals
- [ ] Shopify sync respects closed business days

### Phase 3: Finance Module (P0) - NOT STARTED
Create new Django app: `finance/`

**Models:**
- [ ] Account (name, code, type, opening_balance, current_balance)
- [ ] Remittance (date, business_day, channel, carrier, account, amount, fee, UTR)
- [ ] Expense (category, amount, paid_from_account, notes, attachment)
- [ ] DailySummary (computed aggregates)

**Pages:**
- [ ] Accounts list/create/edit
- [ ] Remittances list/create
- [ ] Expenses list/create (by business day)
- [ ] Daily Summary dashboard
- [ ] Ledger view with Excel/PDF export

**Channel → Account Mapping:**
- [ ] Settings page for channel → default account
- [ ] COD handling rules (credits/debits display)

### Phase 4: Users, Roles & Permissions (P1) - NOT STARTED
- [ ] Role model with permission matrix
- [ ] Permission categories: Orders, Customers, Products, Logistics, Marketing, Integrations, Finance, Settings
- [ ] Checkbox UI for role permissions (Shopify-style)
- [ ] UI enforcement (hide menu items)
- [ ] Backend enforcement (decorators)

---

## Backlog / Future

### Real Integrations (P0)
- [ ] Google OAuth for contacts sync (replace mock)
- [ ] Meta Cloud API for WhatsApp (replace mock)
- [ ] Shopify Admin API for abandoned checkouts (replace mock)

### Responsive Design (P0)
- [ ] Collapsible sidebar for tablet/mobile

### Enhancements (P1)
- [ ] Shopify order split: WEB PAID / WEB COD channels
- [ ] Enhance Logistics to "ClickPost-level" experience
- [ ] Lead assignment to sales reps
- [ ] WhatsApp inbound reply tracking

---

## Key Files Reference

### Core Templates
- `/app/templates/ui/base.html` - Main unified theme
- `/app/templates/order/quick_entry.html` - Quick Order Entry
- `/app/templates/order/order_list.html` - Orders list

### Views
- `/app/master/views.py` - QuickOrderEntryView, quick_order_save

### Models
- `/app/master/models.py` - Account, Channel, Customer, Order, Product
- `/app/marketing/models.py` - Lead, Campaign, PincodeMaster

---

## Test Data Created
- **Channels:** WhatsApp, WhatsApp_COD, Counter, Swiggy, Shopify
- **Accounts:** Cash, COD Receivables, NIZAM AXIS, HDFC Business
- **Products:** Classic T-Shirt, Slim Fit Jeans, Cotton Polo, Hooded Sweatshirt
- **Admin User:** admin / admin123

---

## Mocked APIs (Placeholder Implementations)
- Google Contacts sync
- Shopify Abandoned Checkout sync
- WhatsApp Meta Cloud API

---

*Last Updated: Jan 12, 2026*
