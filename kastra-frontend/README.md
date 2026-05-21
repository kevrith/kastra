# Kastra Frontend

React 18 + Vite + Tailwind CSS frontend for the Kastra business operations platform. PWA-first, mobile-optimised, works offline. Deployable as a Render Static Site or Vercel (free tier).

---

## Stack

| | |
|---|---|
| Framework | React 18 + Vite |
| Styling | Tailwind CSS 3 (custom design system) |
| Routing | React Router v6 |
| Charts | Recharts |
| Icons | Lucide React |
| HTTP | Axios (authenticated + public instances) |
| Auth | React Context + localStorage JWT |
| Error Tracking | @sentry/react (graceful, no-op if DSN not set) |
| PWA | manifest.json + service worker |

---

## Getting Started

```bash
cd kastra-frontend
npm install
cp .env.example .env
# Set VITE_API_URL to your backend URL
npm run dev         # http://localhost:5200
npm run build       # Production build → dist/
```

---

## Environment Variables

```env
VITE_API_URL=http://localhost:8080    # Backend base URL
VITE_SENTRY_DSN=                      # Optional — leave blank in development
```

---

## Pages & Routes

### Public (no login required)

| Route | Page | Description |
|---|---|---|
| `/login` | Login | Email/password or Google OAuth |
| `/register` | Register | Sign up with consent checkbox |
| `/forgot-password` | ForgotPassword | Request password reset email |
| `/reset-password` | ResetPassword | Set new password via email link |
| `/auth/callback` | AuthCallback | Google OAuth redirect handler |
| `/pay/:invoiceId` | PublicPayment | Client pays invoice — M-Pesa or Paystack card |
| `/portal/c/:token` | ClientPortal | Client dashboard — all invoices + quotations |
| `/portal/q/:quotationId` | PublicQuotation | Client views quotation, accepts or declines |
| `/portal/paystack/verify` | PaystackVerify | Payment result after Paystack redirect |
| `/privacy` | PrivacyPolicy | Kenya DPA 2019 compliant privacy policy |
| `/terms` | TermsOfService | Terms of service |

### Protected (requires login)

| Route | Page | Description |
|---|---|---|
| `/` | Dashboard | KPIs, charts, recent activity |
| `/clients` | ClientList | All clients, search, sort |
| `/clients/:id` | ClientDetail | Client profile, stats, portal link, recent docs |
| `/quotations` | QuotationList | All quotations, filter by status/client/date |
| `/quotations/new` | QuotationForm | Create quotation |
| `/quotations/:id` | QuotationDetail | View, share via WhatsApp, copy link, PDF, convert |
| `/quotations/:id/edit` | QuotationForm | Edit draft/pending quotation |
| `/invoices` | InvoiceList | All invoices — overdue badge, filter tabs |
| `/invoices/:id` | InvoiceDetail | View, WhatsApp share, M-Pesa, eTIMS, PDF |
| `/reports` | Reports | Income charts, client analysis, CSV export |
| `/settings` | Settings | Business profile, document template, eTIMS, password |

---

## WhatsApp Sharing

All share flows build `https://wa.me/{phone}?text=...` links:

| Where | What's shared |
|---|---|
| Invoice detail → WhatsApp | Invoice amount + `/pay/{id}` payment link |
| Invoice detail → Copy Link | `/pay/{id}` to clipboard |
| Quotation detail → WhatsApp | Quotation total + `/portal/q/{id}` link |
| Quotation detail → Copy Link | `/portal/q/{id}` to clipboard |
| Client detail → WhatsApp | Portal URL + `/portal/c/{token}` |
| Client detail → Copy Link | `/portal/c/{token}` to clipboard |

---

## Document Templates

Three PDF templates selectable in Settings → Document Template. Selection is auto-saved on click.

| Template | Style |
|---|---|
| Classic | Green accent bar, clean white layout |
| Executive | Dark navy header, amber strip, corporate |
| Vivid | Green gradient header with wave, bold |

PDF is generated via browser print dialog (Ctrl+P → Save as PDF). The `PDFPreviewModal` injects print-only CSS that hides all app chrome so only the document prints.

---

## API Layer

```
src/api/
├── axios.js       # Authenticated Axios instance — attaches JWT, handles 401 refresh
├── auth.js        # register, login, refresh, logout, DPA endpoints
├── clients.js
├── quotations.js
├── invoices.js    # includes etims, remind
├── organization.js
├── pay.js         # Public: getPublicInvoice, publicMpesaPay
└── portal.js      # Public: getClientPortal, getPublicQuotation, respondToQuotation, initializePaystack
```

---

## Project Structure

```
kastra-frontend/
├── src/
│   ├── api/                          # API functions
│   ├── components/
│   │   ├── layout/AppLayout.jsx      # Sidebar + top nav shell
│   │   ├── ui/
│   │   │   ├── Modal.jsx
│   │   │   ├── ConfirmDialog.jsx
│   │   │   ├── Spinner.jsx
│   │   │   └── PDFPreviewModal.jsx   # Print-to-PDF with print CSS injection
│   │   └── documents/
│   │       ├── InvoiceDocument.jsx
│   │       ├── QuotationDocument.jsx
│   │       └── templates/
│   │           ├── ClassicTemplate.jsx
│   │           ├── ExecutiveTemplate.jsx
│   │           └── VividTemplate.jsx
│   ├── context/AuthContext.jsx       # JWT storage, auto-refresh
│   ├── pages/
│   │   ├── auth/
│   │   ├── clients/
│   │   ├── quotations/
│   │   ├── invoices/
│   │   ├── pay/                      # Public payment portal
│   │   ├── portal/                   # Client portal, public quotation, Paystack verify
│   │   ├── legal/                    # Privacy policy, Terms of service
│   │   ├── Dashboard.jsx
│   │   ├── Reports.jsx
│   │   └── Settings.jsx
│   ├── utils/formatters.js           # ksh(), date(), phone(), statusBadgeClass()
│   └── index.css                     # Tailwind + .card, .btn-primary, .input, .badge-* etc.
├── public/
│   ├── manifest.json                 # PWA — installable on home screen
│   ├── sw.js                         # Service worker — offline cache
│   ├── offline.html                  # Branded offline fallback
│   └── icons/icon-192.png, icon-512.png
├── index.html                        # PWA meta tags, manifest link
├── .env
├── .env.example
└── vite.config.js
```

---

## Custom CSS Classes (Tailwind)

Defined in `src/index.css`:

| Class | Usage |
|---|---|
| `.card` | White rounded card with shadow |
| `.btn-primary` | Green filled button |
| `.btn-secondary` | Gray outlined button |
| `.btn-danger` | Red button |
| `.input` | Standard form input |
| `.label` | Form label |
| `.badge-paid` | Green badge |
| `.badge-unpaid` | Amber badge |
| `.badge-pending` | Amber badge |
| `.badge-accepted` | Green badge |
| `.badge-declined` | Red badge |
| `.badge-overdue` | Red badge |
| `.badge-expired` | Orange badge |

---

## Production Deployment (Render Static Sites)

1. Build command: `npm run build`
2. Publish directory: `dist`
3. Set environment variables:
   - `VITE_API_URL=https://api.kastra.co.ke`
   - `VITE_SENTRY_DSN=` (optional)
4. Add rewrite rule: `/* → /index.html` (required for React Router)
