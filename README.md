# Kastra — Business Operations Platform

A full-stack, multi-tenant SaaS platform built for Kenyan SMEs. Manage quotations, invoices, clients, payments, **team collaboration, and project tracking** — with KRA eTIMS compliance and M-Pesa built in from day one.

**Stack:** React 19 + Vite + FastAPI + PostgreSQL + Cloudinary  
**Payments:** M-Pesa STK Push + Paystack (Visa/Mastercard)  
**Compliance:** KRA eTIMS, Kenya DPA 2019  
**Status:** Feature-complete. Production-ready. 536 backend + 170 frontend tests passing.

---

## What It Does

### Core Features
- **Quotations** — Create, send, and get client approval via a shareable link. Clients can Accept or Decline without logging in.
- **Invoices** — Convert accepted quotations to invoices in one click. Clients pay via M-Pesa STK Push or Visa/Mastercard.
- **Client Portal** — Every client gets a permanent shareable link showing all their invoices, quotations, and payment options.
- **WhatsApp Sharing** — Send payment links and quotation links directly via WhatsApp from within the app.
- **KRA eTIMS** — Submit invoices to KRA and receive a Control Unit Invoice Number + QR code on every PDF.
- **PDF Documents** — Three branded templates (Classic, Executive, Vivid). Print-to-PDF via browser.
- **Reports & Dashboard** — Monthly income charts, client rankings, quotation conversion rates, CSV export.
- **PWA** — Installable on Android/iOS. Works offline with a branded fallback page.

### Finance & Compliance
- **Multi-Currency** — Invoice in USD, EUR, GBP and more with live exchange rates; totals still roll up in KES. Online payment stays KES-only.
- **Credit Notes** — KRA-compliant invoice corrections that apply to the balance and submit to eTIMS as refund receipts.
- **Delivery Notes** — Goods delivery documents from an invoice or quotation, with driver, vehicle and signature lines.
- **Statements & Aging** — Per-client running-balance statements and a current / 1-30 / 31-60 / 61-90 / 90+ aging report.
- **Bank & M-Pesa Reconciliation** — Upload a CSV, get suggested matches by invoice reference, amount, or client name.
- **Payroll** — Employees, payroll runs and payslips with Kenyan statutory calculations (PAYE, NSSF, SHIF, Housing Levy).

### Procurement (P2P)
- **Purchase Orders** — Raise POs against suppliers; they confirm or revise prices on a no-login portal.
- **Goods Receipt** — Record deliveries against a PO; product cost prices update from what you actually paid.
- **Supplier Bills & Payables** — Three-way match (PO / receipt / bill), plus a payables aging view.
- **Price History** — Flags when a supplier's price drifts from what you last paid.

### Security & Governance
- **Two-Factor Authentication** — TOTP via any authenticator app, with ten single-use recovery codes. Secrets are encrypted at rest.
- **Spend Approvals** — Per-org thresholds for purchase orders and invoices. Anything at or above the limit waits for a second approver, who can never be the person who raised it.
- **Audit Trail** — Who created, edited, deleted, paid, approved, signed in, or failed to sign in — with IP address, filterable and exportable.
- **Row-Level Security** — RLS enabled on every public table.
- **Encrypted Credentials** — Per-tenant payment keys encrypted at rest.

### Team & Project Management
- **Team Management** — Invite team members with role-based access (Admin, Manager, Field Agent, Viewer)
- **Project Pipeline** — Visual Kanban board to track projects from start to completion
- **Field Reporting** — Team members post progress updates and upload photos from mobile
- **Photo Storage** — Cloudinary integration for fast, scalable photo uploads
- **Team Dashboard** — See who's working on what, track activity, identify stalled projects
- **Multi-Tenant** — One deployment serves unlimited independent businesses, each fully isolated.

---

## SaaS-Ready Architecture

Every record is scoped to an `organization_id`. A single Render deployment (~$14/month) supports hundreds of tenants. Billing break-even: **2 customers at KSh 1,500/month covers hosting.**

---

## Monorepo Structure

```
kastra/
├── kastra-backend/    # FastAPI + PostgreSQL
├── kastra-frontend/   # React 18 + Vite + Tailwind
├── masterplan.md      # Full product specification (as-built)
├── RUNBOOK.md         # Backups, deploys, rollback, incident triage
└── start.sh           # Start both services locally
```

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL running locally

### 1. Clone and set up
```bash
git clone <repo-url>
cd kastra
```

### 2. Backend
```bash
cd kastra-backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # Fill in your values
alembic upgrade head           # Run migrations
uvicorn app.main:app --reload --port 8080
```

### 3. Frontend
```bash
cd kastra-frontend
npm install
cp .env.example .env           # Set VITE_API_URL
npm run dev                    # Runs on http://localhost:5200
```

### 4. Or start everything at once
```bash
./start.sh
```

---

## Running the tests

**Backend** — the suite drops and recreates the schema of its target database on
every run, so it must point at a throwaway `*_test` database. The helper script
derives one from your `.env` and refuses to run against anything else:

```bash
cd kastra-backend
./scripts/run-tests.sh                 # whole suite
./scripts/run-tests.sh tests/test_auth.py -v
```

Two suites pointed at one database corrupt each other, so the script also bails
out if another run is already connected.

**Frontend**

```bash
cd kastra-frontend
npm test                               # vitest
```

---

## Docs
- [Backend README](kastra-backend/README.md) — API, environment variables, running tests
- [Frontend README](kastra-frontend/README.md) — Pages, routes, environment variables
- [masterplan.md](masterplan.md) — Full product spec, data model, all features
- **[IMPLEMENTATION.md](IMPLEMENTATION.md)** — Team & project management technical details
- **[SETUP.md](SETUP.md)** — Quick setup guide for new features
- **[MIGRATION.md](MIGRATION.md)** — Migration guide for existing users
- **[RUNBOOK.md](RUNBOOK.md)** — Backups and restore, deploys and rollback, secret rotation, incident triage

---

## License
Private — Kastra Enterprises © 2026
