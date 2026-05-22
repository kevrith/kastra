# Kastra — Business Operations Platform

A full-stack, multi-tenant SaaS platform built for Kenyan SMEs. Manage quotations, invoices, clients, payments, **team collaboration, and project tracking** — with KRA eTIMS compliance and M-Pesa built in from day one.

**Stack:** React 18 + FastAPI + PostgreSQL + Cloudinary  
**Payments:** M-Pesa STK Push + Paystack (Visa/Mastercard)  
**Compliance:** KRA eTIMS, Kenya DPA 2019  
**Status:** Feature-complete. Production-ready. 77 tests passing.

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

### NEW: Team & Project Management
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

## Docs
- [Backend README](kastra-backend/README.md) — API, environment variables, running tests
- [Frontend README](kastra-frontend/README.md) — Pages, routes, environment variables
- [masterplan.md](masterplan.md) — Full product spec, data model, all features
- **[IMPLEMENTATION.md](IMPLEMENTATION.md)** — Team & project management technical details
- **[SETUP.md](SETUP.md)** — Quick setup guide for new features
- **[MIGRATION.md](MIGRATION.md)** — Migration guide for existing users

---

## License
Private — Kastra Enterprises © 2026
