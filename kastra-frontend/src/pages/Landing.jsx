import { Link } from "react-router-dom";
import {
  FileText, Receipt, CreditCard, Users, BarChart2, Shield,
  CheckCircle, Smartphone, Zap, Globe, ArrowRight, Star,
  TrendingUp, Clock, Lock, UserCog, FolderKanban, Camera, DollarSign, Truck, Sparkles, Wallet,
} from "lucide-react";

const features = [
  {
    icon: Receipt,
    title: "Smart Invoicing",
    desc: "Create professional invoices in seconds. Auto-numbering, VAT, WHT, discounts, and multi-item support built in.",
  },
  {
    icon: FileText,
    title: "Quotations & Proposals",
    desc: "Send branded quotations clients can approve online. Convert to invoice with one click.",
  },
  {
    icon: DollarSign,
    title: "Job Profitability Tracking",
    desc: "Attach expenses (materials, labour, lunch, transport) to any invoice. See instant profit or loss per job — green for profit, red for loss.",
  },
  {
    icon: Truck,
    title: "Supplier Price Comparison",
    desc: "Send price requests to multiple suppliers via a shareable link. They submit their prices online — you compare them side by side and pick the best deal.",
  },
  {
    icon: Smartphone,
    title: "M-Pesa Integration",
    desc: "Collect payments via M-Pesa STK Push directly from your invoice. Reconciled automatically.",
  },
  {
    icon: CreditCard,
    title: "Card Payments",
    desc: "Accept Visa and Mastercard payments via Paystack. Give clients every payment option.",
  },
  {
    icon: UserCog,
    title: "Team Management",
    desc: "Invite team members with role-based access. Admins, managers, field agents, and viewers — all in one platform.",
  },
  {
    icon: FolderKanban,
    title: "Project Pipeline",
    desc: "Visual Kanban board to track projects from start to completion. Drag & drop to update status.",
  },
  {
    icon: Camera,
    title: "Field Reporting",
    desc: "Team members post progress updates and upload photos from mobile. Real-time visibility for managers.",
  },
  {
    icon: Users,
    title: "Client Management",
    desc: "Manage all your clients, track their history, balances, and send payment reminders automatically.",
  },
  {
    icon: BarChart2,
    title: "Financial Reports",
    desc: "Revenue trends, top clients, expense tracking, and net profit at a glance. Make data-driven decisions.",
  },
  {
    icon: Shield,
    title: "eTIMS / KRA Compliant",
    desc: "Submit invoices directly to KRA's eTIMS portal. Stay compliant with Kenyan tax regulations.",
  },
  {
    icon: TrendingUp,
    title: "Recurring Invoices",
    desc: "Set up automatic recurring invoices for retainer clients. Never miss a billing cycle.",
  },
  {
    icon: Globe,
    title: "Multi-Currency Invoicing",
    desc: "Bill export, diaspora, and NGO clients in USD, EUR, GBP and more — with live exchange rates and automatic KES-equivalent reporting alongside your local invoices.",
  },
  {
    icon: Sparkles,
    title: "AI Smart Features",
    desc: "Auto-suggest invoice line items from past history, scan receipts to categorise expenses, get a 30-day cash flow forecast, generate quotation descriptions from bullet points, and score client payment risk — all powered by Claude AI.",
  },
  {
    icon: Wallet,
    title: "Payroll & Payslips",
    desc: "Keep employee records and run monthly payroll in a click — Kastra computes PAYE, NSSF, SHIF and the Affordable Housing Levy automatically, then generates payslips and a payroll register so you can pay your staff with confidence.",
  },
];

const stats = [
  { value: "60s", label: "To create & send an invoice" },
  { value: "16%", label: "VAT handled automatically" },
  { value: "M-Pesa", label: "Payments in one tap" },
  { value: "100%", label: "KRA eTIMS compliant" },
];

const testimonials = [
  {
    name: "Grace Wanjiku",
    role: "CEO, Wanjiku Consulting",
    text: "Kastra transformed how we invoice clients. What used to take hours now takes minutes. M-Pesa integration alone saved us so much chasing of payments.",
    stars: 5,
  },
  {
    name: "David Otieno",
    role: "Director, Otieno Supplies Ltd",
    text: "The eTIMS compliance feature is a game changer. We are always audit-ready and the dashboard gives us a clear picture of our finances every morning.",
    stars: 5,
  },
  {
    name: "Amina Hassan",
    role: "Founder, Amina Events",
    text: "I used to juggle spreadsheets and WhatsApp for quotations. Kastra made me look like a proper enterprise from day one.",
    stars: 5,
  },
];

const plans = [
  {
    id: "free",
    name: "Free",
    price: "KES 0",
    period: "forever",
    desc: "Perfect for freelancers just getting started.",
    features: ["20 invoices / month", "20 quotations / month", "1 team member", "5 OCR scans / month", "3 clients", "M-Pesa payments", "Classic template", "No AI features"],
    cta: "Get started free",
    highlight: false,
  },
  {
    id: "starter",
    name: "Starter",
    price: "KES 1,500",
    period: "/ month",
    desc: "For small businesses ready to grow.",
    features: ["200 invoices / month", "150 quotations / month", "3 team members", "10 OCR scans / month", "20 clients", "M-Pesa + Paystack", "Email invoices", "Client portal", "Products catalog", "Supplier price requests", "Job profitability tracking", "3-month reports", "15 AI calls / month"],
    cta: "Start with Starter",
    highlight: false,
  },
  {
    id: "business",
    name: "Business",
    price: "KES 3,000",
    period: "/ month",
    desc: "For teams that need collaboration.",
    features: ["400 invoices / month", "250 quotations / month", "6 team members", "35 OCR scans / month", "100 clients", "Team management", "Project pipeline", "Field reporting", "Photo uploads", "SMS notifications", "Recurring invoices", "eTIMS / KRA compliance", "Supplier price comparison", "Job profitability tracking", "Audit logs", "50 AI calls / month"],
    cta: "Go Business",
    highlight: true,
  },
  {
    id: "premium",
    name: "Premium",
    price: "KES 5,500",
    period: "/ month",
    desc: "Unlimited power for high-volume operations.",
    features: ["Unlimited invoices", "Unlimited quotations", "15 team members", "100+ OCR scans / month", "Unlimited clients", "Unlimited projects", "White-label branding", "Priority support", "All 3 templates", "Full history reports", "Supplier price comparison", "Job profitability tracking", "Unlimited AI calls"],
    cta: "Go Premium",
    highlight: false,
  },
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-white text-gray-900 font-sans">

      {/* ── Nav ───────────────────────────────────────────── */}
      <nav className="sticky top-0 z-50 bg-white/90 backdrop-blur border-b border-gray-100">
        <div className="max-w-6xl mx-auto px-5 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <img src="/kastra.png" alt="Kastra" className="h-8 w-8 object-contain" />
            <span className="text-xl font-bold text-green-600 tracking-tight">Kastra</span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm font-medium text-gray-600">
            <a href="#features" className="hover:text-green-600 transition-colors">Features</a>
            <a href="#pricing" className="hover:text-green-600 transition-colors">Pricing</a>
            <a href="#testimonials" className="hover:text-green-600 transition-colors">Testimonials</a>
          </div>
          <div className="flex items-center gap-3">
            <Link to="/login" className="text-sm font-medium text-gray-700 hover:text-green-600 transition-colors">
              Sign in
            </Link>
            <Link to="/register" className="text-sm font-semibold bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors">
              Get started free
            </Link>
          </div>
        </div>
      </nav>

      {/* ── Hero ──────────────────────────────────────────── */}
      <section className="relative overflow-hidden bg-gradient-to-br from-green-50 via-white to-emerald-50 pt-20 pb-28 px-5">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(22,163,74,0.12),transparent)]" />
        <div className="relative max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 bg-green-100 text-green-700 text-xs font-semibold px-4 py-1.5 rounded-full mb-6 border border-green-200">
            <Zap size={12} />
            Built for Kenyan businesses
          </div>
          <h1 className="text-5xl md:text-6xl font-extrabold text-gray-900 leading-tight tracking-tight mb-6">
            Invoice, quote, track &amp;{" "}
            <span className="text-green-600">get paid faster</span>
          </h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto mb-10 leading-relaxed">
            The all-in-one business management platform for Kenyan SMEs. Professional invoicing,
            team collaboration, project tracking, M-Pesa &amp; card payments, KRA eTIMS compliance — in one place.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link
              to="/register"
              className="inline-flex items-center justify-center gap-2 bg-green-600 text-white font-semibold px-8 py-4 rounded-xl text-lg hover:bg-green-700 transition-all shadow-lg shadow-green-200 hover:shadow-xl hover:shadow-green-200 hover:-translate-y-0.5"
            >
              Start for free <ArrowRight size={18} />
            </Link>
            <Link
              to="/login"
              className="inline-flex items-center justify-center gap-2 bg-white text-gray-700 font-semibold px-8 py-4 rounded-xl text-lg border border-gray-200 hover:border-green-300 hover:text-green-700 transition-all"
            >
              Sign in
            </Link>
          </div>
          <p className="text-sm text-gray-400 mt-5">No credit card required · 14-day free trial on paid plans · Free forever plan available</p>
        </div>

        {/* Stats bar */}
        <div className="relative max-w-3xl mx-auto mt-20 grid grid-cols-2 md:grid-cols-4 gap-px bg-gray-200 rounded-2xl overflow-hidden shadow-sm">
          {stats.map((s) => (
            <div key={s.label} className="bg-white px-6 py-5 text-center">
              <div className="text-2xl font-bold text-green-600">{s.value}</div>
              <div className="text-xs text-gray-500 mt-1">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Features ──────────────────────────────────────── */}
      <section id="features" className="py-24 px-5 bg-white">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-sm font-semibold text-green-600 uppercase tracking-widest mb-3">Everything you need</p>
            <h2 className="text-4xl font-extrabold text-gray-900 mb-4">Run your business, not your paperwork</h2>
            <p className="text-lg text-gray-500 max-w-xl mx-auto">
              From the first quotation to the final payment, Kastra handles every step of your billing workflow.
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((f) => (
              <div key={f.title} className="group p-6 rounded-2xl border border-gray-100 hover:border-green-200 hover:shadow-md transition-all bg-white">
                <div className="w-11 h-11 rounded-xl bg-green-50 flex items-center justify-center mb-4 group-hover:bg-green-100 transition-colors">
                  <f.icon size={20} className="text-green-600" />
                </div>
                <h3 className="font-bold text-gray-900 mb-2">{f.title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ──────────────────────────────────── */}
      <section className="py-24 px-5 bg-gray-50">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-sm font-semibold text-green-600 uppercase tracking-widest mb-3">How it works</p>
            <h2 className="text-4xl font-extrabold text-gray-900">From quote to payment in 3 steps</h2>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {[
              { step: "01", icon: FileText, title: "Create a quotation", desc: "Build a professional quotation in under a minute. Add your logo, items, and send directly to the client." },
              { step: "02", icon: Receipt, title: "Convert to invoice", desc: "Client approves? Convert to invoice with one click. Auto-fills all the details, calculates VAT automatically." },
              { step: "03", icon: CreditCard, title: "Get paid", desc: "Client pays via M-Pesa, card, or bank. Payment is recorded and reconciled automatically in your dashboard." },
            ].map((item) => (
              <div key={item.step} className="relative text-center">
                <div className="w-14 h-14 rounded-2xl bg-green-600 flex items-center justify-center mx-auto mb-4 shadow-lg shadow-green-200">
                  <item.icon size={24} className="text-white" />
                </div>
                <div className="absolute -top-2 left-1/2 -translate-x-1/2 ml-5 text-xs font-bold text-green-300">{item.step}</div>
                <h3 className="font-bold text-gray-900 mb-2 text-lg">{item.title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Compliance strip ──────────────────────────────── */}
      <section className="py-14 px-5 bg-green-700 text-white">
        <div className="max-w-5xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-4">
            <Shield size={40} className="text-green-300 shrink-0" />
            <div>
              <h3 className="text-xl font-bold">KRA eTIMS &amp; DPA 2019 Compliant</h3>
              <p className="text-green-200 text-sm mt-1">Kastra is built to meet Kenya's tax and data protection requirements out of the box.</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-4 shrink-0">
            {["eTIMS Ready", "VAT 16%", "WHT Support", "DPA Compliant"].map((tag) => (
              <span key={tag} className="flex items-center gap-1.5 bg-green-600 text-white text-sm font-medium px-4 py-1.5 rounded-full border border-green-500">
                <CheckCircle size={13} /> {tag}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ── Testimonials ──────────────────────────────────── */}
      <section id="testimonials" className="py-24 px-5 bg-white">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-sm font-semibold text-green-600 uppercase tracking-widest mb-3">Testimonials</p>
            <h2 className="text-4xl font-extrabold text-gray-900">Trusted by Kenyan businesses</h2>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {testimonials.map((t) => (
              <div key={t.name} className="p-6 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow bg-white">
                <div className="flex gap-0.5 mb-4">
                  {Array.from({ length: t.stars }).map((_, i) => (
                    <Star key={i} size={15} className="fill-amber-400 text-amber-400" />
                  ))}
                </div>
                <p className="text-gray-700 text-sm leading-relaxed mb-5">"{t.text}"</p>
                <div>
                  <p className="font-semibold text-gray-900 text-sm">{t.name}</p>
                  <p className="text-xs text-gray-400">{t.role}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Pricing ───────────────────────────────────────── */}
      <section id="pricing" className="py-24 px-5 bg-gray-50">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-sm font-semibold text-green-600 uppercase tracking-widest mb-3">Pricing</p>
            <h2 className="text-4xl font-extrabold text-gray-900 mb-4">Simple, transparent pricing</h2>
            <p className="text-lg text-gray-500">Start free forever — or try any paid plan free for 14 days. No credit card required.</p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5 items-start">
            {plans.map((plan) => (
              <div
                key={plan.id}
                className={`rounded-2xl p-6 border ${plan.highlight
                  ? "bg-green-600 border-green-600 text-white shadow-2xl shadow-green-200 scale-105"
                  : "bg-white border-gray-200"
                }`}
              >
                {plan.highlight && (
                  <div className="text-xs font-bold bg-white text-green-600 px-3 py-1 rounded-full inline-block mb-4">
                    Most popular
                  </div>
                )}
                <h3 className={`text-lg font-bold mb-1 ${plan.highlight ? "text-white" : "text-gray-900"}`}>{plan.name}</h3>
                <p className={`text-xs mb-4 ${plan.highlight ? "text-green-200" : "text-gray-500"}`}>{plan.desc}</p>
                <div className="mb-5">
                  <span className={`text-3xl font-extrabold ${plan.highlight ? "text-white" : "text-gray-900"}`}>{plan.price}</span>
                  <span className={`text-xs ml-1 ${plan.highlight ? "text-green-200" : "text-gray-400"}`}>{plan.period}</span>
                </div>
                <ul className="space-y-2 mb-6">
                  {plan.features.map((f) => (
                    <li key={f} className={`flex items-start gap-2 text-xs ${plan.highlight ? "text-green-100" : "text-gray-600"}`}>
                      <CheckCircle size={13} className={`mt-0.5 flex-shrink-0 ${plan.highlight ? "text-green-300" : "text-green-500"}`} />
                      {f}
                    </li>
                  ))}
                </ul>
                <Link
                  to={`/register?plan=${plan.id}`}
                  className={`block text-center text-sm font-semibold py-2.5 rounded-xl transition-all ${plan.highlight
                    ? "bg-white text-green-700 hover:bg-green-50"
                    : "bg-green-600 text-white hover:bg-green-700"
                  }`}
                >
                  {plan.cta}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ───────────────────────────────────────────── */}
      <section className="py-24 px-5 bg-gradient-to-br from-green-600 to-emerald-700 text-white text-center">
        <div className="max-w-2xl mx-auto">
          <h2 className="text-4xl font-extrabold mb-4">Ready to take control of your finances?</h2>
          <p className="text-green-200 text-lg mb-10">Join hundreds of Kenyan businesses already using Kastra to invoice faster and get paid on time.</p>
          <Link
            to="/register"
            className="inline-flex items-center gap-2 bg-white text-green-700 font-bold px-10 py-4 rounded-xl text-lg hover:bg-green-50 transition-all shadow-xl hover:-translate-y-0.5"
          >
            Create your free account <ArrowRight size={18} />
          </Link>
        </div>
      </section>

      {/* ── Footer ────────────────────────────────────────── */}
      <footer className="bg-gray-900 text-gray-400 py-14 px-5">
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-4 gap-8 mb-10">
            <div>
              <div className="flex items-center gap-2 mb-3">
                <img src="/kastra.png" alt="Kastra" className="h-7 w-7 object-contain" />
                <span className="text-white font-bold text-lg">Kastra</span>
              </div>
              <p className="text-sm leading-relaxed">Business operations platform built for Kenyan SMEs.</p>
            </div>
            <div>
              <h4 className="text-white font-semibold text-sm mb-3">Product</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#features" className="hover:text-white transition-colors">Features</a></li>
                <li><a href="#pricing" className="hover:text-white transition-colors">Pricing</a></li>
                <li><Link to="/register" className="hover:text-white transition-colors">Get started</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white font-semibold text-sm mb-3">Legal</h4>
              <ul className="space-y-2 text-sm">
                <li><Link to="/privacy" className="hover:text-white transition-colors">Privacy Policy</Link></li>
                <li><Link to="/terms" className="hover:text-white transition-colors">Terms of Service</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white font-semibold text-sm mb-3">Contact</h4>
              <ul className="space-y-2 text-sm">
                <li className="flex items-center gap-2"><Globe size={13} /> kastra.co.ke</li>
                <li className="flex items-center gap-2"><Lock size={13} /> DPA 2019 Compliant</li>
                <li className="flex items-center gap-2"><Clock size={13} /> Nairobi, Kenya</li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-800 pt-6 text-center text-xs">
            © {new Date().getFullYear()} Kastra. All rights reserved. Built for Kenyan businesses.
          </div>
        </div>
      </footer>
    </div>
  );
}
