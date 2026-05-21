# Kastra Backend

FastAPI + PostgreSQL backend for the Kastra business operations platform. Multi-tenant by design — all data is scoped to `organization_id`. One deployment, unlimited tenants.

---

## Stack

| | |
|---|---|
| Framework | FastAPI (Python 3.11+) |
| Database | PostgreSQL 15+ via SQLAlchemy async + asyncpg |
| Migrations | Alembic |
| Auth | JWT (access + refresh tokens) + Google OAuth |
| Payments | M-Pesa Daraja STK Push + Paystack card |
| Compliance | KRA eTIMS, Kenya DPA 2019 |
| Scheduling | APScheduler (nightly overdue + expiry jobs) |
| Rate Limiting | SlowAPI |
| Error Tracking | Sentry (graceful, no-op if DSN not set) |
| Tests | pytest-asyncio, 77 tests |
| CI | GitHub Actions |

---

## Getting Started

```bash
cd kastra-backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env — minimum required: DATABASE_URL, SECRET_KEY, REFRESH_SECRET_KEY
alembic upgrade head
uvicorn app.main:app --reload --port 8080
```

API docs available at: `http://localhost:8080/docs`

---

## Environment Variables

Copy `.env.example` to `.env` and fill in values:

```env
# Required
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/kastra
SECRET_KEY=<random 256-bit string>
REFRESH_SECRET_KEY=<separate random string>
FRONTEND_URL=http://localhost:5200

# M-Pesa (get from Safaricom Daraja portal)
MPESA_CONSUMER_KEY=
MPESA_CONSUMER_SECRET=
MPESA_SHORTCODE=174379
MPESA_PASSKEY=
MPESA_CALLBACK_URL=https://api.kastra.co.ke/api/mpesa/callback
MPESA_ENV=sandbox   # change to: production

# Paystack (get from paystack.com/dashboard)
PAYSTACK_SECRET_KEY=sk_test_placeholder
PAYSTACK_PUBLIC_KEY=pk_test_placeholder

# Google OAuth (optional)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# Email — SendGrid (optional)
SENDGRID_API_KEY=
MAIL_FROM=noreply@kastra.co.ke

# Sentry (optional — leave blank in development)
SENTRY_DSN=

# Set to "production" to enable: HSTS, Safaricom IP whitelist, Paystack HMAC enforcement
ENVIRONMENT=development
```

---

## Running Tests

```bash
# Create test database first
createdb kastra_test

# Run all tests
pytest

# Run with output
pytest -v -s
```

**Test database URL** defaults to `postgresql+asyncpg://kastra_user:REMOVED_SEE_GITHUB_SECRETS@localhost:5432/kastra_test`. Override via `TEST_DATABASE_URL` env var.

The test suite wipes and recreates the public schema on each run. 77 tests covering auth, clients, quotations, and invoices.

---

## Database Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "description"

# Check current version
alembic current

# Migration history
alembic history
```

### Migration chain (latest first)

| Revision | Description |
|---|---|
| `b1c2d3e4f5a6` | Add `portal_token` to clients (latest) |
| `a2b3c4d5e6f7` | DPA: `consented_at`, `expires_at`, `audit_logs` |
| `f7c8d9e0a1b2` | Add `token_version` to users |
| `da817823e711` | Add eTIMS fields to organizations |
| `375c6461dd68` | Add `logo_url`, `document_template` to organizations |
| `c3d9e4259a99` | Add organizations, multitenancy, `due_date` |
| `82a654d56a8f` | Initial schema |

---

## API Overview

All authenticated endpoints require: `Authorization: Bearer <access_token>`

### Public endpoints (no auth)
```
POST  /api/auth/register
POST  /api/auth/login
POST  /api/auth/refresh
POST  /api/auth/forgot-password
POST  /api/auth/reset-password
GET   /api/auth/google
GET   /api/auth/google/callback

GET   /api/pay/{invoice_id}              # Public invoice view
POST  /api/pay/{invoice_id}/mpesa        # Public M-Pesa payment

GET   /api/portal/c/{token}             # Client portal (all docs)
GET   /api/portal/q/{quotation_id}      # Public quotation view
POST  /api/portal/q/{quotation_id}/respond  # Accept / Decline

POST  /api/paystack/initialize           # Initialize card payment
POST  /api/paystack/webhook             # Paystack payment confirmation
POST  /api/mpesa/callback               # Safaricom callback (IP-whitelisted)
```

### Authenticated endpoints
```
GET   /api/auth/me
DELETE /api/auth/me                      # Right to erasure (DPA)
GET   /api/auth/me/export               # Data export (DPA)
POST  /api/auth/change-password
POST  /api/auth/logout

GET/PUT /api/organization

GET/POST  /api/clients
GET/PUT/DELETE /api/clients/{id}
GET   /api/clients/{id}/history

GET/POST  /api/quotations
GET/PUT/DELETE /api/quotations/{id}
PATCH /api/quotations/{id}/status
POST  /api/quotations/{id}/convert

GET   /api/invoices
GET   /api/invoices/{id}
PATCH /api/invoices/{id}/mark-paid
POST  /api/invoices/{id}/mpesa-pay
POST  /api/invoices/{id}/etims-submit
POST  /api/invoices/{id}/remind

GET   /api/dashboard/stats
GET   /api/dashboard/charts
GET   /api/reports/income
GET   /api/reports/clients
GET   /api/reports/export/csv
```

---

## Project Structure

```
kastra-backend/
├── app/
│   ├── main.py              # App entry, CORS, middleware, router registration
│   ├── config.py            # Settings (pydantic-settings, reads .env)
│   ├── database.py          # Async engine + session factory
│   ├── dependencies.py      # get_db, get_current_user
│   ├── models/
│   │   ├── user.py
│   │   ├── client.py        # portal_token field
│   │   ├── quotation.py     # expires_at field
│   │   ├── invoice.py       # due_date, etims fields
│   │   ├── organization.py  # document_template, etims config
│   │   └── audit_log.py
│   ├── schemas/             # Pydantic v2 request/response models
│   ├── routers/
│   │   ├── auth.py
│   │   ├── organization.py
│   │   ├── clients.py
│   │   ├── quotations.py
│   │   ├── invoices.py
│   │   ├── mpesa.py         # Safaricom callback
│   │   ├── pay.py           # Public payment portal
│   │   ├── portal.py        # Client portal + public quotation
│   │   ├── paystack.py      # Card payment + webhook
│   │   ├── dashboard.py
│   │   └── reports.py
│   ├── services/
│   │   ├── mpesa_service.py   # STK Push
│   │   ├── etims_service.py   # KRA eTIMS submission
│   │   ├── email_service.py   # SendGrid
│   │   ├── audit_service.py   # Audit log writes
│   │   └── scheduler.py       # Nightly APScheduler jobs
│   └── utils/
│       ├── id_generator.py    # QT-YYYY-XXX / INV-YYYY-XXX
│       └── rate_limit.py      # SlowAPI instance
├── alembic/
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_clients.py
│   ├── test_quotations.py
│   └── test_invoices.py
├── .env
├── .env.example
├── requirements.txt
├── pytest.ini
└── .github/workflows/test.yml
```

---

## Production Deployment (Render)

1. Create a **Web Service** pointing to this directory
2. Build command: `pip install -r requirements.txt`
3. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add all environment variables from `.env.example`
5. Set `ENVIRONMENT=production`
6. Run `alembic upgrade head` once after first deploy (use Render Shell)
7. Register webhook URLs:
   - M-Pesa callback: `https://api.kastra.co.ke/api/mpesa/callback`
   - Paystack webhook: `https://api.kastra.co.ke/api/paystack/webhook`
   - Paystack callback URL (in dashboard): `https://kastra.co.ke/portal/paystack/verify`
