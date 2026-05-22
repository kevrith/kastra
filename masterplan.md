# KASTRA ENTERPRISES MANAGEMENT SYSTEM — MASTERPLAN
**Version:** 3.0 (As-Built — May 2026)
**Owner:** Kelvin
**Stack:** React 18 + FastAPI + PostgreSQL
**Status:** Feature-complete. Production-ready.

---

## 1. APP OVERVIEW & OBJECTIVES

Kastra Enterprises Management System is a business operations platform built for Kenyan SMEs. It manages the full sales cycle — from quotation creation through invoice management to payment collection — with deep local market integration: M-Pesa STK Push, Paystack card payments, WhatsApp link sharing, KRA eTIMS compliance, and a public client portal.

### Primary Objectives
- Reduce quotation creation time by 70%
- Process KSh 10M+ in invoices monthly
- Support 500+ active users within 6 months
- Achieve 95%+ uptime with offline-capable frontend (PWA)
- Provide a fully compliant, KRA eTIMS-ready invoicing workflow

---

## 2. TARGET AUDIENCE

**Primary Users:**
- Kenyan SME owners and managers
- Freelancers and independent consultants
- Small agencies (design, tech, logistics, construction)

**User Personas:**
- **Admin:** Full access — manages users, settings, reports, all data
- **Manager:** Creates quotations/invoices, manages clients, views reports

**Client Persona (external — no login):**
- Receives a WhatsApp link to their portal or individual document
- Views invoices and quotations, pays online, accepts/declines quotes

**Market Context:**
- M-Pesa is the dominant payment method — STK Push fully integrated
- Paystack handles card payments (Visa/Mastercard) for clients who prefer card
- WhatsApp is the primary business communication channel — share links directly
- Mobile-first usage patterns (majority on Android devices)
- 16% VAT compliance is a legal requirement — auto-calculated on all documents
- KRA eTIMS e-invoicing — fully implemented with QR code verification

---

## 3. CORE FEATURES & FUNCTIONALITY (ALL BUILT)

### 3.1 Authentication & User Management ✅
- Email/password login with JWT access + refresh tokens
- Google OAuth login (one-click sign-in)
- Token version blacklisting (logout invalidates all sessions)
- Role-based access control: Admin / Manager
- Password reset via email (SendGrid)
- Kenya DPA 2019 consent checkbox on registration (consent_at timestamp stored)
- Change password endpoint

### 3.2 Quotation Management ✅
- Create quotations with multiple line items (drag-sort supported)
- Auto-calculations: subtotal, 16% VAT, grand total
- ID format: `QT-YYYY-XXX` (auto-incremented per year, per org)
- Status workflow: `Draft → Pending → Accepted / Declined`
- Expiry date (`expires_at`) — quotation auto-marked expired by scheduler
- Custom footer notes per quotation
- PDF generation — three professional branded templates: **Classic, Executive, Vivid**
- Template selected per business in Settings (auto-saved on click)
- WhatsApp sharing — sends quotation portal link with pre-filled message
- Copy quotation portal link — shareable URL for client to view and respond
- Public quotation portal: client can Accept or Decline via a link (no login)
- Search and filter by status, client, date range
- Edit, delete quotations (draft/pending only)
- One-click convert accepted quotation to invoice

### 3.3 Invoice Management ✅
- One-click conversion from accepted quotations
- ID format: `INV-YYYY-XXX` (sequential, auto-incremented per org)
- Reference to originating quotation maintained
- Payment status: `Unpaid → Paid`
- Overdue detection: unpaid invoices past due_date flagged with badge
- Payment methods: M-Pesa, Bank Transfer, Cash (via Mark Paid)
- **M-Pesa STK Push** — trigger payment prompt to client's phone (from dashboard or public portal)
- **Paystack card payment** — client pays with Visa/Mastercard on the public payment page
- Automatic invoice status update on M-Pesa callback (Safaricom IP whitelist in production)
- Automatic invoice status update on Paystack webhook (HMAC-SHA512 verified)
- Email notification to business owner on payment received
- WhatsApp share — sends payment link with pre-filled message to client
- Copy payment link — `/pay/{invoice_id}` shareable URL
- Audit log entry created on every payment event
- KRA eTIMS submission — get Control Unit Invoice Number + QR code on invoice PDF
- PDF generation with eTIMS QR code (if submitted)
- Filter by payment status (All / Unpaid / Paid / Overdue), client

### 3.4 Client Management ✅
- Full client profile: name, email, phone, address
- Phone stored in M-Pesa format: `254XXXXXXXXX` (auto-normalised from 07XX)
- Client status: Active / Inactive
- **Client portal token** — each client has a unique permanent portal URL
- View all quotations and invoices per client
- Aggregated stats: total billed, invoice count, paid/unpaid counts
- Client portal card: copy link, send via WhatsApp, preview in browser

### 3.5 Public Client Portal ✅
- **Client portal** at `/portal/c/{token}` — shareable, no login required
  - Shows all invoices and quotations for that client
  - Invoices tab: amount, status, due date — click to pay online
  - Quotations tab: amount, status, expiry — click to view and respond
- **Public quotation view** at `/portal/q/{quotation_id}`
  - Full quotation detail: items, totals, expiry, business contact
  - Accept / Decline buttons (updates quotation status in real time)
- **Public invoice payment** at `/pay/{invoice_id}`
  - Pay via M-Pesa STK Push (polls automatically until confirmed)
  - Pay via Paystack card (redirects to Paystack hosted page, returns to verify page)

### 3.6 Paystack Card Payments ✅
- Initialize payment via `POST /api/paystack/initialize`
- Redirect to Paystack hosted payment page (handles Visa/Mastercard/USSD)
- Webhook at `/api/paystack/webhook` (HMAC-SHA512 verified, skipped in dev)
- On success: marks invoice paid, creates PaymentDetail, audit log, sends email
- Verify page at `/portal/paystack/verify` — polls invoice until confirmed

### 3.7 M-Pesa Daraja Integration ✅
- STK Push from business dashboard (authenticated) and public payment portal (no auth)
- Callback at `/api/mpesa/callback` — Safaricom IP whitelist enforced in production
- Idempotency: double-callback for same invoice is a no-op
- Stores receipt number, transaction ID, payment date
- Email notification to business owner on success

### 3.8 KRA eTIMS Integration ✅
- Submit invoice to KRA: `POST /api/invoices/{id}/etims-submit`
- Returns Control Unit Invoice Number (`etims_cu_invoice_no`)
- eTIMS QR code rendered on invoice PDF for client scanning
- eTIMS credentials (Device Serial + Auth Token) managed in Settings
- "Test KRA Connection" button in Settings validates credentials
- Enable/disable eTIMS per organization

### 3.9 Dashboard ✅
- KPI cards: Pending Quotations, Unpaid Invoices, Monthly Revenue, Active Clients
- Monthly income bar chart (last 6 months)
- Yearly income trend line chart
- Top 5 clients by total value
- Recent activity feed (latest quotations and invoices)
- All stats computed server-side

### 3.10 Reports ✅
- Monthly income breakdown
- Client revenue analysis
- Quotation-to-invoice conversion rates
- Date range and client filters
- Export to CSV

### 3.11 Settings ✅
- **Business Profile:** name, email, phone, address, KRA PIN, payment terms, logo upload
- **Document Template:** Classic / Executive / Vivid — auto-saved on click
- **KRA eTIMS:** enable toggle, Device Serial, Auth Token, Branch ID, test connection
- **Account info:** view email, name, role
- **Change Password**

### 3.12 Kenya DPA 2019 Compliance ✅
- Consent checkbox + `consent_at` timestamp on registration
- Privacy Policy page (`/privacy`) — 11 sections, DPA 2019 compliant
- Terms of Service page (`/terms`)
- Right to erasure: `DELETE /api/auth/me`
- Data portability: `GET /api/auth/me/export` (JSON download)
- Audit log: immutable table tracking all financial actions (create/update/payment)
- Security headers: X-Content-Type-Options, X-Frame-Options, Referrer-Policy, etc.

### 3.13 Progressive Web App (PWA) ✅
- `manifest.json` — installable on Android/iOS home screen
- Service worker — pre-caches offline fallback page
- Offline page (`/offline.html`) — branded fallback when offline
- Theme colour, Apple touch icon, meta tags

### 3.14 Error Tracking & Monitoring ✅
- **Sentry** on backend — graceful, only initialises if `SENTRY_DSN` is set
- **Sentry** on frontend (`@sentry/react`) — only initialises if `VITE_SENTRY_DSN` is set
- Browser tracing integration, 20% sample rate, no PII

### 3.15 Automated Scheduling ✅
- **APScheduler** runs nightly at 02:00 EAT:
  - Marks overdue invoices with a flag
  - Marks expired quotations
- Quotation expiry also computed in real time via Pydantic `@computed_field`

### 3.16 CI/CD ✅
- GitHub Actions workflow (`.github/workflows/test.yml`)
- Runs full pytest suite on every push/PR to `main` or `develop`
- PostgreSQL 16 service spun up in CI for real DB tests
- 77 tests, all passing

---

## 4. TECHNICAL STACK

### 4.1 Frontend
| Layer | Technology |
|---|---|
| Framework | React 18 + Vite |
| Styling | Tailwind CSS 3 (custom design system via `index.css`) |
| Routing | React Router v6 |
| Charts | Recharts |
| Icons | Lucide React |
| HTTP Client | Axios (separate instances: `api.js` authenticated, `pay.js` / `portal.js` public) |
| Auth State | React Context + localStorage (JWT) |
| PDF Generation | Browser print-to-PDF via `PDFPreviewModal` (no server dependency) |
| Error Tracking | `@sentry/react` (graceful, no-op if DSN not set) |
| PWA | `manifest.json` + `sw.js` service worker |

**Hosting:** Render Static Sites or Vercel

### 4.2 Backend
| Layer | Technology |
|---|---|
| Framework | FastAPI (Python 3.11+) |
| Database ORM | SQLAlchemy async |
| Migrations | Alembic |
| Auth | python-jose (JWT) + passlib (bcrypt) |
| Validation | Pydantic v2 |
| Async HTTP | httpx (M-Pesa, Paystack, eTIMS API calls) |
| Email | SendGrid via httpx |
| Scheduling | APScheduler (in-process, async) |
| Rate Limiting | SlowAPI |
| Error Tracking | Sentry SDK (graceful, no-op if DSN not set) |
| Security | Pure ASGI middleware (security headers), Safaricom IP whitelist, HMAC webhook verification |

**Hosting:** Render Web Service

### 4.3 Database
| Component | Technology |
|---|---|
| Primary DB | PostgreSQL 15+ (Render managed) |
| ORM | SQLAlchemy async + asyncpg |
| Connection Pool | NullPool in tests, default pool in production |
| Backups | Render automated daily backups |

### 4.4 External Integrations
| Service | Purpose | Status |
|---|---|---|
| M-Pesa Daraja API | STK Push + callback | ✅ Production-ready |
| Paystack | Card payments (Visa/Mastercard) | ✅ Needs real keys |
| KRA eTIMS | E-invoicing + QR verification | ✅ Production-ready |
| Google OAuth2 | Social login | ✅ |
| SendGrid | Transactional email (payment notifications, password reset) | ✅ |
| WhatsApp URL scheme | Share links directly from invoice/quotation detail | ✅ |
| Sentry | Error tracking | ✅ Graceful |

---

## 5. DATA MODEL

### Entity Relationships

```
Organization (1) ──── (M) User
     │
     ├──── (M) Client ──── portal_token (unique UUID)
     │         │
     │         ├──── (M) Quotation ──── (M) QuotationItem
     │         │         │
     │         │         └── converts to ──► Invoice ──── (M) InvoiceItem
     │         │                                 │
     │         │                                 └── (1) PaymentDetail
     │         └──── (M) Invoice
     │
     └──── (M) AuditLog
```

### Database Tables

**organizations**
- id (UUID PK), name, email, phone, address, kra_pin
- payment_terms_days (default 30), logo_url, document_template
- etims_enabled, etims_branch_id, etims_device_serial, etims_auth_token
- created_at, updated_at

**users**
- id (UUID PK), organization_id (FK), email, hashed_password, display_name
- role (admin/manager), google_id, token_version, is_active
- consented_at (Kenya DPA 2019), created_at, last_login_at

**clients**
- id (UUID PK), organization_id (FK)
- portal_token (UUID, unique) — permanent shareable portal link token
- name, email, phone (254XXXXXXXXX), address
- status (active/inactive), created_at, updated_at

**quotations**
- id (QT-YYYY-XXX), organization_id (FK), client_id (FK), created_by (FK→users)
- status (draft/pending/accepted/declined)
- subtotal, vat_amount, grand_total, notes
- expires_at (nullable) — scheduler expires at 02:00 EAT daily
- converted_to_invoice (bool), invoice_id (nullable FK)
- created_at, updated_at

**quotation_items**
- id (UUID PK), quotation_id (FK)
- description, quantity, unit_price, line_total, sort_order

**invoices**
- id (INV-YYYY-XXX), organization_id (FK), quotation_id (nullable FK), client_id (FK)
- payment_status (unpaid/paid), payment_method
- subtotal, vat_amount, grand_total
- due_date (set from org.payment_terms_days at invoice creation)
- mpesa_checkout_request_id (for callback matching)
- etims_cu_invoice_no, etims_submitted_at (KRA eTIMS)
- reminders_sent, created_at, updated_at

**invoice_items**
- id (UUID PK), invoice_id (FK)
- description, quantity, unit_price, line_total, sort_order

**payment_details**
- id (UUID PK), invoice_id (FK, unique)
- payment_method (mpesa/bank/cash/card)
- payment_date, mpesa_receipt_number, transaction_id, notes

**sequence_counters**
- organization_id (FK), entity_type (quotation/invoice), year, last_sequence_number
- Ensures per-org sequential IDs that reset each calendar year

**audit_logs**
- id (UUID PK), organization_id, user_id (nullable)
- action (create/update/delete/payment/etims/login/logout/data_export/erasure)
- resource_type, resource_id, detail, created_at
- Immutable — no UPDATE or DELETE allowed

---

## 6. API REFERENCE

### Authentication
```
POST   /api/auth/register            — email/password + consent
POST   /api/auth/login
POST   /api/auth/refresh
POST   /api/auth/logout
POST   /api/auth/forgot-password
POST   /api/auth/reset-password
POST   /api/auth/change-password
GET    /api/auth/google
GET    /api/auth/google/callback
GET    /api/auth/me
DELETE /api/auth/me                  — right to erasure (Kenya DPA)
GET    /api/auth/me/export           — data portability (Kenya DPA)
```

### Organization
```
GET    /api/organization
PUT    /api/organization
POST   /api/organization/logo
```

### Clients
```
GET    /api/clients
POST   /api/clients
GET    /api/clients/{id}
PUT    /api/clients/{id}
DELETE /api/clients/{id}
GET    /api/clients/{id}/history
```

### Quotations
```
GET    /api/quotations
POST   /api/quotations
GET    /api/quotations/{id}
PUT    /api/quotations/{id}
DELETE /api/quotations/{id}
PATCH  /api/quotations/{id}/status
POST   /api/quotations/{id}/convert  → creates invoice
```

### Invoices
```
GET    /api/invoices
GET    /api/invoices/{id}
PATCH  /api/invoices/{id}/mark-paid
POST   /api/invoices/{id}/mpesa-pay  → STK Push
POST   /api/invoices/{id}/etims-submit
POST   /api/invoices/{id}/remind     → returns WhatsApp URL with payment link
```

### Public Payment Portal (no auth)
```
GET    /api/pay/{invoice_id}         → public invoice summary
POST   /api/pay/{invoice_id}/mpesa   → public STK Push
```

### Client Portal (no auth)
```
GET    /api/portal/c/{token}         → all invoices + quotations for client
GET    /api/portal/q/{quotation_id}  → public quotation detail
POST   /api/portal/q/{quotation_id}/respond  → accept or decline
```

### Paystack Card Payments (no auth on initialize, webhook is public)
```
POST   /api/paystack/initialize      → returns Paystack authorization_url
POST   /api/paystack/webhook         → payment confirmation (HMAC verified)
```

### M-Pesa
```
POST   /api/mpesa/callback           → Safaricom callback (public, IP-whitelisted)
```

### Dashboard & Reports
```
GET    /api/dashboard/stats
GET    /api/dashboard/charts
GET    /api/reports/income
GET    /api/reports/clients
GET    /api/reports/export/csv
```

---

## 7. PAYMENT FLOWS

### M-Pesa STK Push Flow
```
1. User (or client on public portal) enters phone number and clicks Pay
2. POST /api/invoices/{id}/mpesa-pay (or /api/pay/{id}/mpesa for public)
3. Backend authenticates with Safaricom → gets access_token
4. Backend sends STK Push → receives CheckoutRequestID → stores on invoice
5. Customer enters M-Pesa PIN on phone
6. Safaricom calls POST /api/mpesa/callback
7. Backend matches CheckoutRequestID → invoice, marks paid, emails business owner
8. Frontend polls GET /api/pay/{id} or /api/invoices/{id} every 3–4s
9. On payment_status = "paid" → UI updates automatically
```

### Paystack Card Payment Flow
```
1. Client on /pay/{invoice_id} enters email, clicks "Pay by Card"
2. POST /api/paystack/initialize → backend calls Paystack API
3. Paystack returns authorization_url → frontend redirects client
4. Client completes payment on Paystack hosted page
5. Paystack redirects client to /portal/paystack/verify?reference={invoice_id}
6. Paystack also sends POST /api/paystack/webhook (HMAC-SHA512 verified)
7. Backend marks invoice paid, creates PaymentDetail, audit log, emails business
8. Verify page polls /api/pay/{reference} until payment_status = "paid"
```

---

## 8. WHATSAPP SHARING FLOWS

| From | What's shared |
|---|---|
| Invoice detail → WhatsApp button | Pre-filled message with invoice amount + `/pay/{invoice_id}` link |
| Invoice detail → Copy Link | Copies `/pay/{invoice_id}` to clipboard |
| Quotation detail → WhatsApp button | Pre-filled message with total + `/portal/q/{quotation_id}` link |
| Quotation detail → Copy Link | Copies `/portal/q/{quotation_id}` to clipboard |
| Client detail → WhatsApp button | Pre-filled message with portal link + `/portal/c/{token}` |
| Client detail → Copy Link | Copies `/portal/c/{token}` to clipboard |

All WhatsApp links use `https://wa.me/{phone}?text=...` — opens WhatsApp Web or app on any device.

---

## 9. DOCUMENT TEMPLATES

Three built-in PDF templates, selectable per business in Settings → Document Template:

| Template | Style |
|---|---|
| **Classic** | Clean layout, green accent bar, white background. Timeless. |
| **Executive** | Dark navy header, amber accent strip, corporate. Refined. |
| **Vivid** | Green gradient header with wave, bold table. Eye-catching. |

Templates apply to both quotations and invoices. Selection is auto-saved (no save button required). PDF is generated via browser print dialog (Ctrl+P → Save as PDF) — no server required.

---

## 10. SECURITY

- **HTTPS only** — enforced by Render in production
- **JWT tokens** — access token (30 min) + refresh token (30 days), token_version blacklisting on logout
- **CORS** — configured to allow only the frontend domain
- **Rate limiting** — SlowAPI on auth endpoints (bypassed in tests via `limiter.enabled = False`)
- **SQL injection protection** — SQLAlchemy ORM parameterized queries
- **Input validation** — Pydantic v2 schemas on all endpoints
- **M-Pesa callback validation** — Safaricom IP whitelist enforced in production
- **Paystack webhook validation** — HMAC-SHA512 signature verification
- **Security headers** — X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy, Permissions-Policy, Cache-Control, HSTS (production only)
- **Kenya DPA 2019** — consent, erasure, portability, audit log, privacy policy
- **No secrets in code** — all secrets via environment variables

---

## 11. FOLDER STRUCTURE (AS-BUILT)

### Backend
```
kastra-backend/
├── app/
│   ├── main.py                  # FastAPI app, middleware, router registration
│   ├── config.py                # Settings via pydantic-settings
│   ├── database.py              # Async SQLAlchemy engine + session
│   ├── dependencies.py          # get_current_user, get_db
│   ├── models/
│   │   ├── user.py
│   │   ├── client.py            # includes portal_token
│   │   ├── quotation.py         # includes expires_at
│   │   ├── invoice.py           # includes due_date, etims fields
│   │   ├── organization.py      # includes document_template, etims config
│   │   └── audit_log.py
│   ├── schemas/
│   │   ├── common.py            # Response, PaginatedResponse, Meta
│   │   ├── auth.py
│   │   ├── client.py            # includes portal_token
│   │   ├── quotation.py         # includes is_expired computed field
│   │   ├── invoice.py           # includes is_overdue computed field
│   │   └── organization.py
│   ├── routers/
│   │   ├── auth.py              # register, login, refresh, logout, OAuth, DPA
│   │   ├── organization.py
│   │   ├── clients.py
│   │   ├── quotations.py
│   │   ├── invoices.py          # includes etims-submit, remind with link
│   │   ├── mpesa.py             # Safaricom callback
│   │   ├── pay.py               # Public payment portal (no auth)
│   │   ├── portal.py            # Client portal + public quotation (no auth)
│   │   ├── paystack.py          # Card payment initialize + webhook
│   │   ├── dashboard.py
│   │   └── reports.py
│   ├── services/
│   │   ├── mpesa_service.py     # STK Push logic
│   │   ├── etims_service.py     # KRA eTIMS submission
│   │   ├── email_service.py     # SendGrid email
│   │   ├── audit_service.py     # Audit log writes
│   │   └── scheduler.py         # APScheduler jobs
│   └── utils/
│       ├── id_generator.py      # QT-YYYY-XXX / INV-YYYY-XXX sequential IDs
│       └── rate_limit.py        # SlowAPI limiter instance
├── alembic/
│   └── versions/
│       ├── 82a654d56a8f_initial.py
│       ├── c3d9e4259a99_add_organizations_multitenancy_due_date.py
│       ├── 375c6461dd68_add_logo_and_template_to_organizations.py
│       ├── da817823e711_add_etims_fields.py
│       ├── f7c8d9e0a1b2_add_token_version_to_users.py
│       ├── a2b3c4d5e6f7_dpa_and_feature_additions.py
│       └── b1c2d3e4f5a6_add_portal_token_to_clients.py  ← latest
├── tests/
│   ├── conftest.py              # NullPool, asyncio.run schema setup, fixtures
│   ├── test_auth.py
│   ├── test_clients.py
│   ├── test_quotations.py
│   └── test_invoices.py
├── .env
├── .env.example
├── requirements.txt
├── pytest.ini                   # asyncio_mode = auto
└── .github/workflows/test.yml   # CI/CD
```

### Frontend
```
kastra-frontend/
├── src/
│   ├── api/
│   │   ├── axios.js             # Authenticated Axios instance (JWT)
│   │   ├── auth.js              # register, login, refresh, DPA exports
│   │   ├── clients.js
│   │   ├── quotations.js
│   │   ├── invoices.js          # includes etims, reminder
│   │   ├── organization.js
│   │   ├── pay.js               # Public payment portal API (unauthenticated)
│   │   └── portal.js            # Client portal + Paystack API (unauthenticated)
│   ├── components/
│   │   ├── layout/
│   │   │   └── AppLayout.jsx
│   │   ├── ui/
│   │   │   ├── Modal.jsx
│   │   │   ├── ConfirmDialog.jsx
│   │   │   ├── Spinner.jsx
│   │   │   └── PDFPreviewModal.jsx
│   │   └── documents/
│   │       ├── InvoiceDocument.jsx
│   │       ├── QuotationDocument.jsx
│   │       └── templates/
│   │           ├── ClassicTemplate.jsx
│   │           ├── ExecutiveTemplate.jsx
│   │           └── VividTemplate.jsx
│   ├── context/
│   │   └── AuthContext.jsx
│   ├── pages/
│   │   ├── auth/
│   │   │   ├── Login.jsx
│   │   │   ├── Register.jsx     # consent checkbox, DPA links
│   │   │   ├── ForgotPassword.jsx
│   │   │   ├── ResetPassword.jsx
│   │   │   └── AuthCallback.jsx
│   │   ├── clients/
│   │   │   ├── ClientList.jsx
│   │   │   └── ClientDetail.jsx # portal link card
│   │   ├── quotations/
│   │   │   ├── QuotationList.jsx
│   │   │   ├── QuotationForm.jsx  # expires_at field
│   │   │   └── QuotationDetail.jsx  # copy link + WhatsApp with portal link
│   │   ├── invoices/
│   │   │   ├── InvoiceList.jsx  # overdue badge, filter tabs
│   │   │   └── InvoiceDetail.jsx  # copy link + WhatsApp + M-Pesa + eTIMS
│   │   ├── pay/
│   │   │   └── PublicPayment.jsx  # M-Pesa + Paystack card
│   │   ├── portal/
│   │   │   ├── ClientPortal.jsx   # /portal/c/:token — full client dashboard
│   │   │   ├── PublicQuotation.jsx  # /portal/q/:quotationId — accept/decline
│   │   │   └── PaystackVerify.jsx   # /portal/paystack/verify — payment result
│   │   ├── legal/
│   │   │   ├── PrivacyPolicy.jsx
│   │   │   └── TermsOfService.jsx
│   │   ├── Dashboard.jsx
│   │   ├── Reports.jsx
│   │   └── Settings.jsx         # template auto-save, eTIMS config
│   ├── utils/
│   │   └── formatters.js        # ksh, date, phone, statusBadgeClass
│   └── index.css                # Tailwind + custom badge/card/input classes
├── public/
│   ├── manifest.json            # PWA manifest
│   ├── sw.js                    # Service worker (offline cache)
│   ├── offline.html             # Branded offline fallback
│   └── icons/
│       ├── icon-192.png
│       └── icon-512.png
├── index.html                   # PWA meta tags, manifest link
├── .env
└── .env.example
```

---

## 12. ENVIRONMENT VARIABLES

### Backend (`.env`)
```
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/kastra

# JWT
SECRET_KEY=<random 256-bit key>
REFRESH_SECRET_KEY=<separate random key>
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30

# Google OAuth
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...

# App
FRONTEND_URL=https://kastra.co.ke
BACKEND_URL=https://api.kastra.co.ke
ENVIRONMENT=production  # development | production

# M-Pesa
MPESA_CONSUMER_KEY=...
MPESA_CONSUMER_SECRET=...
MPESA_SHORTCODE=174379
MPESA_PASSKEY=...
MPESA_CALLBACK_URL=https://api.kastra.co.ke/api/mpesa/callback
MPESA_ENV=sandbox  # sandbox | production

# Paystack
PAYSTACK_SECRET_KEY=sk_live_...
PAYSTACK_PUBLIC_KEY=pk_live_...

# Email
SENDGRID_API_KEY=...
MAIL_FROM=noreply@kastra.co.ke

# Sentry (optional)
SENTRY_DSN=
```

### Frontend (`.env`)
```
VITE_API_URL=https://api.kastra.co.ke
VITE_SENTRY_DSN=
```

---

## 13. HOSTING & INFRASTRUCTURE

### Current Deployment (Free Tier)
| Service | Provider | Plan | Cost |
|---|---|---|---|
| Backend | Render | Free | $0 |
| Frontend | Vercel | Free | $0 |
| Database | Supabase | Free | $0 |
| **Total** | | | **$0/month** |

**Limitations:**
- Backend sleeps after 15min inactivity (30-60s wake-up time)
- Database limited to 500MB storage
- No automated backups

---

### Recommended Upgrade Path

#### **Phase 1: First 5 Paying Customers (KSh 15,000/month revenue)**
**Action: Upgrade Backend + Switch to Render PostgreSQL**

| Service | Provider | Plan | Cost | Why |
|---|---|---|---|---|
| Backend | Render | Starter | $7 | No sleep time, always-on |
| Database | Render PostgreSQL | Starter | $7 | 10GB storage, daily backups |
| Frontend | Vercel | Free | $0 | Still plenty of bandwidth |
| **Total** | | | **$14/month** | |

**Benefits:**
- ✅ Instant response (no 30s wake-up)
- ✅ Daily backups (7-day retention)
- ✅ 10GB storage (supports ~10,000 invoices)
- ✅ Everything on one platform (Render)
- ✅ Lower latency (backend + DB in same data center)
- ✅ Free bandwidth between services

**Migration Steps:**
1. Create Render PostgreSQL Starter database
2. Backup Supabase: `pg_dump [supabase_url] > backup.sql`
3. Restore to Render: `psql [render_url] < backup.sql`
4. Update `DATABASE_URL` in backend to Render Internal URL
5. Test thoroughly for 1 week
6. Cancel Supabase

**Savings vs Supabase Pro:** $18/month (Render $14 vs Supabase $25 + Render $7)

---

#### **Phase 2: 10-30 Customers (KSh 30-90k/month revenue)**
**Action: Stay on current setup**

| Service | Provider | Plan | Cost |
|---|---|---|---|
| Backend | Render | Starter | $7 |
| Database | Render PostgreSQL | Starter | $7 |
| Frontend | Vercel | Free | $0 |
| Cloudinary | Free | $0 |
| **Total** | | | **$14/month** |

**No upgrade needed** — Render Starter handles 50+ concurrent users easily.

---

#### **Phase 3: 30-50 Customers (KSh 90-150k/month revenue)**
**Action: Upgrade Backend to Standard**

| Service | Provider | Plan | Cost | Why |
|---|---|---|---|---|
| Backend | Render | Standard | $25 | 2GB RAM, faster response |
| Database | Render PostgreSQL | Starter | $7 | Still enough storage |
| Frontend | Vercel | Free | $0 | |
| Cloudinary | Free | $0 | |
| **Total** | | | **$32/month** | |

**Upgrade when:**
- Backend is slow during peak hours
- Memory errors in logs
- Response times > 2 seconds

---

#### **Phase 4: 50-100 Customers (KSh 150-300k/month revenue)**
**Action: Upgrade Database to Standard**

| Service | Provider | Plan | Cost | Why |
|---|---|---|---|---|
| Backend | Render | Standard | $25 | |
| Database | Render PostgreSQL | Standard | $20 | 100GB storage, 30-day backups |
| Frontend | Vercel | Free | $0 | |
| Cloudinary | Free | $0 | |
| **Total** | | | **$45/month** | |

**Upgrade when:**
- Database size > 8GB
- Slow queries
- Need longer backup retention

---

#### **Phase 5: 100+ Customers (KSh 300k+/month revenue)**
**Action: Upgrade Cloudinary (if needed)**

| Service | Provider | Plan | Cost | Why |
|---|---|---|---|---|
| Backend | Render | Standard | $25 | |
| Database | Render PostgreSQL | Standard | $20 | |
| Frontend | Vercel | Free | $0 | |
| Cloudinary | Plus | $89 | 225GB storage for photos |
| **Total** | | | **$134/month** | |

**Upgrade when:**
- Cloudinary storage > 20GB
- "Quota exceeded" errors
- 50+ organizations uploading photos

---

### Cost vs Revenue Analysis

| Customers | Revenue (KSh 3k/customer) | Hosting Cost | Profit | Margin |
|---|---|---|---|---|
| 0-5 | KSh 0-15k | $0 (free tier) | KSh 0-15k | 100% |
| 5-10 | KSh 15-30k | $14 (~KSh 1,820) | KSh 13-28k | 88-94% |
| 10-30 | KSh 30-90k | $14 (~KSh 1,820) | KSh 28-88k | 94-98% |
| 30-50 | KSh 90-150k | $32 (~KSh 4,160) | KSh 86-146k | 95-97% |
| 50-100 | KSh 150-300k | $45 (~KSh 5,850) | KSh 144-294k | 96-98% |
| 100+ | KSh 300k+ | $134 (~KSh 17,420) | KSh 283k+ | 94%+ |

**Break-even: 2 customers at KSh 3,000/month covers $14 hosting**

---

### Warning Signs to Upgrade

#### Backend (Render)
- ⚠️ Customers complain about slow first load
- ⚠️ M-Pesa callbacks fail (Safaricom timeout)
- ⚠️ Memory errors in logs
- ⚠️ Response times > 2 seconds during peak hours

#### Database (Render PostgreSQL)
- ⚠️ Storage > 8GB (check dashboard)
- ⚠️ "Database full" errors
- ⚠️ Slow queries (> 1 second)
- ⚠️ 50+ active organizations

#### Cloudinary
- ⚠️ Storage > 20GB (check dashboard)
- ⚠️ "Quota exceeded" errors
- ⚠️ Photos not uploading

---

### Migration: Supabase → Render PostgreSQL

**Why migrate:**
- Save $18/month (Render $7 vs Supabase $25)
- Better performance (same data center as backend)
- Simpler management (one platform)
- Daily backups included

**When to migrate:**
- As soon as you have 5 paying customers
- Before Supabase free tier runs out (500MB)

**How to migrate:**

```bash
# Step 1: Create Render PostgreSQL database (Starter plan)
# Via Render dashboard: New + → PostgreSQL → Starter ($7)

# Step 2: Backup Supabase data
pg_dump "postgresql://postgres:[password]@db.[project].supabase.co:5432/postgres" > kastra_backup.sql

# Step 3: Restore to Render (use External URL for this step)
psql "postgresql://user:pass@dpg-xxx.oregon-postgres.render.com/kastra_db" < kastra_backup.sql

# Step 4: Update backend environment variable
# In Render backend service, change:
# DATABASE_URL=postgresql://user:pass@dpg-xxx-a/kastra_db  (Internal URL)

# Step 5: Restart backend service

# Step 6: Test thoroughly
# - Log in
# - Create quotation
# - Create invoice
# - Check all data is present

# Step 7: Monitor for 1 week, then cancel Supabase
```

**Rollback plan:**
- Keep Supabase running for 1 week as backup
- If issues, revert `DATABASE_URL` to Supabase
- Have backup SQL file ready

---

### Deployment Checklist
- [ ] Set all environment variables on Render dashboard
- [ ] Set `ENVIRONMENT=production` (enables HSTS, Safaricom IP whitelist)
- [ ] Run `alembic upgrade head` after first deploy
- [ ] Register M-Pesa callback URL with Safaricom: `https://api.kastra.co.ke/api/mpesa/callback`
- [ ] Register Paystack webhook URL: `https://api.kastra.co.ke/api/paystack/webhook`
- [ ] Set Paystack callback URL in dashboard: `https://kastra.co.ke/portal/paystack/verify`
- [ ] Add real M-Pesa production keys (switch `MPESA_ENV=production`)
- [ ] Add real Paystack live keys
- [ ] Configure custom domain + SSL on Render
- [ ] Verify eTIMS credentials work (Settings → Test KRA Connection)

---

## 14. KNOWN LIMITATIONS & FUTURE IMPROVEMENTS

| Area | Current State | Possible Improvement |
|---|---|---|
| PDF generation | Browser print-to-PDF (user must choose "Save as PDF") | Server-side PDF via WeasyPrint for true download button |
| WhatsApp PDF sending | Text + link only (WhatsApp links can't attach files) | WhatsApp Business API (Meta Cloud) for file attachments |
| Multi-currency | KES only | USD/EUR for international clients |
| Recurring invoices | Manual creation only | Scheduled auto-generation |
| SMS notifications | Not implemented | Africa's Talking API |
| Multi-user roles | Admin + Manager only | Viewer (read-only), Accountant (reports only) |
| Mobile app | PWA (installable) | Native React Native app |
| Accounting export | CSV only | QuickBooks / Xero / Sage format |
| Bank reconciliation | Manual | Integration with bank statement APIs |
| Multi-branch/location | Single org | Branch-level reporting |

---

## 15. TEST SUITE

**77 tests, all passing.** Key decisions:

| Decision | Why |
|---|---|
| `NullPool` for asyncpg in tests | Prevents cross-loop connection attachment across pytest function-scoped event loops |
| `asyncio.run()` at conftest import time | Drops schema without async fixture ownership issues |
| `limiter.enabled = False` | Bypasses SlowAPI rate limits that would 429 after ~10 registrations |
| `db.expire(obj)` before re-fetch | Clears SQLAlchemy identity map stale cache after flush |
| Flush ordering in `convert_to_invoice` | SQLAlchemy processes UPDATEs before INSERTs; must flush invoice INSERT before setting `qt.invoice_id` FK |
| `DROP SCHEMA public CASCADE` in conftest | Resolves circular FK between `quotations.invoice_id` and `invoices.quotation_id` that `drop_all()` can't handle |
| `assert resp.status_code in (401, 403)` | FastAPI OAuth2 returns 403 (not 401) when no credentials are provided |

---

---

## 16. BUSINESS MODEL & PRICING (KENYAN MARKET)

### Architecture: Multi-Tenant SaaS
Kastra is already built for multi-tenancy. Every record is scoped to an `organization_id`, so a single deployment can serve hundreds of independent businesses — each completely isolated from one another. No additional code changes are needed to run this as a hosted SaaS product.

### Infrastructure Cost at Scale
| Customers | Monthly Revenue | Hosting Cost (Render) | Margin |
|---|---|---|---|
| 1–3 | KSh 4,500–9,000 | ~KSh 1,820 (~$14) | ~KSh 2,700–7,200 |
| 10 | KSh 30,000 | ~KSh 3,600 (upgraded tier) | ~KSh 26,400 |
| 50+ | KSh 150,000+ | ~KSh 10,000 | KSh 140,000+ |

### Recommended SaaS Pricing (KES/month)

| Plan | Price | Seats | Invoices/month | Notes |
|---|---|---|---|---|
| **Starter** | **KSh 1,500** | 1 user | Up to 100 | Freelancers, sole traders |
| **Business** | **KSh 3,000** | Up to 3 users | Unlimited | Small teams, agencies |
| **Premium** | **KSh 5,500** | Unlimited users | Unlimited | Growing SMEs, full eTIMS |

**Annual pricing:** 10 months charged, 2 months free (pay KSh 15,000 / 30,000 / 55,000 per year).

**Why this range works for Kenya:**
- KSh 1,500/month ≈ a tank of petrol — in reach of any freelancer billing over KSh 30,000/month.
- A business processing KSh 500,000/month in invoices will barely notice KSh 3,000/month.
- KRA eTIMS compliance alone (legally required for VAT-registered businesses) justifies the cost — alternatives charge more for less.
- M-Pesa STK Push is a differentiator: most global tools don't support it at all.
- Hosting break-even: **2 Starter customers covers your entire Render bill.**

### Competitive Landscape
| Tool | Price | M-Pesa | KRA eTIMS | Kenya-first |
|---|---|---|---|---|
| **Kastra** | KSh 1,500–5,500/mo | ✅ | ✅ | ✅ |
| QuickBooks Simple Start | ~KSh 2,600/mo (USD) | ❌ | ❌ | ❌ |
| Zoho Invoice (free tier) | Free / $9 USD | ❌ | ❌ | ❌ |
| Wave Accounting | Free | ❌ | ❌ | ❌ |
| Local billing tools | Varies | Partial | Partial | Partial |

### If Selling the App Outright (One-Time License)
For a single business wanting the full codebase deployed and managed for them:

| Option | Price Range | What's included |
|---|---|---|
| **Code only** (self-hosted) | KSh 150,000–250,000 | Codebase + deployment guide |
| **Deployed + 3 months support** | KSh 300,000–450,000 | Live deployment, .env configured, 3 months fixes |
| **White-label (another dev/agency)** | KSh 400,000–650,000 | Codebase + right to resell under own brand |

These are fair prices given the complexity (M-Pesa, eTIMS, Paystack, PWA, DPA compliance, 77 tests) — a comparable custom build would cost KSh 500,000+ in developer hours.

### Recommended Launch Strategy
1. **Month 1–2:** Soft launch at Starter only (KSh 1,500/month). Get 5 paying users. Gather feedback.
2. **Month 3:** Introduce Business plan. Target SMEs through M-Pesa agent networks and local WhatsApp business groups.
3. **Month 6+:** Premium plan + annual billing. Partner with accounting firms for referrals.

---

*This masterplan reflects the app as built as of May 2026. All phases are complete.*
