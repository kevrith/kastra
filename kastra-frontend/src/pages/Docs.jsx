import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ChevronDown, ChevronUp, FileText, Receipt, Users, CreditCard,
  TrendingDown, BarChart2, Package, UserCog, HelpCircle,
  ArrowRight, BookOpen, Repeat, Truck, Wallet, ShoppingCart,
} from "lucide-react";

const sections = [
  {
    id: "getting-started",
    icon: BookOpen,
    title: "Getting Started",
    color: "text-green-600",
    bg: "bg-green-50",
    guides: [
      {
        title: "Create your account",
        steps: [
          "Go to kastra.app and click Get Started.",
          "Enter your name, email, and a password.",
          "Check your email for a verification link and click it.",
          "You'll be taken to your dashboard automatically.",
        ],
      },
      {
        title: "Set up your business profile",
        steps: [
          "Go to Settings from the sidebar.",
          "Under Organisation, enter your business name, phone, and address.",
          "Upload your business logo (shown on invoices and quotations).",
          "If you're KRA registered, enter your KRA PIN and enable eTIMS.",
          "Click Save Changes.",
        ],
      },
      {
        title: "Add your first client",
        steps: [
          "Click Clients in the sidebar.",
          "Click New Client.",
          "Enter the client's name, email, phone, and address.",
          "Click Save. The client is now available when creating invoices.",
        ],
      },
      {
        title: "Create your first invoice",
        steps: [
          "Click Invoices in the sidebar, then New Invoice.",
          "Select a client from the dropdown.",
          "Add line items: type the item name, quantity, and unit price.",
          "Set a due date and any notes.",
          "Click Save as Draft to save, or Save & Send to email/WhatsApp the client immediately.",
        ],
      },
    ],
  },
  {
    id: "invoices",
    icon: Receipt,
    title: "Invoices",
    color: "text-indigo-600",
    bg: "bg-indigo-50",
    guides: [
      {
        title: "Scan a receipt to pre-fill line items",
        steps: [
          "On the New Invoice page, click Scan Receipt in the top-right.",
          "Take a photo or upload an image of a receipt.",
          "Kastra reads the items automatically using AI-powered OCR.",
          "Review the detected items and click Use These Items to fill the invoice.",
        ],
      },
      {
        title: "Send an invoice to a client",
        steps: [
          "Open an invoice and click Send.",
          "Choose Email, WhatsApp, or both.",
          "The client receives a link to view and pay the invoice online.",
        ],
      },
      {
        title: "Share a payment link",
        steps: [
          "Open an invoice and click the Payment Link button.",
          "Copy the link and share it via WhatsApp, SMS, or email.",
          "The client opens the link and pays via M-Pesa or card — no login required.",
        ],
      },
      {
        title: "Record a manual payment",
        steps: [
          "Open an invoice and click Record Payment.",
          "Enter the amount paid, payment method, and date.",
          "The invoice status updates automatically (Partial or Paid).",
        ],
      },
      {
        title: "Convert a quotation to an invoice",
        steps: [
          "Go to Quotations and open the accepted quotation.",
          "Click Convert to Invoice.",
          "Review the details, adjust if needed, then save.",
          "A new invoice number is generated automatically.",
        ],
      },
    ],
  },
  {
    id: "quotations",
    icon: FileText,
    title: "Quotations",
    color: "text-blue-600",
    bg: "bg-blue-50",
    guides: [
      {
        title: "Create a quotation",
        steps: [
          "Click Quotations in the sidebar, then New Quotation.",
          "Select a client and add line items with quantities and prices.",
          "Set an expiry date and any notes.",
          "Click Save as Draft or Save & Send.",
        ],
      },
      {
        title: "Track quotations via Pipeline",
        steps: [
          "Click Pipeline in the sidebar.",
          "Quotations are grouped by stage: Draft, Sent, Accepted, Rejected.",
          "Drag a quotation card to move it between stages.",
          "Click a card to open and edit the quotation.",
        ],
      },
      {
        title: "Convert a quotation to an invoice",
        steps: [
          "Open an accepted quotation.",
          "Click Convert to Invoice.",
          "Confirm the details and save.",
          "The new invoice is numbered sequentially from your invoice counter.",
        ],
      },
    ],
  },
  {
    id: "payments",
    icon: CreditCard,
    title: "Payments (M-Pesa & Card)",
    color: "text-purple-600",
    bg: "bg-purple-50",
    guides: [
      {
        title: "Set up M-Pesa (Daraja / STK Push)",
        steps: [
          "Go to Settings → Payments.",
          "Enable M-Pesa and enter your Daraja API credentials: Consumer Key, Consumer Secret, Shortcode, and Passkey.",
          "Save. Clients can now pay via M-Pesa STK Push directly from their payment link.",
        ],
      },
      {
        title: "Set up Paystack (Card + M-Pesa via Paystack)",
        steps: [
          "Create a free account at paystack.com.",
          "Go to Settings → API Keys on Paystack and copy your Live Secret Key and Live Public Key.",
          "In Kastra, go to Settings → Payments, enable Paystack, and paste your keys.",
          "Save. Clients can now pay by Visa, Mastercard, or M-Pesa via Paystack.",
        ],
      },
      {
        title: "Send a payment link to a client",
        steps: [
          "Open an invoice and click Copy Payment Link.",
          "Share the link via WhatsApp, SMS, or email.",
          "The client opens the page and chooses their preferred payment method.",
          "You receive a notification and the invoice updates automatically when paid.",
        ],
      },
    ],
  },
  {
    id: "clients",
    icon: Users,
    title: "Clients",
    color: "text-cyan-600",
    bg: "bg-cyan-50",
    guides: [
      {
        title: "Add a client",
        steps: [
          "Go to Clients and click New Client.",
          "Fill in the name, email, phone, and address.",
          "Optionally add a KRA PIN if the client is a business.",
          "Click Save.",
        ],
      },
      {
        title: "Give a client portal access",
        steps: [
          "Open a client record and click Enable Portal.",
          "The client receives a unique link to view their invoices, quotations, and payments.",
          "They can download documents and make payments without logging into Kastra.",
        ],
      },
      {
        title: "Request a testimonial from a client",
        steps: [
          "Open a client record and click Request Review.",
          "Enter their WhatsApp number (and email if available).",
          "They receive a link to leave a review that appears on your account.",
        ],
      },
    ],
  },
  {
    id: "expenses",
    icon: TrendingDown,
    title: "Expenses",
    color: "text-rose-600",
    bg: "bg-rose-50",
    guides: [
      {
        title: "Record an expense",
        steps: [
          "Go to Expenses and click Add Expense.",
          "Enter the description, category, amount, and date.",
          "Optionally attach a receipt image.",
          "Click Save.",
        ],
      },
      {
        title: "Scan a receipt for an expense",
        steps: [
          "Click Add Expense, then Scan Receipt.",
          "Upload or photograph the receipt.",
          "Kastra extracts the amount and description automatically.",
          "Review and save.",
        ],
      },
    ],
  },
  {
    id: "products",
    icon: Package,
    title: "Products & Services",
    color: "text-amber-600",
    bg: "bg-amber-50",
    guides: [
      {
        title: "Add a product or service",
        steps: [
          "Go to Products and click Add Product.",
          "Enter the name, unit price, unit (e.g. hrs, pcs, kg), and tax rate.",
          "Click Save.",
        ],
      },
      {
        title: "Use a product on an invoice",
        steps: [
          "On the New Invoice page, start typing in a line item field.",
          "Select the product from the dropdown.",
          "The name and price fill in automatically.",
        ],
      },
    ],
  },
  {
    id: "recurring",
    icon: Repeat,
    title: "Recurring Invoices",
    color: "text-teal-600",
    bg: "bg-teal-50",
    guides: [
      {
        title: "Set up a recurring invoice",
        steps: [
          "Go to Recurring in the sidebar and click New Recurring Invoice.",
          "Choose the client, line items, and billing cycle (weekly, monthly, etc.).",
          "Set the start date and optionally an end date.",
          "Click Save. Kastra generates the invoice automatically on each cycle.",
        ],
      },
    ],
  },
  {
    id: "reports",
    icon: BarChart2,
    title: "Reports",
    color: "text-violet-600",
    bg: "bg-violet-50",
    guides: [
      {
        title: "View income and expense reports",
        steps: [
          "Click Reports in the sidebar.",
          "Select a date range to filter.",
          "View total income, expenses, and net profit.",
          "Drill into individual invoices or expense categories.",
        ],
      },
      {
        title: "Export a report",
        steps: [
          "Open a report and click Export PDF or Export CSV.",
          "The file downloads to your device.",
        ],
      },
    ],
  },
  {
    id: "team",
    icon: UserCog,
    title: "Team Management",
    color: "text-slate-600",
    bg: "bg-slate-50",
    guides: [
      {
        title: "Invite a team member",
        steps: [
          "Go to Team in the sidebar (admin only).",
          "Click Invite Member.",
          "Enter their email and select a role: Manager or Viewer.",
          "They receive an email invite with a link to join your workspace.",
        ],
      },
      {
        title: "Understanding roles",
        steps: [
          "Admin — full access including settings, team, and billing.",
          "Manager — can create/edit invoices, quotations, clients, and expenses.",
          "Viewer — read-only access to invoices, quotations, clients, and reports.",
          "Field Agent — limited mobile-focused access for field staff.",
        ],
      },
    ],
  },
  {
    id: "suppliers",
    icon: Truck,
    title: "Suppliers",
    color: "text-orange-600",
    bg: "bg-orange-50",
    guides: [
      {
        title: "Add a supplier",
        steps: [
          "Go to Suppliers and click Add Supplier.",
          "Enter the supplier name, contact, and product categories.",
          "Click Save.",
        ],
      },
      {
        title: "Create a supplier request (price comparison)",
        steps: [
          "Go to Suppliers → New Request.",
          "List the items you need and quantity.",
          "Send to multiple suppliers. They respond via their supplier portal link.",
          "Compare prices and select the best offer, then click Create Purchase Order on the winning quote.",
        ],
      },
    ],
  },
  {
    id: "purchasing",
    icon: ShoppingCart,
    title: "Purchasing (Orders, Deliveries & Bills)",
    color: "text-indigo-600",
    bg: "bg-indigo-50",
    guides: [
      {
        title: "Send a purchase order to a supplier",
        steps: [
          "Go to Purchasing → New Order, or create one straight from a supplier's price quote.",
          "Choose the supplier, add items, quantities and your expected prices, then save the draft.",
          "Click Send to supplier — they receive a private link (no login) to review the order.",
        ],
      },
      {
        title: "Supplier confirms, revises, and price-change flags",
        steps: [
          "The supplier confirms the quantity they can supply and their price per item.",
          "Their prices appear next to yours, with a red ↑ (more expensive) or green ↓ (cheaper) flag versus your order and the last price you paid them.",
          "Accept the prices, or Reject with a reason so the supplier can revise and resubmit. The negotiation history stays on the order.",
        ],
      },
      {
        title: "Receive goods and keep profit accurate",
        steps: [
          "When goods arrive, open the accepted order and click Receive goods (partial deliveries are supported).",
          "This updates each item's cost price so your profit and loss stays accurate when you sell.",
        ],
      },
      {
        title: "Bill and pay suppliers (Accounts Payable)",
        steps: [
          "After receiving, click Create bill — Kastra 3-way matches it against the order and the goods received.",
          "Track everything you owe under Purchasing → Bills, with due dates and aging.",
          "Record payments until the bill is fully paid. Goods for resale stay as payables (not expenses) to keep profit correct.",
        ],
      },
    ],
  },
  {
    id: "subscription",
    icon: Wallet,
    title: "Subscription & Billing",
    color: "text-green-700",
    bg: "bg-green-50",
    guides: [
      {
        title: "Upgrade your plan",
        steps: [
          "Go to Settings → Subscription.",
          "Click Upgrade Plan and choose Starter, Business, or Premium.",
          "Pay via M-Pesa or card through Paystack.",
          "Your plan activates immediately after payment.",
        ],
      },
      {
        title: "What happens when the subscription expires?",
        steps: [
          "You receive a reminder email 5 days before expiry.",
          "After expiry, there is a 3-day grace period where the app still works.",
          "After the grace period, access is limited to read-only until renewed.",
          "Go to Settings → Subscription to renew at any time.",
        ],
      },
    ],
  },
];

const faqs = [
  {
    q: "Can I use both M-Pesa and card payments?",
    a: "Yes. You can set up both independently. M-Pesa uses the Safaricom Daraja API (STK Push) and card payments go through Paystack. Paystack also supports M-Pesa on their hosted page, so if you only want one integration, Paystack alone covers both card and M-Pesa.",
  },
  {
    q: "What is KRA eTIMS and do I need it?",
    a: "KRA eTIMS is the Kenya Revenue Authority's Electronic Tax Invoice Management System. If your business is VAT-registered in Kenya, you are required by law to submit invoices through eTIMS. Enable it in Settings → Organisation by entering your KRA PIN.",
  },
  {
    q: "How are invoice numbers generated?",
    a: "Invoice numbers are auto-generated per organisation in the format PREFIX-INV-YEAR-001 (e.g. KAS-INV-2026-001). The counter increments with each new invoice, whether created directly or converted from a quotation. Numbers are never duplicated.",
  },
  {
    q: "Can I have multiple businesses on one account?",
    a: "Each Kastra account is tied to one organisation. If you run multiple businesses, each needs its own separate Kastra account with its own subscription.",
  },
  {
    q: "What happens to my data if I downgrade or cancel?",
    a: "Your data is never deleted when you downgrade. You will lose access to premium features but can still view all your historical invoices, clients, and reports. If you cancel entirely, your data is retained for 90 days before permanent deletion.",
  },
  {
    q: "Can my client pay without logging in?",
    a: "Yes. Payment links and the client portal do not require a login. Your client receives a unique link and can view their invoice and pay via M-Pesa or card directly from their browser.",
  },
  {
    q: "Is my data secure?",
    a: "Yes. All data is encrypted in transit (HTTPS) and at rest. Payments are processed by Paystack and Safaricom Daraja — Kastra never stores card numbers. Your credentials are hashed and never stored in plain text.",
  },
  {
    q: "Can I use Kastra on my phone?",
    a: "Yes. Kastra works on any browser on mobile. You can also install it as a PWA (Progressive Web App) from your browser — tap the Share icon on Safari or the install prompt on Chrome for an app-like experience.",
  },
  {
    q: "How do I get support?",
    a: "Email us at support@kastra.app or use the Help section inside your dashboard. We aim to respond within 24 hours on business days.",
  },
];

function GuideCard({ guide }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 text-left bg-white hover:bg-gray-50 transition-colors"
      >
        <span className="text-sm font-medium text-gray-800">{guide.title}</span>
        {open ? <ChevronUp size={16} className="text-gray-400 shrink-0" /> : <ChevronDown size={16} className="text-gray-400 shrink-0" />}
      </button>
      {open && (
        <div className="px-4 pb-4 bg-white border-t border-gray-100">
          <ol className="mt-3 space-y-2">
            {guide.steps.map((step, i) => (
              <li key={i} className="flex gap-3 text-sm text-gray-600">
                <span className="flex-shrink-0 w-5 h-5 rounded-full bg-green-100 text-green-700 text-xs font-bold flex items-center justify-center mt-0.5">{i + 1}</span>
                <span>{step}</span>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}

function FaqItem({ faq }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3.5 text-left bg-white hover:bg-gray-50 transition-colors"
      >
        <span className="text-sm font-medium text-gray-800">{faq.q}</span>
        {open ? <ChevronUp size={16} className="text-gray-400 shrink-0" /> : <ChevronDown size={16} className="text-gray-400 shrink-0" />}
      </button>
      {open && (
        <div className="px-4 pb-4 bg-white border-t border-gray-100">
          <p className="mt-3 text-sm text-gray-600 leading-relaxed">{faq.a}</p>
        </div>
      )}
    </div>
  );
}

export default function Docs() {
  const [activeSection, setActiveSection] = useState("getting-started");

  const current = sections.find(s => s.id === activeSection);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 min-w-0">
            <img src="/kastra1.png" alt="Kastra" className="h-7 w-7 object-contain shrink-0" />
            <span className="text-base font-bold text-green-600 tracking-tight">Kastra</span>
            <span className="text-gray-300 mx-1 hidden sm:inline">/</span>
            <span className="text-sm text-gray-500 font-medium hidden sm:inline">Docs</span>
          </Link>
          <div className="flex items-center gap-2 shrink-0">
            <Link to="/login" className="text-sm text-gray-600 hover:text-gray-900 font-medium px-2 py-1">Sign in</Link>
            <Link to="/register" className="text-sm bg-green-600 hover:bg-green-700 text-white font-semibold px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap">
              Get started
            </Link>
          </div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 py-6">
        <div className="mb-5">
          <h1 className="text-xl font-bold text-gray-900">Help & Documentation</h1>
          <p className="text-gray-500 mt-0.5 text-sm">Step-by-step guides for every feature in Kastra.</p>
        </div>

        {/* Mobile section selector — full width, above content */}
        <div className="md:hidden mb-4">
          <select
            className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-green-400"
            value={activeSection}
            onChange={e => setActiveSection(e.target.value)}
          >
            {sections.map(s => <option key={s.id} value={s.id}>{s.title}</option>)}
            <option value="faq">FAQ</option>
          </select>
        </div>

        <div className="md:flex md:gap-6">
          {/* Desktop sidebar nav */}
          <aside className="hidden md:block w-52 shrink-0">
            <nav className="space-y-0.5 sticky top-20">
              {sections.map(s => (
                <button
                  key={s.id}
                  onClick={() => setActiveSection(s.id)}
                  className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium text-left transition-colors ${
                    activeSection === s.id ? "bg-green-50 text-green-700" : "text-gray-600 hover:bg-gray-100"
                  }`}
                >
                  <s.icon size={15} />
                  {s.title}
                </button>
              ))}
              <button
                onClick={() => setActiveSection("faq")}
                className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium text-left transition-colors ${
                  activeSection === "faq" ? "bg-green-50 text-green-700" : "text-gray-600 hover:bg-gray-100"
                }`}
              >
                <HelpCircle size={15} />
                FAQ
              </button>
            </nav>
          </aside>

          {/* Content — full width on mobile, flex-1 on desktop */}
          <main className="w-full min-w-0">
            {activeSection === "faq" ? (
              <div>
                <div className="flex items-center gap-3 mb-5">
                  <div className="w-8 h-8 rounded-xl bg-gray-100 flex items-center justify-center shrink-0">
                    <HelpCircle size={17} className="text-gray-600" />
                  </div>
                  <h2 className="text-lg font-bold text-gray-900">Frequently Asked Questions</h2>
                </div>
                <div className="space-y-2">
                  {faqs.map((faq, i) => <FaqItem key={i} faq={faq} />)}
                </div>
              </div>
            ) : current ? (
              <div>
                <div className="flex items-center gap-3 mb-5">
                  <div className={`w-8 h-8 rounded-xl ${current.bg} flex items-center justify-center shrink-0`}>
                    <current.icon size={17} className={current.color} />
                  </div>
                  <h2 className="text-lg font-bold text-gray-900">{current.title}</h2>
                </div>
                <div className="space-y-2">
                  {current.guides.map((guide, i) => <GuideCard key={i} guide={guide} />)}
                </div>
              </div>
            ) : null}

            {/* CTA */}
            <div className="mt-8 bg-green-600 rounded-2xl p-5 text-white text-center">
              <p className="font-bold text-base">Ready to get started?</p>
              <p className="text-green-100 text-sm mt-1">Create your free Kastra account — no credit card required.</p>
              <Link
                to="/register"
                className="inline-flex items-center gap-2 mt-4 bg-white text-green-700 font-semibold px-5 py-2.5 rounded-xl hover:bg-green-50 transition-colors text-sm"
              >
                Start for free <ArrowRight size={15} />
              </Link>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
