import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ChevronDown, ChevronUp, FileText, Receipt, Users, CreditCard,
  TrendingDown, BarChart2, Settings, Package, UserCog, HelpCircle,
  BookOpen, Repeat, Truck, Wallet, Mail, MessageCircle,
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
        title: "Set up your business profile",
        steps: [
          "Go to Settings from the sidebar.",
          "Under Organisation, enter your business name, phone, and address.",
          "Upload your business logo — it appears on all invoices and quotations.",
          "If you're KRA registered, enter your KRA PIN and enable eTIMS.",
          "Click Save Changes.",
        ],
      },
      {
        title: "Add your first client",
        steps: [
          "Click Clients in the sidebar, then New Client.",
          "Enter the client's name, email, phone, and address.",
          "Click Save. The client is now available when creating invoices.",
        ],
      },
      {
        title: "Create your first invoice",
        steps: [
          "Click Invoices in the sidebar, then New Invoice.",
          "Select a client from the dropdown.",
          "Add line items — type the item name, quantity, and unit price.",
          "Set a due date and click Save as Draft or Save & Send.",
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
          "Upload or photograph a receipt.",
          "Kastra reads the items automatically using AI-powered OCR.",
          "Review and click Use These Items.",
        ],
      },
      {
        title: "Send an invoice to a client",
        steps: [
          "Open an invoice and click Send.",
          "Choose Email, WhatsApp, or both.",
          "The client receives a link to view and pay online.",
        ],
      },
      {
        title: "Share a payment link",
        steps: [
          "Open an invoice and click Copy Payment Link.",
          "Share via WhatsApp, SMS, or email.",
          "The client pays via M-Pesa or card — no login required.",
        ],
      },
      {
        title: "Record a manual payment",
        steps: [
          "Open an invoice and click Record Payment.",
          "Enter the amount, payment method, and date.",
          "The invoice updates to Partial or Paid automatically.",
        ],
      },
      {
        title: "Convert a quotation to an invoice",
        steps: [
          "Open an accepted quotation and click Convert to Invoice.",
          "Review the details, then save.",
          "A new invoice number is generated from the same counter.",
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
          "Select a client and add line items.",
          "Set an expiry date and click Save as Draft or Save & Send.",
        ],
      },
      {
        title: "Track quotations in Pipeline",
        steps: [
          "Click Pipeline in the sidebar.",
          "Cards show your quotations by stage: Draft, Sent, Accepted, Rejected.",
          "Drag a card to move it between stages.",
        ],
      },
    ],
  },
  {
    id: "payments",
    icon: CreditCard,
    title: "Payments",
    color: "text-purple-600",
    bg: "bg-purple-50",
    guides: [
      {
        title: "Set up M-Pesa (Daraja STK Push)",
        steps: [
          "Go to Settings → Payments.",
          "Enable M-Pesa and enter your Daraja API credentials: Consumer Key, Consumer Secret, Shortcode, and Passkey.",
          "Save. Clients can now pay via M-Pesa from their payment link.",
        ],
      },
      {
        title: "Set up Paystack (Card + M-Pesa via Paystack)",
        steps: [
          "Sign up at paystack.com and get your Live Secret Key and Live Public Key.",
          "In Kastra, go to Settings → Payments, enable Paystack, and paste your keys.",
          "Save. Clients can pay by Visa, Mastercard, or M-Pesa via Paystack.",
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
        title: "Enable the client portal",
        steps: [
          "Open a client record and click Enable Portal.",
          "The client gets a unique link to view their invoices and make payments.",
          "No login required on their end.",
        ],
      },
      {
        title: "Request a testimonial",
        steps: [
          "Open a client record and click Request Review.",
          "Enter their WhatsApp number (email is optional).",
          "They receive a link to leave a testimonial.",
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
          "Optionally attach a receipt and click Save.",
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
          "Enter the name, unit price, unit type (hrs, pcs, kg, etc.), and tax rate.",
          "Click Save. Products appear in the line item dropdown on invoices and quotations.",
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
          "Go to Recurring and click New Recurring Invoice.",
          "Choose the client, line items, and billing cycle.",
          "Set the start date and save. Invoices are generated automatically each cycle.",
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
        title: "View and export reports",
        steps: [
          "Click Reports in the sidebar.",
          "Select a date range to filter income, expenses, and net profit.",
          "Click Export PDF or Export CSV to download.",
        ],
      },
    ],
  },
  {
    id: "team",
    icon: UserCog,
    title: "Team",
    color: "text-slate-600",
    bg: "bg-slate-50",
    guides: [
      {
        title: "Invite a team member",
        steps: [
          "Go to Team in the sidebar (admin only).",
          "Click Invite Member, enter their email, and choose a role.",
          "They receive an invite email to join your workspace.",
        ],
      },
      {
        title: "Role permissions",
        steps: [
          "Admin — full access including settings, team, and billing.",
          "Manager — create/edit invoices, quotations, clients, and expenses.",
          "Viewer — read-only access to documents and reports.",
          "Field Agent — limited mobile access for field staff.",
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
        title: "Create a supplier price request",
        steps: [
          "Go to Suppliers → New Request.",
          "List the items and quantities you need.",
          "Send to multiple suppliers. They respond via their unique portal link.",
          "Compare prices and select the best offer.",
        ],
      },
    ],
  },
  {
    id: "subscription",
    icon: Wallet,
    title: "Subscription",
    color: "text-green-700",
    bg: "bg-green-50",
    guides: [
      {
        title: "Upgrade your plan",
        steps: [
          "Go to Settings → Subscription.",
          "Click Upgrade Plan and choose Starter, Business, or Premium.",
          "Pay via M-Pesa or card through Paystack.",
          "Your plan activates immediately.",
        ],
      },
      {
        title: "What happens when subscription expires?",
        steps: [
          "You receive a reminder email 5 days before expiry.",
          "After expiry, there is a 3-day grace period where the app still works.",
          "After the grace period, access is read-only until you renew.",
          "Go to Settings → Subscription to renew at any time.",
        ],
      },
    ],
  },
];

const faqs = [
  {
    q: "Can I use both M-Pesa and card payments?",
    a: "Yes. Set up M-Pesa via Daraja API and Paystack for card payments independently. Paystack also supports M-Pesa on their hosted page, so Paystack alone covers both.",
  },
  {
    q: "What is KRA eTIMS?",
    a: "KRA eTIMS is the Kenya Revenue Authority's Electronic Tax Invoice Management System. If your business is VAT-registered, enable it in Settings → Organisation and enter your KRA PIN.",
  },
  {
    q: "How are invoice numbers generated?",
    a: "Auto-generated per organisation in the format PREFIX-INV-YEAR-001. The counter is shared between direct invoices and quotation conversions so numbers are never duplicated.",
  },
  {
    q: "Can my client pay without logging in?",
    a: "Yes. Payment links and the client portal work without a login. Your client uses a unique link from their browser.",
  },
  {
    q: "What happens to my data if I downgrade?",
    a: "Your data is never deleted when you downgrade. You lose access to premium features but can still view all historical invoices, clients, and reports.",
  },
  {
    q: "Can I use Kastra on my phone?",
    a: "Yes. Kastra works on any mobile browser. You can also install it as a PWA — tap the install/share prompt in Chrome or Safari.",
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

export default function Help() {
  const [activeSection, setActiveSection] = useState("getting-started");

  const current = sections.find(s => s.id === activeSection);

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">
      <div className="mb-6">
        <h1 className="text-xl font-bold text-gray-900">Help & Guides</h1>
        <p className="text-gray-500 text-sm mt-0.5">Step-by-step guides for every feature.</p>
      </div>

      <div className="flex gap-5">
        {/* Sidebar nav — desktop */}
        <aside className="hidden md:block w-48 shrink-0">
          <nav className="space-y-0.5 sticky top-6">
            {sections.map(s => (
              <button
                key={s.id}
                onClick={() => setActiveSection(s.id)}
                className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium text-left transition-colors ${
                  activeSection === s.id ? "bg-green-50 text-green-700" : "text-gray-600 hover:bg-gray-100"
                }`}
              >
                <s.icon size={14} />
                {s.title}
              </button>
            ))}
            <button
              onClick={() => setActiveSection("faq")}
              className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium text-left transition-colors ${
                activeSection === "faq" ? "bg-green-50 text-green-700" : "text-gray-600 hover:bg-gray-100"
              }`}
            >
              <HelpCircle size={14} />
              FAQ
            </button>
          </nav>
        </aside>

        {/* Mobile dropdown */}
        <div className="md:hidden w-full mb-4">
          <select
            className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-green-400"
            value={activeSection}
            onChange={e => setActiveSection(e.target.value)}
          >
            {sections.map(s => <option key={s.id} value={s.id}>{s.title}</option>)}
            <option value="faq">FAQ</option>
          </select>
        </div>

        {/* Content */}
        <main className="flex-1 min-w-0">
          {activeSection === "faq" ? (
            <div>
              <div className="flex items-center gap-3 mb-5">
                <div className="w-8 h-8 rounded-xl bg-gray-100 flex items-center justify-center">
                  <HelpCircle size={16} className="text-gray-600" />
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
                <div className={`w-8 h-8 rounded-xl ${current.bg} flex items-center justify-center`}>
                  <current.icon size={16} className={current.color} />
                </div>
                <h2 className="text-lg font-bold text-gray-900">{current.title}</h2>
              </div>
              <div className="space-y-2">
                {current.guides.map((guide, i) => <GuideCard key={i} guide={guide} />)}
              </div>
            </div>
          ) : null}

          {/* Contact support */}
          <div className="mt-8 border border-gray-200 rounded-2xl p-5 bg-white">
            <p className="text-sm font-semibold text-gray-800 mb-1">Still need help?</p>
            <p className="text-xs text-gray-500 mb-4">Our support team responds within 24 hours on business days.</p>
            <div className="flex flex-wrap gap-3">
              <a
                href="mailto:support@kastra.app"
                className="inline-flex items-center gap-2 text-sm font-medium text-green-700 bg-green-50 hover:bg-green-100 px-4 py-2 rounded-xl transition-colors"
              >
                <Mail size={14} /> Email support
              </a>
              <Link
                to="/docs"
                className="inline-flex items-center gap-2 text-sm font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 px-4 py-2 rounded-xl transition-colors"
              >
                <BookOpen size={14} /> Full documentation
              </Link>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
