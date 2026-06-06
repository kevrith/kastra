import { useEffect, useRef, useState } from "react";
import { useAuth } from "../context/AuthContext";
import api from "../api/axios";
import { getOrganization, updateOrganization } from "../api/organization";
import { testEtimsConnection } from "../api/invoices";
import { getMyPlan, upgradePlan } from "../api/subscriptions";
import { Building2, User, Lock, Upload, X, Palette, ShieldCheck, Eye, EyeOff, Loader, Package, ArrowRight, CreditCard, Smartphone, CheckCircle, Zap, Phone } from "lucide-react";
import ConfirmDialog from "../components/ui/ConfirmDialog";
import { Link, useSearchParams } from "react-router-dom";

const TEMPLATES = [
  {
    id: "classic",
    name: "Classic",
    description: "Clean green accent, timeless layout",
    preview: (
      <svg viewBox="0 0 160 110" xmlns="http://www.w3.org/2000/svg" style={{ width: "100%", height: "100%" }}>
        <rect width="160" height="110" fill="#fff" />
        {/* Logo box */}
        <rect x="10" y="10" width="22" height="22" rx="3" fill="#f0fdf4" stroke="#16a34a" strokeWidth="1.5" />
        <text x="21" y="25" textAnchor="middle" fontSize="8" fontWeight="700" fill="#16a34a">B</text>
        {/* Business name */}
        <rect x="36" y="12" width="48" height="5" rx="1" fill="#16a34a" />
        <rect x="36" y="20" width="32" height="3" rx="1" fill="#d1fae5" />
        <rect x="36" y="26" width="40" height="3" rx="1" fill="#d1fae5" />
        {/* Doc number */}
        <rect x="110" y="10" width="40" height="7" rx="1" fill="#111827" />
        <rect x="118" y="20" width="24" height="3" rx="1" fill="#9ca3af" />
        <rect x="114" y="26" width="28" height="5" rx="2" fill="#dcfce7" />
        {/* Green divider */}
        <rect x="10" y="38" width="140" height="2.5" rx="1" fill="#16a34a" />
        {/* Bill to */}
        <rect x="10" y="46" width="20" height="2.5" rx="1" fill="#9ca3af" />
        <rect x="10" y="52" width="45" height="4" rx="1" fill="#111827" />
        <rect x="10" y="59" width="55" height="3" rx="1" fill="#d1d5db" />
        {/* Table header */}
        <rect x="10" y="68" width="140" height="8" rx="1" fill="#f9fafb" />
        <rect x="14" y="71" width="35" height="2" rx="1" fill="#9ca3af" />
        <rect x="130" y="71" width="16" height="2" rx="1" fill="#9ca3af" />
        {/* Table rows */}
        <rect x="10" y="78" width="140" height="7" fill="#fff" />
        <rect x="14" y="80" width="50" height="2" rx="1" fill="#374151" />
        <rect x="130" y="80" width="16" height="2" rx="1" fill="#374151" />
        <rect x="10" y="86" width="140" height="7" fill="#f9fafb" />
        <rect x="14" y="88" width="40" height="2" rx="1" fill="#374151" />
        <rect x="130" y="88" width="16" height="2" rx="1" fill="#374151" />
        {/* Total */}
        <rect x="100" y="97" width="50" height="8" rx="2" fill="#f0fdf4" />
        <rect x="104" y="100" width="22" height="2" rx="1" fill="#16a34a" />
        <rect x="130" y="100" width="16" height="2" rx="1" fill="#16a34a" />
      </svg>
    ),
  },
  {
    id: "executive",
    name: "Executive",
    description: "Dark header, corporate & refined",
    preview: (
      <svg viewBox="0 0 160 110" xmlns="http://www.w3.org/2000/svg" style={{ width: "100%", height: "100%" }}>
        <rect width="160" height="110" fill="#fff" />
        {/* Dark header */}
        <rect width="160" height="38" fill="#1e293b" />
        {/* Logo */}
        <rect x="10" y="9" width="20" height="20" rx="3" fill="rgba(255,255,255,0.15)" stroke="rgba(255,255,255,0.3)" strokeWidth="1" />
        <text x="20" y="22" textAnchor="middle" fontSize="8" fontWeight="700" fill="#fff">B</text>
        {/* Business name white */}
        <rect x="34" y="11" width="44" height="5" rx="1" fill="#f8fafc" />
        <rect x="34" y="19" width="30" height="3" rx="1" fill="#475569" />
        <rect x="34" y="25" width="38" height="2.5" rx="1" fill="#334155" />
        {/* Doc number right */}
        <rect x="108" y="9" width="42" height="8" rx="1" fill="#f8fafc" />
        <rect x="116" y="20" width="26" height="3" rx="1" fill="#475569" />
        <rect x="116" y="26" width="20" height="3" rx="1" fill="#334155" />
        {/* Amber strip */}
        <rect x="0" y="38" width="160" height="3" fill="#f59e0b" />
        {/* Bill To + Status */}
        <rect x="10" y="48" width="18" height="2.5" rx="1" fill="#94a3b8" />
        <rect x="10" y="54" width="40" height="4" rx="1" fill="#0f172a" />
        <rect x="10" y="61" width="50" height="2.5" rx="1" fill="#94a3b8" />
        <rect x="120" y="48" width="16" height="2.5" rx="1" fill="#94a3b8" />
        <rect x="115" y="55" width="36" height="7" rx="2" fill="#fef3c7" />
        <text x="133" y="61" textAnchor="middle" fontSize="5" fontWeight="700" fill="#92400e">UNPAID</text>
        {/* Table */}
        <rect x="10" y="72" width="140" height="7" fill="#fff" />
        <rect x="10" y="71" width="140" height="1.5" fill="#0f172a" />
        <rect x="14" y="74" width="35" height="2" rx="1" fill="#6b7280" />
        <rect x="130" y="74" width="16" height="2" rx="1" fill="#1e293b" />
        <rect x="10" y="80" width="140" height="6" fill="#fff" />
        <rect x="10" y="80" width="140" height="0.5" fill="#f1f5f9" />
        <rect x="14" y="82" width="45" height="2" rx="1" fill="#6b7280" />
        <rect x="130" y="82" width="16" height="2" rx="1" fill="#1e293b" />
        {/* Total box */}
        <rect x="100" y="90" width="50" height="16" rx="2" stroke="#e2e8f0" strokeWidth="1" fill="#fff" />
        <rect x="100" y="98" width="50" height="8" rx="0 0 2 2" fill="#1e293b" />
        <rect x="104" y="100" width="18" height="2" rx="1" fill="#fff" />
        <rect x="130" y="100" width="16" height="2" rx="1" fill="#f59e0b" />
      </svg>
    ),
  },
  {
    id: "vivid",
    name: "Vivid",
    description: "Bold green gradient, eye-catching",
    preview: (
      <svg viewBox="0 0 160 110" xmlns="http://www.w3.org/2000/svg" style={{ width: "100%", height: "100%" }}>
        <defs>
          <linearGradient id="vg" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#15803d" />
            <stop offset="100%" stopColor="#166534" />
          </linearGradient>
        </defs>
        <rect width="160" height="110" fill="#fff" />
        {/* Gradient header */}
        <rect width="160" height="40" fill="url(#vg)" />
        {/* Wave */}
        <path d="M0,32 C40,46 120,18 160,32 L160,40 L0,40 Z" fill="#fff" />
        {/* Logo */}
        <rect x="10" y="8" width="22" height="22" rx="4" fill="#fff" />
        <text x="21" y="22" textAnchor="middle" fontSize="8" fontWeight="800" fill="#15803d">B</text>
        {/* Business name */}
        <rect x="36" y="10" width="46" height="5" rx="1" fill="rgba(255,255,255,0.9)" />
        <rect x="36" y="18" width="32" height="3" rx="1" fill="rgba(255,255,255,0.55)" />
        <rect x="36" y="24" width="38" height="2.5" rx="1" fill="rgba(255,255,255,0.4)" />
        {/* Doc number */}
        <rect x="108" y="8" width="44" height="9" rx="1" fill="rgba(255,255,255,0.9)" />
        <rect x="116" y="20" width="28" height="3" rx="1" fill="rgba(255,255,255,0.55)" />
        {/* Bill To card */}
        <rect x="10" y="48" width="100" height="24" rx="4" fill="#f0fdf4" />
        <rect x="15" y="52" width="18" height="2" rx="1" fill="#15803d" />
        <rect x="15" y="57" width="42" height="4" rx="1" fill="#111827" />
        <rect x="15" y="64" width="50" height="2.5" rx="1" fill="#6b7280" />
        {/* Status badge */}
        <rect x="120" y="54" width="32" height="10" rx="5" fill="#fee2e2" />
        <text x="136" y="61" textAnchor="middle" fontSize="4.5" fontWeight="700" fill="#991b1b">UNPAID</text>
        {/* Green table header */}
        <rect x="10" y="76" width="140" height="8" fill="#15803d" />
        <rect x="14" y="79" width="30" height="2" rx="1" fill="rgba(255,255,255,0.8)" />
        <rect x="130" y="79" width="16" height="2" rx="1" fill="rgba(255,255,255,0.8)" />
        {/* Table rows */}
        <rect x="10" y="85" width="140" height="7" fill="#fff" />
        <rect x="14" y="87" width="46" height="2" rx="1" fill="#374151" />
        <rect x="130" y="87" width="16" height="2" rx="1" fill="#374151" />
        {/* Total */}
        <rect x="100" y="95" width="50" height="11" rx="2" fill="#15803d" />
        <rect x="104" y="98" width="18" height="2" rx="1" fill="rgba(255,255,255,0.8)" />
        <rect x="130" y="98" width="16" height="2" rx="1" fill="#fff" />
      </svg>
    ),
  },
];

function Section({ title, icon: Icon, children }) {
  return (
    <div className="card p-5 space-y-4">
      <div className="flex items-center gap-2 pb-1 border-b border-gray-100">
        <Icon size={16} className="text-green-600" />
        <h2 className="text-sm font-semibold text-gray-700">{title}</h2>
      </div>
      {children}
    </div>
  );
}

export default function Settings() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const fileInputRef = useRef(null);
  const [searchParams, setSearchParams] = useSearchParams();

  const [org, setOrg] = useState({
    name: "", email: "", phone: "", address: "", kra_pin: "",
    payment_terms_days: 30, quotation_validity_days: 30, authorised_by: "", logo_url: "", document_template: "classic",
    etims_enabled: false, etims_branch_id: "000", etims_device_serial: "", etims_auth_token: "",
  });
  const [showAuthToken, setShowAuthToken] = useState(false);
  const [etimsTestResult, setEtimsTestResult] = useState(null);
  const [etimsTesting, setEtimsTesting] = useState(false);
  const [orgSaved, setOrgSaved] = useState(false);
  const [orgError, setOrgError] = useState("");
  const [orgSaving, setOrgSaving] = useState(false);

  const [payments, setPayments] = useState({
    paystack_secret_key: "",
    mpesa_consumer_key: "",
    mpesa_consumer_secret: "",
    mpesa_shortcode: "",
    mpesa_passkey: "",
    mpesa_env: "sandbox",
  });
  const [paymentsConfigured, setPaymentsConfigured] = useState({ paystack: false, mpesa: false });
  const [showPaystackKey, setShowPaystackKey] = useState(false);
  const [showMpesaSecret, setShowMpesaSecret] = useState(false);
  const [showMpesaPasskey, setShowMpesaPasskey] = useState(false);
  const [paymentsSaved, setPaymentsSaved] = useState(false);
  const [paymentsError, setPaymentsError] = useState("");
  const [paymentsSaving, setPaymentsSaving] = useState(false);

  const [pw, setPw] = useState({ current_password: "", new_password: "" });
  const [pwSaved, setPwSaved] = useState(false);
  const [pwError, setPwError] = useState("");
  const [pwSaving, setPwSaving] = useState(false);

  const [planInfo, setPlanInfo] = useState(null);
  const [upgradeModal, setUpgradeModal] = useState(null); // { plan, price }
  const [confirmDowngrade, setConfirmDowngrade] = useState(false);
  const [payMethod, setPayMethod] = useState("mpesa"); // "mpesa" | "card"
  const [mpesaPhone, setMpesaPhone] = useState("");
  const [upgrading, setUpgrading] = useState(false);
  const [upgradeMsg, setUpgradeMsg] = useState({ text: "", type: "success" });

  const refreshPlan = async () => {
    const { data } = await getMyPlan();
    setPlanInfo(data.data);
  };

  const openUpgrade = (plan, price) => {
    setUpgradeModal({ plan, price });
    setPayMethod("mpesa");
    setUpgradeMsg({ text: "", type: "success" });
  };

  const handleMpesaUpgrade = async () => {
    if (!mpesaPhone) { setUpgradeMsg({ text: "Enter your M-Pesa phone number", type: "error" }); return; }
    setUpgrading(true);
    setUpgradeMsg({ text: "", type: "success" });
    try {
      const { data } = await api.post("/api/subscriptions/upgrade/mpesa", {
        plan: upgradeModal.plan,
        phone: mpesaPhone,
      });
      setUpgradeMsg({ text: data.message, type: "success" });
      await refreshPlan();
    } catch (err) {
      setUpgradeMsg({ text: err.response?.data?.detail ?? "M-Pesa STK Push failed", type: "error" });
    } finally {
      setUpgrading(false);
    }
  };

  const handlePaystackUpgrade = async () => {
    if (!user?.email) { setUpgradeMsg({ text: "No email on your account", type: "error" }); return; }
    setUpgrading(true);
    try {
      const { data } = await api.post("/api/subscriptions/upgrade/paystack", {
        plan: upgradeModal.plan,
        email: user.email,
      });
      window.location.href = data.authorization_url;
    } catch (err) {
      setUpgradeMsg({ text: err.response?.data?.detail ?? "Paystack initialization failed", type: "error" });
      setUpgrading(false);
    }
  };

  const handleDowngradeToFree = async () => {
    setUpgrading(true);
    try {
      await api.post("/api/subscriptions/upgrade/free");
      setUpgradeMsg({ text: "Downgraded to Free plan", type: "success" });
      await refreshPlan();
      setUpgradeModal(null);
    } catch (err) {
      setUpgradeMsg({ text: err.response?.data?.detail ?? "Downgrade failed", type: "error" });
    } finally {
      setUpgrading(false);
    }
  };

  // Auto-verify Paystack redirect after payment
  useEffect(() => {
    const subRef = searchParams.get("sub_ref");
    if (!subRef) return;
    setSearchParams({}, { replace: true }); // clear the param
    api.get(`/api/subscriptions/upgrade/paystack/verify/${subRef}`)
      .then(({ data }) => {
        if (data.status === "success") {
          setUpgradeMsg({ text: `🎉 ${data.message}`, type: "success" });
          refreshPlan();
        } else {
          setUpgradeMsg({ text: "Payment was not completed. Please try again.", type: "error" });
        }
      })
      .catch(() => setUpgradeMsg({ text: "Could not verify payment. Contact support if charged.", type: "error" }));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    refreshPlan();
    getOrganization()
      .then(({ data }) => {
        const d = data.data;
        setOrg({
          name: d.name ?? "",
          email: d.email ?? "",
          phone: d.phone ?? "",
          address: d.address ?? "",
          kra_pin: d.kra_pin ?? "",
          payment_terms_days: d.payment_terms_days ?? 30,
          quotation_validity_days: d.quotation_validity_days ?? 30,
          authorised_by: d.authorised_by ?? "",
          logo_url: d.logo_url ?? "",
          document_template: d.document_template ?? "classic",
          etims_enabled: d.etims_enabled ?? false,
          etims_branch_id: d.etims_branch_id ?? "000",
          etims_device_serial: d.etims_device_serial ?? "",
          etims_auth_token: "",  // never pre-fill auth token for security
        });
        setPaymentsConfigured({ paystack: d.paystack_configured ?? false, mpesa: d.mpesa_configured ?? false });
        setPayments((p) => ({ ...p, mpesa_env: d.mpesa_env ?? "sandbox" }));
      })
      .catch(() => {});
  }, []);

  const handleLogoChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => setOrg((prev) => ({ ...prev, logo_url: ev.target.result }));
    reader.readAsDataURL(file);
  };

  const handleOrgSave = async (e) => {
    e.preventDefault();
    setOrgSaving(true);
    setOrgError("");
    setOrgSaved(false);
    try {
      await updateOrganization(org);
      setOrgSaved(true);
    } catch (err) {
      setOrgError(err.response?.data?.detail ?? "Failed to save business profile");
    } finally {
      setOrgSaving(false);
    }
  };

  const handleTemplateSelect = async (templateId) => {
    const updated = { ...org, document_template: templateId };
    setOrg(updated);
    try {
      await updateOrganization(updated);
    } catch {
      // silent — selection is still visible; user can save via the form
    }
  };

  const handleEtimsTest = async () => {
    setEtimsTesting(true);
    setEtimsTestResult(null);
    try {
      const { data } = await testEtimsConnection();
      setEtimsTestResult(data);
    } catch (err) {
      setEtimsTestResult({ ok: false, message: err.response?.data?.detail ?? "Test failed" });
    } finally {
      setEtimsTesting(false);
    }
  };

  const handlePaymentsSave = async (e) => {
    e.preventDefault();
    setPaymentsSaving(true);
    setPaymentsError("");
    setPaymentsSaved(false);
    try {
      // Only send fields that have been filled in; empty string means "don't change"
      const payload = {};
      if (payments.paystack_secret_key) payload.paystack_secret_key = payments.paystack_secret_key;
      if (payments.mpesa_consumer_key) payload.mpesa_consumer_key = payments.mpesa_consumer_key;
      if (payments.mpesa_consumer_secret) payload.mpesa_consumer_secret = payments.mpesa_consumer_secret;
      if (payments.mpesa_shortcode) payload.mpesa_shortcode = payments.mpesa_shortcode;
      if (payments.mpesa_passkey) payload.mpesa_passkey = payments.mpesa_passkey;
      payload.mpesa_env = payments.mpesa_env;
      const { data } = await updateOrganization(payload);
      setPaymentsConfigured({ paystack: data.data.paystack_configured ?? false, mpesa: data.data.mpesa_configured ?? false });
      setPayments({ paystack_secret_key: "", mpesa_consumer_key: "", mpesa_consumer_secret: "", mpesa_shortcode: "", mpesa_passkey: "", mpesa_env: payments.mpesa_env });
      setPaymentsSaved(true);
    } catch (err) {
      setPaymentsError(err.response?.data?.detail ?? "Failed to save payment settings");
    } finally {
      setPaymentsSaving(false);
    }
  };

  const handlePwSave = async (e) => {
    e.preventDefault();
    setPwSaving(true);
    setPwError("");
    setPwSaved(false);
    try {
      await api.post("/api/auth/change-password", pw);
      setPwSaved(true);
      setPw({ current_password: "", new_password: "" });
    } catch (err) {
      setPwError(err.response?.data?.detail ?? "Failed to change password");
    } finally {
      setPwSaving(false);
    }
  };

  return (
    <div className="p-4 md:p-6 max-w-2xl mx-auto space-y-5">
      <h1 className="text-xl font-bold text-gray-900">Settings</h1>

      {/* Plan & Billing */}
      {isAdmin && <Section title="Plan &amp; Billing" icon={Zap}>
        {planInfo ? (
          <div className="space-y-4">
            {upgradeMsg.text && (
              <div className={`text-sm px-3 py-2 rounded-lg ${upgradeMsg.type === "error" ? "bg-red-50 text-red-700" : "bg-green-50 text-green-700"}`}>
                {upgradeMsg.text}
              </div>
            )}
            {/* Trial callout */}
            {planInfo.is_trial && planInfo.trial_ends_at && (() => {
              const daysLeft = Math.max(0, Math.ceil((new Date(planInfo.trial_ends_at) - Date.now()) / 86400000));
              const urgent = daysLeft <= 3;
              return (
                <div className={`rounded-lg px-4 py-3 flex items-start gap-3 ${urgent ? "bg-red-50 border border-red-200" : "bg-blue-50 border border-blue-200"}`}>
                  <Zap size={16} className={`mt-0.5 flex-shrink-0 ${urgent ? "text-red-600" : "text-blue-600"}`} />
                  <div>
                    <p className={`text-sm font-semibold ${urgent ? "text-red-700" : "text-blue-700"}`}>
                      {daysLeft === 0 ? "Trial ends today!" : `${daysLeft} day${daysLeft === 1 ? "" : "s"} left on your free trial`}
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      Trial expires {new Date(planInfo.trial_ends_at).toLocaleDateString("en-KE", { day: "numeric", month: "long", year: "numeric" })}.
                      {" "}Pay below to keep your {planInfo.plan} features.
                    </p>
                  </div>
                </div>
              );
            })()}

            <div className="flex items-center gap-3 flex-wrap">
              <div>
                <p className="text-xs text-gray-400 uppercase tracking-wide">Current Plan</p>
                <div className="flex items-center gap-2">
                  <p className="text-lg font-bold text-green-600 capitalize">{planInfo.plan}</p>
                  {planInfo.is_trial && (
                    <span className="text-xs bg-blue-100 text-blue-700 font-medium px-2 py-0.5 rounded-full">Trial</span>
                  )}
                </div>
              </div>
              {planInfo.pending_plan && (
                <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded-full">
                  Pending upgrade to {planInfo.pending_plan} — awaiting payment
                </span>
              )}
              <div className="text-gray-200">|</div>
              <div>
                <p className="text-xs text-gray-400 uppercase tracking-wide">Status</p>
                <p className="text-sm font-medium text-gray-700 capitalize">{planInfo.plan_status}</p>
              </div>
              {planInfo.next_billing_date && !planInfo.is_trial && (
                <>
                  <div className="text-gray-200">|</div>
                  <div>
                    <p className="text-xs text-gray-400 uppercase tracking-wide">Next billing</p>
                    <p className="text-sm text-gray-700">{new Date(planInfo.next_billing_date).toLocaleDateString("en-KE")}</p>
                  </div>
                </>
              )}
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { label: "Invoices this month", used: planInfo.invoices_this_month, cap: planInfo.limits?.invoices_per_month },
                { label: "Quotations this month", used: planInfo.quotations_this_month, cap: planInfo.limits?.quotations_per_month },
                { label: "OCR scans this month", used: planInfo.ocr_scans_this_month, cap: planInfo.limits?.ocr_scans_per_month },
                { label: "AI calls this month", used: planInfo.ai_calls_this_month ?? 0, cap: planInfo.limits?.ai_calls_per_month ?? 0 },
              ].map(({ label, used, cap }) => (
                <div key={label} className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500 mb-1">{label}</p>
                  <p className="text-lg font-bold text-gray-900">{used}<span className="text-xs text-gray-400 font-normal"> / {cap === -1 ? "∞" : cap}</span></p>
                  {cap !== -1 && (
                    <div className="h-1.5 bg-gray-200 rounded-full mt-1.5 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${used / cap > 0.9 ? "bg-red-500" : used / cap > 0.7 ? "bg-yellow-400" : "bg-green-500"}`}
                        style={{ width: `${Math.min(100, (used / cap) * 100)}%` }}
                      />
                    </div>
                  )}
                </div>
              ))}
            </div>
            {planInfo.plan !== "premium" && (
              <div>
                <p className="text-sm font-medium text-gray-700 mb-2">
                  {planInfo.is_trial ? `Activate your ${planInfo.plan} plan` : "Upgrade your plan"}
                </p>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {[
                    { id: "starter", label: "Starter", price: 1500 },
                    { id: "business", label: "Business", price: 3000 },
                    { id: "premium", label: "Premium", price: 5500 },
                  ].filter((p) => planInfo.is_trial ? true : p.id !== planInfo.plan).map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => openUpgrade(p.id, p.price)}
                      className={`rounded-lg px-3 py-2 text-left transition border ${
                        planInfo.is_trial && p.id === planInfo.plan
                          ? "border-green-500 bg-green-50"
                          : "border-green-300 hover:bg-green-50"
                      }`}
                    >
                      <p className="text-sm font-semibold text-green-700">
                        {planInfo.is_trial && p.id === planInfo.plan ? `Activate ${p.label}` : p.label}
                      </p>
                      <p className="text-xs text-gray-500">KES {p.price.toLocaleString()}/mo</p>
                    </button>
                  ))}
                </div>
                {planInfo.plan !== "free" && (
                  <button
                    type="button"
                    onClick={() => setConfirmDowngrade(true)}
                    disabled={upgrading}
                    className="mt-2 text-xs text-gray-400 hover:text-gray-600 underline"
                  >
                    Downgrade to Free
                  </button>
                )}
              </div>
            )}
          </div>
        ) : (
          <div className="text-sm text-gray-400">Loading plan info…</div>
        )}
      </Section>}

      {/* Upgrade payment modal */}
      {upgradeModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-gray-900">
                Upgrade to {upgradeModal.plan.charAt(0).toUpperCase() + upgradeModal.plan.slice(1)}
              </h2>
              <button onClick={() => setUpgradeModal(null)} className="text-gray-400 hover:text-gray-600"><X size={18} /></button>
            </div>
            <p className="text-sm text-gray-500">
              KES {upgradeModal.price.toLocaleString()} / month — billed monthly
            </p>

            {upgradeMsg.text && (
              <div className={`text-sm px-3 py-2 rounded-lg ${upgradeMsg.type === "error" ? "bg-red-50 text-red-700" : "bg-green-50 text-green-700"}`}>
                {upgradeMsg.text}
              </div>
            )}

            {/* Payment method tabs */}
            <div className="flex rounded-lg border border-gray-200 overflow-hidden">
              <button
                type="button"
                onClick={() => setPayMethod("mpesa")}
                className={`flex-1 py-2 text-sm font-medium flex items-center justify-center gap-1.5 transition ${payMethod === "mpesa" ? "bg-green-600 text-white" : "bg-white text-gray-600 hover:bg-gray-50"}`}
              >
                <Smartphone size={14} /> M-Pesa
              </button>
              <button
                type="button"
                onClick={() => setPayMethod("card")}
                className={`flex-1 py-2 text-sm font-medium flex items-center justify-center gap-1.5 transition ${payMethod === "card" ? "bg-green-600 text-white" : "bg-white text-gray-600 hover:bg-gray-50"}`}
              >
                <CreditCard size={14} /> Card
              </button>
            </div>

            {payMethod === "mpesa" && (
              <div className="space-y-3">
                <div>
                  <label className="label">M-Pesa Phone Number</label>
                  <div className="relative">
                    <Phone size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                    <input
                      className="input pl-8"
                      type="tel"
                      placeholder="254700000000"
                      value={mpesaPhone}
                      onChange={(e) => setMpesaPhone(e.target.value)}
                    />
                  </div>
                  <p className="text-xs text-gray-400 mt-1">Format: 254XXXXXXXXX (no +)</p>
                </div>
                <button
                  type="button"
                  onClick={handleMpesaUpgrade}
                  disabled={upgrading}
                  className="btn-primary w-full justify-center"
                >
                  {upgrading ? "Sending STK Push…" : `Pay KES ${upgradeModal.price.toLocaleString()} via M-Pesa`}
                </button>
                <p className="text-xs text-gray-400 text-center">
                  A payment request will be sent to your phone. Approve it to activate your plan.
                </p>
              </div>
            )}

            {payMethod === "card" && (
              <div className="space-y-3">
                <p className="text-sm text-gray-600">
                  You'll be redirected to Paystack's secure checkout to pay with Visa or Mastercard.
                </p>
                <button
                  type="button"
                  onClick={handlePaystackUpgrade}
                  disabled={upgrading}
                  className="btn-primary w-full justify-center"
                >
                  {upgrading ? "Redirecting…" : `Pay KES ${upgradeModal.price.toLocaleString()} with Card`}
                </button>
                <p className="text-xs text-gray-400 text-center">
                  Secured by Paystack. You'll return here after payment.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Business Profile */}
      {isAdmin && <form onSubmit={handleOrgSave}>
        <Section title="Business Profile" icon={Building2}>
          {orgError && <div className="bg-red-50 text-red-700 text-sm px-3 py-2 rounded-lg">{orgError}</div>}
          {orgSaved && <div className="bg-green-50 text-green-700 text-sm px-3 py-2 rounded-lg">Business profile saved.</div>}

          {/* Logo Upload */}
          <div>
            <label className="label">Business Logo</label>
            <div className="flex items-center gap-4">
              <div className="w-20 h-20 rounded-xl border-2 border-dashed border-gray-200 flex items-center justify-center overflow-hidden bg-gray-50 flex-shrink-0">
                {org.logo_url ? (
                  <img src={org.logo_url} alt="logo" className="w-full h-full object-contain p-1" />
                ) : (
                  <div className="text-center">
                    <Upload size={20} className="mx-auto text-gray-300 mb-1" />
                    <span className="text-xs text-gray-400">No logo</span>
                  </div>
                )}
              </div>
              <div className="space-y-2">
                <button type="button" onClick={() => fileInputRef.current?.click()}
                  className="btn-secondary text-xs">
                  <Upload size={13} /> Upload Logo
                </button>
                {org.logo_url && (
                  <button type="button" onClick={() => setOrg((p) => ({ ...p, logo_url: "" }))}
                    className="btn-secondary text-xs text-red-500 hover:text-red-700 flex items-center gap-1 ml-1">
                    <X size={13} /> Remove
                  </button>
                )}
                <p className="text-xs text-gray-400">PNG, JPG or SVG. Recommended: square, max 1 MB.</p>
              </div>
              <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={handleLogoChange} />
            </div>
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <label className="label">Business Name</label>
              <input className="input" value={org.name} onChange={(e) => setOrg({ ...org, name: e.target.value })} required />
            </div>
            <div>
              <label className="label">Business Email</label>
              <input className="input" type="email" placeholder="info@yourbusiness.co.ke" value={org.email}
                onChange={(e) => setOrg({ ...org, email: e.target.value })} />
            </div>
            <div>
              <label className="label">Phone</label>
              <input className="input" placeholder="254700000000" value={org.phone}
                onChange={(e) => setOrg({ ...org, phone: e.target.value })} />
            </div>
            <div className="sm:col-span-2">
              <label className="label">Address</label>
              <input className="input" placeholder="P.O. Box 1234, Nairobi" value={org.address}
                onChange={(e) => setOrg({ ...org, address: e.target.value })} />
            </div>
            <div>
              <label className="label">KRA PIN</label>
              <input className="input" placeholder="P000000000A" value={org.kra_pin}
                onChange={(e) => setOrg({ ...org, kra_pin: e.target.value })} />
            </div>
            <div>
              <label className="label">Authorised By</label>
              <input className="input" placeholder="e.g. John Kamau, Director" value={org.authorised_by}
                onChange={(e) => setOrg({ ...org, authorised_by: e.target.value })} />
              <p className="text-xs text-gray-400 mt-1">Name shown on the signature line of quotations</p>
            </div>
            <div>
              <label className="label">Default Payment Terms (days)</label>
              <input className="input" type="number" min="1" max="365" value={org.payment_terms_days}
                onChange={(e) => setOrg({ ...org, payment_terms_days: Number(e.target.value) })} />
              <p className="text-xs text-gray-400 mt-1">Auto-sets due date on new invoices</p>
            </div>
            <div>
              <label className="label">Default Quotation Validity (days)</label>
              <input className="input" type="number" min="1" max="365" value={org.quotation_validity_days}
                onChange={(e) => setOrg({ ...org, quotation_validity_days: Number(e.target.value) })} />
              <p className="text-xs text-gray-400 mt-1">Auto-sets expiry date on new quotations</p>
            </div>
          </div>

          <div className="flex justify-end pt-1">
            <button type="submit" className="btn-primary" disabled={orgSaving}>
              {orgSaving ? "Saving…" : "Save Business Profile"}
            </button>
          </div>
        </Section>
      </form>}

      {/* Document Template */}
      {isAdmin && <Section title="Document Template" icon={Palette}>
        <p className="text-xs text-gray-500">Choose the design for your quotations and invoices. Your selection is saved automatically when you click a template.</p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {TEMPLATES.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => handleTemplateSelect(t.id)}
              className={`relative rounded-xl border-2 p-0 overflow-hidden transition-all text-left focus:outline-none ${
                org.document_template === t.id
                  ? "border-green-500 ring-2 ring-green-200"
                  : "border-gray-200 hover:border-green-300"
              }`}
            >
              <div className="bg-white aspect-[160/110]">{t.preview}</div>
              <div className="px-3 py-2 bg-white border-t border-gray-100">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-gray-800">{t.name}</span>
                  {org.document_template === t.id && (
                    <span className="text-xs font-semibold text-green-600">Active</span>
                  )}
                </div>
                <p className="text-xs text-gray-400 mt-0.5">{t.description}</p>
              </div>
            </button>
          ))}
        </div>
        <p className="text-xs text-gray-400">Selection is saved immediately — no need to click Save.</p>
      </Section>}

      {/* eTIMS / KRA */}
      {isAdmin && <Section title="KRA eTIMS Integration" icon={ShieldCheck}>
        <div className="space-y-1">
          <p className="text-xs text-gray-500">
            eTIMS (Electronic Tax Invoice Management System) lets you issue KRA-verified receipts with a
            scannable QR code on every invoice. Register at{" "}
            <a href="https://etims.kra.go.ke" target="_blank" rel="noopener noreferrer" className="text-green-600 underline">etims.kra.go.ke</a>{" "}
            to get your Device Serial Number and Auth Token. Works for both VAT-registered and non-VAT businesses.
          </p>
        </div>

        {/* Enable toggle */}
        <label className="flex items-center gap-3 cursor-pointer select-none">
          <div
            onClick={() => setOrg((p) => ({ ...p, etims_enabled: !p.etims_enabled }))}
            className={`relative w-10 h-6 rounded-full transition-colors ${org.etims_enabled ? "bg-green-500" : "bg-gray-200"}`}
          >
            <div className={`absolute top-1 w-4 h-4 rounded-full bg-white shadow transition-transform ${org.etims_enabled ? "translate-x-5" : "translate-x-1"}`} />
          </div>
          <span className="text-sm font-medium text-gray-700">
            {org.etims_enabled ? "eTIMS enabled — QR code will appear on invoices" : "eTIMS disabled — standard invoices only"}
          </span>
        </label>

        {org.etims_enabled && (
          <div className="space-y-3 pt-1">
            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <label className="label">KRA PIN</label>
                <input className="input bg-gray-50" value={org.kra_pin} readOnly
                  placeholder="Set KRA PIN in Business Profile above" />
                <p className="text-xs text-gray-400 mt-1">Uses KRA PIN from Business Profile.</p>
              </div>
              <div>
                <label className="label">Branch ID</label>
                <input className="input" value={org.etims_branch_id}
                  onChange={(e) => setOrg((p) => ({ ...p, etims_branch_id: e.target.value }))}
                  placeholder="000" />
                <p className="text-xs text-gray-400 mt-1">"000" for head office / single branch.</p>
              </div>
              <div>
                <label className="label">Device Serial Number</label>
                <input className="input" value={org.etims_device_serial}
                  onChange={(e) => setOrg((p) => ({ ...p, etims_device_serial: e.target.value }))}
                  placeholder="From KRA eTIMS portal" />
              </div>
              <div>
                <label className="label">Auth Token</label>
                <div className="relative">
                  <input
                    className="input pr-10"
                    type={showAuthToken ? "text" : "password"}
                    value={org.etims_auth_token}
                    onChange={(e) => setOrg((p) => ({ ...p, etims_auth_token: e.target.value }))}
                    placeholder="From KRA eTIMS portal (leave blank to keep current)"
                  />
                  <button type="button" onClick={() => setShowAuthToken((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600" tabIndex={-1}>
                    {showAuthToken ? <EyeOff size={15} /> : <Eye size={15} />}
                  </button>
                </div>
                <p className="text-xs text-gray-400 mt-1">Leave blank to keep the saved token. Only fill when updating.</p>
              </div>
            </div>

            {/* Test connection */}
            <div className="flex items-center gap-3 pt-1">
              <button type="button" onClick={handleEtimsTest} disabled={etimsTesting}
                className="btn-secondary text-xs">
                {etimsTesting ? <Loader size={13} className="animate-spin" /> : <ShieldCheck size={13} />}
                {etimsTesting ? "Testing…" : "Test KRA Connection"}
              </button>
              {etimsTestResult && (
                <span className={`text-xs font-medium ${etimsTestResult.ok ? "text-green-600" : "text-red-600"}`}>
                  {etimsTestResult.message}
                </span>
              )}
            </div>

            <div className="bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
              <p className="text-xs text-amber-800 font-medium">How to get eTIMS credentials:</p>
              <ol className="text-xs text-amber-700 mt-1 space-y-0.5 list-decimal list-inside">
                <li>Go to <strong>etims.kra.go.ke</strong> and log in with your KRA credentials</li>
                <li>Register your business as a Virtual SCU taxpayer</li>
                <li>Download or copy your <strong>Device Serial Number</strong> and <strong>Auth Token</strong></li>
                <li>Enter them above and click Save — then use "Test KRA Connection" to verify</li>
              </ol>
            </div>
          </div>
        )}
      </Section>}

      {/* Payment Integrations */}
      {isAdmin && <form onSubmit={handlePaymentsSave}>
        <Section title="Payment Integrations" icon={CreditCard}>
          <p className="text-xs text-gray-500">
            Connect your own Paystack and M-Pesa accounts so your clients can pay invoices directly into your account.
            Credentials are stored securely and never shown after saving.
          </p>

          {paymentsError && <div className="bg-red-50 text-red-700 text-sm px-3 py-2 rounded-lg">{paymentsError}</div>}
          {paymentsSaved && <div className="bg-green-50 text-green-700 text-sm px-3 py-2 rounded-lg">Payment credentials saved.</div>}

          {/* Paystack */}
          <div className="border border-gray-100 rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CreditCard size={15} className="text-gray-500" />
                <span className="text-sm font-semibold text-gray-700">Paystack (Card Payments)</span>
              </div>
              {paymentsConfigured.paystack ? (
                <span className="flex items-center gap-1 text-xs font-medium text-green-600">
                  <CheckCircle size={13} /> Configured
                </span>
              ) : (
                <span className="text-xs text-gray-400">Not configured</span>
              )}
            </div>
            <div>
              <label className="label">Secret Key</label>
              <div className="relative">
                <input
                  className="input pr-10"
                  type={showPaystackKey ? "text" : "password"}
                  value={payments.paystack_secret_key}
                  onChange={(e) => setPayments((p) => ({ ...p, paystack_secret_key: e.target.value }))}
                  placeholder={paymentsConfigured.paystack ? "Leave blank to keep current key" : "sk_live_... or sk_test_..."}
                />
                <button type="button" onClick={() => setShowPaystackKey((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600" tabIndex={-1}>
                  {showPaystackKey ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
              <p className="text-xs text-gray-400 mt-1">
                Get your secret key from{" "}
                <a href="https://dashboard.paystack.com/#/settings/developers" target="_blank" rel="noopener noreferrer" className="text-green-600 underline">
                  Paystack Dashboard → Settings → API Keys
                </a>
              </p>
            </div>
          </div>

          {/* M-Pesa */}
          <div className="border border-gray-100 rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Smartphone size={15} className="text-gray-500" />
                <span className="text-sm font-semibold text-gray-700">M-Pesa (STK Push)</span>
              </div>
              {paymentsConfigured.mpesa ? (
                <span className="flex items-center gap-1 text-xs font-medium text-green-600">
                  <CheckCircle size={13} /> Configured
                </span>
              ) : (
                <span className="text-xs text-gray-400">Not configured</span>
              )}
            </div>
            <div className="grid sm:grid-cols-2 gap-3">
              <div>
                <label className="label">Consumer Key</label>
                <div className="relative">
                  <input
                    className="input pr-10"
                    type="password"
                    value={payments.mpesa_consumer_key}
                    onChange={(e) => setPayments((p) => ({ ...p, mpesa_consumer_key: e.target.value }))}
                    placeholder={paymentsConfigured.mpesa ? "Leave blank to keep current" : "From Daraja portal"}
                  />
                </div>
              </div>
              <div>
                <label className="label">Consumer Secret</label>
                <div className="relative">
                  <input
                    className="input pr-10"
                    type={showMpesaSecret ? "text" : "password"}
                    value={payments.mpesa_consumer_secret}
                    onChange={(e) => setPayments((p) => ({ ...p, mpesa_consumer_secret: e.target.value }))}
                    placeholder={paymentsConfigured.mpesa ? "Leave blank to keep current" : "From Daraja portal"}
                  />
                  <button type="button" onClick={() => setShowMpesaSecret((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600" tabIndex={-1}>
                    {showMpesaSecret ? <EyeOff size={15} /> : <Eye size={15} />}
                  </button>
                </div>
              </div>
              <div>
                <label className="label">Shortcode (Paybill/Till)</label>
                <input
                  className="input"
                  value={payments.mpesa_shortcode}
                  onChange={(e) => setPayments((p) => ({ ...p, mpesa_shortcode: e.target.value }))}
                  placeholder={paymentsConfigured.mpesa ? "Leave blank to keep current" : "e.g. 174379"}
                />
              </div>
              <div>
                <label className="label">Passkey</label>
                <div className="relative">
                  <input
                    className="input pr-10"
                    type={showMpesaPasskey ? "text" : "password"}
                    value={payments.mpesa_passkey}
                    onChange={(e) => setPayments((p) => ({ ...p, mpesa_passkey: e.target.value }))}
                    placeholder={paymentsConfigured.mpesa ? "Leave blank to keep current" : "From Daraja portal"}
                  />
                  <button type="button" onClick={() => setShowMpesaPasskey((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600" tabIndex={-1}>
                    {showMpesaPasskey ? <EyeOff size={15} /> : <Eye size={15} />}
                  </button>
                </div>
              </div>
              <div className="sm:col-span-2">
                <label className="label">Environment</label>
                <div className="flex gap-3">
                  {["sandbox", "production"].map((env) => (
                    <label key={env} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="mpesa_env"
                        value={env}
                        checked={payments.mpesa_env === env}
                        onChange={() => setPayments((p) => ({ ...p, mpesa_env: env }))}
                        className="accent-green-600"
                      />
                      <span className="text-sm capitalize text-gray-700">{env}</span>
                    </label>
                  ))}
                </div>
                <p className="text-xs text-gray-400 mt-1">Use Sandbox for testing; switch to Production when you go live.</p>
              </div>
            </div>
            <div className="bg-blue-50 border border-blue-100 rounded-lg px-3 py-2">
              <p className="text-xs text-blue-800 font-medium">How to get M-Pesa credentials:</p>
              <ol className="text-xs text-blue-700 mt-1 space-y-0.5 list-decimal list-inside">
                <li>Go to <strong>developer.safaricom.co.ke</strong> and create an account</li>
                <li>Create an app and enable the <strong>M-Pesa Express (STK Push)</strong> API</li>
                <li>Copy your Consumer Key, Consumer Secret, Shortcode, and Passkey</li>
                <li>Test in Sandbox first, then switch to Production when ready</li>
              </ol>
            </div>
          </div>

          <div className="flex justify-end pt-1">
            <button type="submit" className="btn-primary" disabled={paymentsSaving}>
              {paymentsSaving ? "Saving…" : "Save Payment Settings"}
            </button>
          </div>
        </Section>
      </form>}

      {/* Account Info */}
      <Section title="Account" icon={User}>
        <div className="grid sm:grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-xs text-gray-500 mb-0.5">Email</p>
            <p className="font-medium text-gray-900">{user?.email}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-0.5">Name</p>
            <p className="font-medium text-gray-900">{user?.display_name}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-0.5">Role</p>
            <p className="font-medium capitalize text-gray-900">{user?.role}</p>
          </div>
        </div>
      </Section>

      {/* Change Password */}
      <form onSubmit={handlePwSave}>
        <Section title="Change Password" icon={Lock}>
          {pwError && <div className="bg-red-50 text-red-700 text-sm px-3 py-2 rounded-lg">{pwError}</div>}
          {pwSaved && <div className="bg-green-50 text-green-700 text-sm px-3 py-2 rounded-lg">Password changed successfully.</div>}
          <div>
            <label className="label">Current Password</label>
            <input className="input" type="password" value={pw.current_password}
              onChange={(e) => setPw({ ...pw, current_password: e.target.value })} />
          </div>
          <div>
            <label className="label">New Password</label>
            <input className="input" type="password" placeholder="Min 8 characters" value={pw.new_password}
              onChange={(e) => setPw({ ...pw, new_password: e.target.value })} />
          </div>
          <div className="flex justify-end">
            <button type="submit" className="btn-primary" disabled={pwSaving}>
              {pwSaving ? "Saving…" : "Change Password"}
            </button>
          </div>
        </Section>
      </form>

      <Section title="Products &amp; Services Catalog" icon={Package}>
        <p className="text-sm text-gray-500">
          Manage your saved products and services. They autofill line items when creating invoices and quotations — no more typing the same thing twice.
        </p>
        <Link to="/products" className="btn-secondary inline-flex items-center gap-2 mt-1">
          <Package size={15} /> Manage Products <ArrowRight size={13} />
        </Link>
      </Section>

      <ConfirmDialog
        open={confirmDowngrade}
        onClose={() => setConfirmDowngrade(false)}
        onConfirm={handleDowngradeToFree}
        title="Downgrade to Free Plan"
        message="Your current plan features will be removed at the end of this billing cycle. You can upgrade again at any time."
        danger
      />
    </div>
  );
}
