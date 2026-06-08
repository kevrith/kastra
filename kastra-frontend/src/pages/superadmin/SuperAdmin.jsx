import { useState, useEffect, useCallback } from "react";
import {
  superadminLogin, superadminStats, superadminRevenue, superadminPayments,
  superadminTrials, superadminAuditLog, superadminOrgs, superadminOrgDetail,
  superadminChangePlan, superadminSuspendOrg, superadminUnsuspendOrg,
  superadminExtendTrial, superadminRecordPayment,
  superadminGrantComplimentary, superadminRevokeComplimentary,
  superadminResetUserPassword, superadminDeactivateUser, superadminReactivateUser,
  superadminChangeUserRole,
  superadminInvoices, superadminQuotations, superadminSuppliers, superadminSupplierRequests,
  superadminInvoiceDetail, superadminInvoicePdfBlob, superadminQuotationPdfBlob,
  superadminSupplierRequestDetail,
  superadminGetTestimonials, superadminCreateTestimonial,
  superadminUpdateTestimonial, superadminDeleteTestimonial,
  superadminRequestTestimonial, superadminResendTestimonial,
  superadminApproveTestimonial, superadminRejectTestimonial,
} from "../../api/subscriptions";
import {
  LayoutDashboard, Building2, LogOut, Search, ChevronLeft, ChevronRight,
  TrendingUp, Users, FileText, RefreshCw, AlertCircle, CheckCircle2,
  CreditCard, Clock, Activity, DollarSign, BarChart2, ShieldAlert,
  PlusCircle, X, Gift, Menu, Key, UserX, UserCheck, Shield, Receipt, Truck, Package, Printer, Eye,
  MessageSquare, Star, Edit2, Trash2, ToggleLeft, ToggleRight, Send, ThumbsUp, ThumbsDown,
} from "lucide-react";

// ── Colour maps ────────────────────────────────────────────────────────────────
const PLAN_COLORS = {
  free:     "bg-gray-700 text-gray-200",
  starter:  "bg-blue-900 text-blue-200",
  business: "bg-green-900 text-green-200",
  premium:  "bg-purple-900 text-purple-200",
};
const PLAN_COLORS_LIGHT = {
  free:     "bg-gray-100 text-gray-700",
  starter:  "bg-blue-100 text-blue-700",
  business: "bg-green-100 text-green-700",
  premium:  "bg-purple-100 text-purple-700",
};
const STATUS_COLORS = {
  active:        "bg-emerald-900 text-emerald-300",
  suspended:     "bg-red-900 text-red-300",
  cancelled:     "bg-gray-700 text-gray-400",
  complimentary: "bg-pink-900 text-pink-300",
};
const METHOD_COLORS = {
  mpesa:    "bg-green-900 text-green-300",
  paystack: "bg-blue-900 text-blue-300",
  manual:   "bg-yellow-900 text-yellow-300",
};
const ACTION_ICONS = {
  change_plan:          <TrendingUp size={13} />,
  suspend:              <ShieldAlert size={13} />,
  unsuspend:            <CheckCircle2 size={13} />,
  extend_trial:         <Clock size={13} />,
  record_payment:       <CreditCard size={13} />,
  mpesa_payment:        <CreditCard size={13} />,
  paystack_payment:     <CreditCard size={13} />,
  grant_complimentary:  <Gift size={13} />,
  revoke_complimentary: <X size={13} />,
  reset_user_password:  <Key size={13} />,
  deactivate_user:      <UserX size={13} />,
  reactivate_user:      <UserCheck size={13} />,
  change_user_role:     <Shield size={13} />,
};

// ── Reusable components ────────────────────────────────────────────────────────
function StatCard({ label, value, sub, icon: Icon, color = "text-green-400", dark = true }) {
  return (
    <div className={`rounded-xl border p-4 flex items-start gap-3 ${dark ? "bg-gray-800 border-gray-700" : "bg-white border-gray-200"}`}>
      <div className={`p-2 rounded-lg ${dark ? "bg-gray-700" : "bg-gray-50"} ${color}`}>
        <Icon size={18} />
      </div>
      <div className="min-w-0">
        <p className={`text-xl font-bold truncate ${dark ? "text-white" : "text-gray-900"}`}>{value ?? "—"}</p>
        <p className={`text-xs ${dark ? "text-gray-400" : "text-gray-500"}`}>{label}</p>
        {sub && <p className={`text-[10px] mt-0.5 ${dark ? "text-gray-500" : "text-gray-400"}`}>{sub}</p>}
      </div>
    </div>
  );
}

function Badge({ text, colorClass }) {
  return <span className={`inline-block text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wide ${colorClass}`}>{text}</span>;
}

function SectionTitle({ title, onRefresh }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <h2 className="text-base font-bold text-white">{title}</h2>
      {onRefresh && <button onClick={onRefresh} className="text-gray-500 hover:text-gray-300"><RefreshCw size={14} /></button>}
    </div>
  );
}

function Table({ columns, rows, onRowClick, emptyMsg = "No data" }) {
  return (
    <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-x-auto">
      <table className="w-full text-sm min-w-[500px]">
        <thead className="bg-gray-750 border-b border-gray-700">
          <tr>
            {columns.map((c) => (
              <th key={c.key} className={`px-4 py-2.5 text-xs font-semibold text-gray-400 uppercase tracking-wide ${c.right ? "text-right" : "text-left"}`}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-700">
          {rows.length === 0 && (
            <tr><td colSpan={columns.length} className="text-center py-10 text-gray-500 text-sm">{emptyMsg}</td></tr>
          )}
          {rows.map((row, i) => (
            <tr key={i} onClick={onRowClick ? () => onRowClick(row) : undefined}
              className={onRowClick ? "hover:bg-gray-750 cursor-pointer" : ""}>
              {columns.map((c) => (
                <td key={c.key} className={`px-4 py-3 ${c.right ? "text-right" : ""} text-gray-300`}>
                  {c.render ? c.render(row) : row[c.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Pagination({ meta, page, setPage }) {
  if (!meta || meta.pages <= 1) return null;
  return (
    <div className="flex items-center justify-between text-xs text-gray-500 mt-3">
      <span>{meta.total?.toLocaleString()} total</span>
      <div className="flex items-center gap-2">
        <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1} className="p-1 rounded hover:bg-gray-700 disabled:opacity-30"><ChevronLeft size={14} /></button>
        <span className="text-gray-400">Page {page} of {meta.pages}</span>
        <button onClick={() => setPage((p) => Math.min(meta.pages, p + 1))} disabled={page === meta.pages} className="p-1 rounded hover:bg-gray-700 disabled:opacity-30"><ChevronRight size={14} /></button>
      </div>
    </div>
  );
}

function Modal({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
      <div className="bg-gray-800 border border-gray-700 rounded-2xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold text-white">{title}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-white"><X size={18} /></button>
        </div>
        {children}
      </div>
    </div>
  );
}

function fmtKES(n) { return `KES ${Number(n || 0).toLocaleString()}`; }
function fmtDate(s) { return s ? new Date(s).toLocaleDateString("en-KE", { day: "2-digit", month: "short", year: "numeric" }) : "—"; }
function fmtDateTime(s) { return s ? new Date(s).toLocaleString("en-KE", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }) : "—"; }

// ── Main Component ─────────────────────────────────────────────────────────────
export default function SuperAdmin() {
  const [token, setToken] = useState(() => sessionStorage.getItem("sa_token") || "");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [loginForm, setLoginForm] = useState({ username: "", password: "" });
  const [loginError, setLoginError] = useState("");
  const [loginLoading, setLoginLoading] = useState(false);

  const [view, setView] = useState("dashboard");
  const [stats, setStats] = useState(null);
  const [revenue, setRevenue] = useState(null);
  const [payments, setPayments] = useState([]);
  const [paymentsMeta, setPaymentsMeta] = useState(null);
  const [paymentsPage, setPaymentsPage] = useState(1);
  const [trials, setTrials] = useState([]);
  const [auditLog, setAuditLog] = useState([]);
  const [auditMeta, setAuditMeta] = useState(null);
  const [auditPage, setAuditPage] = useState(1);
  const [orgs, setOrgs] = useState([]);
  const [orgsMeta, setOrgsMeta] = useState(null);
  const [orgsPage, setOrgsPage] = useState(1);
  const [orgsSearch, setOrgsSearch] = useState("");
  const [orgsPlanFilter, setOrgsPlanFilter] = useState("");
  const [orgsStatusFilter, setOrgsStatusFilter] = useState("");
  const [selectedOrg, setSelectedOrg] = useState(null);
  const [loading, setLoading] = useState(false);
  const [actionMsg, setActionMsg] = useState({ text: "", type: "success" });

  // Platform data views
  const [saInvoices, setSaInvoices] = useState([]);
  const [saInvoicesMeta, setSaInvoicesMeta] = useState(null);
  const [saInvoicesPage, setSaInvoicesPage] = useState(1);
  const [saInvoicesOrgFilter, setSaInvoicesOrgFilter] = useState("");
  const [saInvoicesStatusFilter, setSaInvoicesStatusFilter] = useState("");

  const [saQuotations, setSaQuotations] = useState([]);
  const [saQuotationsMeta, setSaQuotationsMeta] = useState(null);
  const [saQuotationsPage, setSaQuotationsPage] = useState(1);
  const [saQuotationsOrgFilter, setSaQuotationsOrgFilter] = useState("");
  const [saQuotationsStatusFilter, setSaQuotationsStatusFilter] = useState("");

  const [saSuppliers, setSaSuppliers] = useState([]);
  const [saSuppliersMeta, setSaSuppliersMeta] = useState(null);
  const [saSuppliersPage, setSaSuppliersPage] = useState(1);
  const [saSuppliersOrgFilter, setSaSuppliersOrgFilter] = useState("");

  const [saRequests, setSaRequests] = useState([]);
  const [saRequestsMeta, setSaRequestsMeta] = useState(null);
  const [saRequestsPage, setSaRequestsPage] = useState(1);
  const [saRequestsOrgFilter, setSaRequestsOrgFilter] = useState("");

  const [allOrgs, setAllOrgs] = useState([]); // for filter dropdowns
  const [pdfLoading, setPdfLoading] = useState(null); // id of item generating PDF
  const [viewingRequest, setViewingRequest] = useState(null); // supplier request detail modal

  // Modal states
  const [extendModal, setExtendModal] = useState(false);
  const [extendDays, setExtendDays] = useState(7);
  const [paymentModal, setPaymentModal] = useState(false);
  const [paymentForm, setPaymentForm] = useState({ plan: "starter", amount_kes: 1500, payment_method: "manual", reference: "", note: "" });
  const [compModal, setCompModal] = useState(false);
  const [compForm, setCompForm] = useState({ plan: "starter", reason: "", days: "" });
  const [userActionModal, setUserActionModal] = useState(null); // { type, user }
  const [roleChangeForm, setRoleChangeForm] = useState("");
  const [confirmModal, setConfirmModal] = useState(null); // { title, message, onConfirm }

  // Testimonials
  const [testimonials, setTestimonials] = useState([]);
  const [testimonialLoading, setTestimonialLoading] = useState(false);
  const [testimonialModal, setTestimonialModal] = useState(null); // null | "create" | testimonial object
  const [testimonialForm, setTestimonialForm] = useState({ name: "", role: "", text: "", stars: 5, is_active: true, sort_order: 0 });
  const [testimonialTab, setTestimonialTab] = useState("pending"); // "pending" | "approved" | "rejected"
  const [requestModal, setRequestModal] = useState(false);
  const [requestForm, setRequestForm] = useState({ email: "", name: "", role_hint: "", phone: "" });
  const [rejectModal, setRejectModal] = useState(null); // testimonial id
  const [rejectReason, setRejectReason] = useState("");
  const [whatsappLink, setWhatsappLink] = useState(null); // shown after request sent

  const isAuthed = Boolean(token);

  const flash = (text, type = "success") => {
    setActionMsg({ text, type });
    setTimeout(() => setActionMsg({ text: "", type: "success" }), 4000);
  };

  const logout = () => {
    sessionStorage.removeItem("sa_token");
    setToken("");
    setStats(null);
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginError("");
    setLoginLoading(true);
    try {
      const { data } = await superadminLogin(loginForm.username, loginForm.password);
      sessionStorage.setItem("sa_token", data.access_token);
      setToken(data.access_token);
    } catch {
      setLoginError("Invalid credentials");
    } finally {
      setLoginLoading(false);
    }
  };

  // ── Data loaders ─────────────────────────────────────────────────────────────
  const loadStats = useCallback(async () => {
    if (!token) return;
    try { const { data } = await superadminStats(token); setStats(data); } catch { logout(); }
  }, [token]);

  const loadRevenue = useCallback(async () => {
    if (!token) return;
    try { const { data } = await superadminRevenue(token); setRevenue(data); } catch {}
  }, [token]);

  const loadPayments = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const { data } = await superadminPayments(token, { page: paymentsPage, limit: 25 });
      setPayments(data.data); setPaymentsMeta(data.meta);
    } finally { setLoading(false); }
  }, [token, paymentsPage]);

  const loadTrials = useCallback(async () => {
    if (!token) return;
    try { const { data } = await superadminTrials(token); setTrials(data); } catch {}
  }, [token]);

  const loadAuditLog = useCallback(async () => {
    if (!token) return;
    try {
      const { data } = await superadminAuditLog(token, { page: auditPage, limit: 50 });
      setAuditLog(data.data); setAuditMeta(data.meta);
    } catch {}
  }, [token, auditPage]);

  const loadOrgs = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const { data } = await superadminOrgs(token, {
        page: orgsPage, limit: 20,
        ...(orgsSearch ? { search: orgsSearch } : {}),
        ...(orgsPlanFilter ? { plan: orgsPlanFilter } : {}),
        ...(orgsStatusFilter ? { status: orgsStatusFilter } : {}),
      });
      setOrgs(data.data); setOrgsMeta(data.meta);
    } finally { setLoading(false); }
  }, [token, orgsPage, orgsSearch, orgsPlanFilter, orgsStatusFilter]);

  const loadOrgDetail = async (orgId) => {
    setLoading(true);
    try {
      const { data } = await superadminOrgDetail(token, orgId);
      setSelectedOrg(data); setView("org_detail");
    } finally { setLoading(false); }
  };

  const openPdf = async (type, id) => {
    setPdfLoading(id);
    try {
      const blob = type === "invoice"
        ? await superadminInvoicePdfBlob(token, id)
        : await superadminQuotationPdfBlob(token, id);
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank");
      setTimeout(() => URL.revokeObjectURL(url), 10000);
    } catch {
      flash("Failed to generate PDF", "error");
    } finally {
      setPdfLoading(null);
    }
  };

  const openSupplierRequest = async (id) => {
    try {
      const { data } = await superadminSupplierRequestDetail(token, id);
      setViewingRequest(data);
    } catch {
      flash("Failed to load request", "error");
    }
  };

  const loadAllOrgs = useCallback(async () => {
    if (!token || allOrgs.length > 0) return;
    try {
      const { data } = await superadminOrgs(token, { page: 1, limit: 100 });
      setAllOrgs(data.data ?? []);
    } catch {}
  }, [token, allOrgs.length]);

  const loadSaInvoices = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const { data } = await superadminInvoices(token, {
        page: saInvoicesPage, limit: 30,
        ...(saInvoicesOrgFilter ? { org_id: saInvoicesOrgFilter } : {}),
        ...(saInvoicesStatusFilter ? { payment_status: saInvoicesStatusFilter } : {}),
      });
      setSaInvoices(data.data); setSaInvoicesMeta(data.meta);
    } finally { setLoading(false); }
  }, [token, saInvoicesPage, saInvoicesOrgFilter, saInvoicesStatusFilter]);

  const loadSaQuotations = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const { data } = await superadminQuotations(token, {
        page: saQuotationsPage, limit: 30,
        ...(saQuotationsOrgFilter ? { org_id: saQuotationsOrgFilter } : {}),
        ...(saQuotationsStatusFilter ? { status: saQuotationsStatusFilter } : {}),
      });
      setSaQuotations(data.data); setSaQuotationsMeta(data.meta);
    } finally { setLoading(false); }
  }, [token, saQuotationsPage, saQuotationsOrgFilter, saQuotationsStatusFilter]);

  const loadSaSuppliers = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const { data } = await superadminSuppliers(token, {
        page: saSuppliersPage, limit: 30,
        ...(saSuppliersOrgFilter ? { org_id: saSuppliersOrgFilter } : {}),
      });
      setSaSuppliers(data.data); setSaSuppliersMeta(data.meta);
    } finally { setLoading(false); }
  }, [token, saSuppliersPage, saSuppliersOrgFilter]);

  const loadSaRequests = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const { data } = await superadminSupplierRequests(token, {
        page: saRequestsPage, limit: 30,
        ...(saRequestsOrgFilter ? { org_id: saRequestsOrgFilter } : {}),
      });
      setSaRequests(data.data); setSaRequestsMeta(data.meta);
    } finally { setLoading(false); }
  }, [token, saRequestsPage, saRequestsOrgFilter]);

  const loadTestimonials = useCallback(async () => {
    if (!token) return;
    setTestimonialLoading(true);
    try {
      const { data } = await superadminGetTestimonials(token); // all statuses
      setTestimonials(data);
    } catch { flash("Failed to load testimonials", "error"); }
    finally { setTestimonialLoading(false); }
  }, [token]);

  // ── Effects ───────────────────────────────────────────────────────────────────
  useEffect(() => { if (isAuthed) loadStats(); }, [isAuthed, loadStats]);
  useEffect(() => { if (isAuthed && view === "revenue") { loadRevenue(); loadPayments(); } }, [isAuthed, view, loadRevenue, loadPayments]);
  useEffect(() => { if (isAuthed && view === "revenue") loadPayments(); }, [paymentsPage]);
  useEffect(() => { if (isAuthed && view === "trials") loadTrials(); }, [isAuthed, view, loadTrials]);
  useEffect(() => { if (isAuthed && view === "audit") loadAuditLog(); }, [isAuthed, view, auditPage, loadAuditLog]);
  useEffect(() => { if (isAuthed && view === "orgs") loadOrgs(); }, [isAuthed, view, loadOrgs]);
  useEffect(() => { if (isAuthed && ["invoices","quotations","suppliers","supplier_requests"].includes(view)) loadAllOrgs(); }, [isAuthed, view, loadAllOrgs]);
  useEffect(() => { if (isAuthed && view === "invoices") loadSaInvoices(); }, [isAuthed, view, loadSaInvoices]);
  useEffect(() => { if (isAuthed && view === "quotations") loadSaQuotations(); }, [isAuthed, view, loadSaQuotations]);
  useEffect(() => { if (isAuthed && view === "suppliers") loadSaSuppliers(); }, [isAuthed, view, loadSaSuppliers]);
  useEffect(() => { if (isAuthed && view === "supplier_requests") loadSaRequests(); }, [isAuthed, view, loadSaRequests]);
  useEffect(() => { if (isAuthed && view === "testimonials") loadTestimonials(); }, [isAuthed, view, loadTestimonials]);

  // ── Org actions ───────────────────────────────────────────────────────────────
  const changePlan = async (orgId, plan) => {
    try {
      await superadminChangePlan(token, orgId, plan);
      flash(`Plan changed to ${plan}`);
      await loadOrgDetail(orgId);
    } catch (e) { flash(e.response?.data?.detail ?? "Error changing plan", "error"); }
  };

  const suspendOrg = (orgId) => {
    setConfirmModal({
      title: "Suspend Organisation",
      message: "Suspending blocks the organisation from accessing Kastra until reactivated. Continue?",
      onConfirm: async () => {
        try {
          await superadminSuspendOrg(token, orgId);
          flash("Organisation suspended");
          await loadOrgDetail(orgId);
        } catch { flash("Error suspending org", "error"); }
      },
    });
  };

  const unsuspendOrg = async (orgId) => {
    try {
      await superadminUnsuspendOrg(token, orgId);
      flash("Organisation reactivated");
      await loadOrgDetail(orgId);
    } catch { flash("Error reactivating org", "error"); }
  };

  const doExtendTrial = async () => {
    try {
      await superadminExtendTrial(token, selectedOrg.id, extendDays);
      flash(`Trial extended by ${extendDays} days`);
      setExtendModal(false);
      await loadOrgDetail(selectedOrg.id);
    } catch (e) { flash(e.response?.data?.detail ?? "Error extending trial", "error"); }
  };

  const doGrantComplimentary = async () => {
    if (!compForm.reason.trim()) { flash("Reason is required", "error"); return; }
    try {
      await superadminGrantComplimentary(token, selectedOrg.id, {
        plan: compForm.plan,
        reason: compForm.reason,
        days: compForm.days ? Number(compForm.days) : null,
      });
      flash(`Complimentary ${compForm.plan} access granted`);
      setCompModal(false);
      await loadOrgDetail(selectedOrg.id);
    } catch (e) { flash(e.response?.data?.detail ?? "Error granting access", "error"); }
  };

  const doRevokeComplimentary = () => {
    setConfirmModal({
      title: "Revoke Complimentary Access",
      message: "The organisation will move to the free plan immediately. Continue?",
      onConfirm: async () => {
        try {
          await superadminRevokeComplimentary(token, selectedOrg.id);
          flash("Complimentary access revoked");
          await loadOrgDetail(selectedOrg.id);
        } catch { flash("Error revoking access", "error"); }
      },
    });
  };

  const doRecordPayment = async () => {
    try {
      await superadminRecordPayment(token, selectedOrg.id, paymentForm);
      flash("Payment recorded and plan activated");
      setPaymentModal(false);
      await loadOrgDetail(selectedOrg.id);
    } catch (e) { flash(e.response?.data?.detail ?? "Error recording payment", "error"); }
  };

  const doResetUserPassword = (userId) => {
    setConfirmModal({
      title: "Reset User Password",
      message: "A temporary password will be emailed to this user. Continue?",
      onConfirm: async () => {
        try {
          await superadminResetUserPassword(token, userId);
          flash("Password reset. Temporary password sent via email.");
          setUserActionModal(null);
        } catch (e) { flash(e.response?.data?.detail ?? "Error resetting password", "error"); }
      },
    });
  };

  const doDeactivateUser = (userId) => {
    setConfirmModal({
      title: "Deactivate User",
      message: "This user will be logged out immediately and unable to sign back in until reactivated. Continue?",
      onConfirm: async () => {
        try {
          await superadminDeactivateUser(token, userId);
          flash("User deactivated");
          setUserActionModal(null);
          await loadOrgDetail(selectedOrg.id);
        } catch (e) { flash(e.response?.data?.detail ?? "Error deactivating user", "error"); }
      },
    });
  };

  const doReactivateUser = async (userId) => {
    try {
      await superadminReactivateUser(token, userId);
      flash("User reactivated");
      setUserActionModal(null);
      await loadOrgDetail(selectedOrg.id);
    } catch (e) { flash(e.response?.data?.detail ?? "Error reactivating user", "error"); }
  };

  const doChangeUserRole = async (userId) => {
    if (!roleChangeForm) { flash("Please select a role", "error"); return; }
    try {
      await superadminChangeUserRole(token, userId, roleChangeForm);
      flash(`User role changed to ${roleChangeForm}`);
      setUserActionModal(null);
      await loadOrgDetail(selectedOrg.id);
    } catch (e) { flash(e.response?.data?.detail ?? "Error changing role", "error"); }
  };

  // ── Login screen ──────────────────────────────────────────────────────────────
  if (!isAuthed) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4">
        <div className="w-full max-w-sm">
          <div className="text-center mb-8">
            <img src="/kastra1.png" alt="Kastra" className="h-12 w-12 object-contain mx-auto mb-3" />
            <h1 className="text-xl font-bold text-white">Kastra Admin Console</h1>
            <p className="text-gray-500 text-xs mt-1 uppercase tracking-widest">Restricted Access</p>
          </div>
          <form onSubmit={handleLogin} className="bg-gray-800 border border-gray-700 rounded-2xl p-6 space-y-4">
            {loginError && (
              <div className="bg-red-900/40 border border-red-700 text-red-300 text-sm px-3 py-2 rounded-lg flex items-center gap-2">
                <AlertCircle size={14} /> {loginError}
              </div>
            )}
            {["username", "password"].map((field) => (
              <div key={field}>
                <label className="block text-xs font-medium text-gray-400 mb-1 uppercase tracking-wide">{field}</label>
                <input
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-green-500"
                  type={field === "password" ? "password" : "text"}
                  placeholder={field === "username" ? "superadmin" : "••••••••"}
                  value={loginForm[field]}
                  onChange={(e) => setLoginForm({ ...loginForm, [field]: e.target.value })}
                  required
                />
              </div>
            ))}
            <button type="submit" className="w-full bg-green-600 hover:bg-green-500 text-white font-semibold py-2.5 rounded-lg text-sm transition" disabled={loginLoading}>
              {loginLoading ? "Authenticating…" : "Sign in"}
            </button>
          </form>
        </div>
      </div>
    );
  }

  // ── Authenticated layout ──────────────────────────────────────────────────────
  const navItems = [
    { id: "dashboard",         label: "Dashboard",       icon: LayoutDashboard },
    { id: "revenue",           label: "Revenue",         icon: DollarSign },
    { id: "trials",            label: "Trials",          icon: Clock, badge: stats?.trials_expiring_7d > 0 ? stats.trials_expiring_7d : null },
    { id: "orgs",              label: "Organisations",   icon: Building2 },
    { id: "invoices",          label: "Invoices",        icon: Receipt },
    { id: "quotations",        label: "Quotations",      icon: FileText },
    { id: "suppliers",         label: "Suppliers",       icon: Truck },
    { id: "supplier_requests", label: "Price Requests",  icon: Package },
    { id: "audit",             label: "Audit Log",       icon: Activity },
    { id: "testimonials", label: "Testimonials", icon: MessageSquare, badge: testimonials.filter((t) => t.status === "pending" && t.submitted_at).length || null },
  ];

  return (
    <div className="min-h-screen bg-gray-950 flex">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/60 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={`fixed lg:static inset-y-0 left-0 z-40 w-56 bg-gray-900 border-r border-gray-800 flex flex-col shrink-0 transition-transform duration-200 ${
        sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
      }`}>
        <div className="p-4 border-b border-gray-800">
          <div className="flex items-center gap-2.5">
            <img src="/kastra1.png" alt="" className="h-8 w-8 object-contain" />
            <div>
              <p className="text-sm font-bold text-white">Kastra</p>
              <p className="text-[10px] text-green-500 uppercase tracking-widest">Admin Console</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 p-3 space-y-0.5 overflow-y-auto">
          {navItems.map(({ id, label, icon: Icon, badge }) => (
            <button
              key={id}
              onClick={() => { setView(id); setSidebarOpen(false); }}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition ${
                view === id || (view === "org_detail" && id === "orgs")
                  ? "bg-green-600 text-white"
                  : "text-gray-400 hover:bg-gray-800 hover:text-white"
              }`}
            >
              <span className="flex items-center gap-2.5"><Icon size={15} />{label}</span>
              {badge && <span className="bg-red-500 text-white text-[9px] font-bold w-4 h-4 rounded-full flex items-center justify-center">{badge}</span>}
            </button>
          ))}
        </nav>

        <div className="p-3 border-t border-gray-800 space-y-1">
          {stats && (
            <div className="px-3 py-2 text-xs text-gray-500">
              <p>MRR <span className="text-green-400 font-semibold">{fmtKES(stats.mrr_kes)}</span></p>
              <p>ARR <span className="text-green-400 font-semibold">{fmtKES(stats.arr_kes)}</span></p>
            </div>
          )}
          <button onClick={logout} className="w-full flex items-center gap-2 px-3 py-2 text-gray-500 hover:text-white text-sm rounded-lg hover:bg-gray-800">
            <LogOut size={14} /> Sign out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto bg-gray-950 lg:ml-0">
        {/* Mobile top bar */}
        <div className="lg:hidden flex items-center gap-3 px-4 py-3 bg-gray-900 border-b border-gray-800 sticky top-0 z-20">
          <button onClick={() => setSidebarOpen(true)} className="text-gray-400 hover:text-white p-1">
            <Menu size={20} />
          </button>
          <div className="flex items-center gap-2">
            <img src="/kastra1.png" alt="" className="h-6 w-6 object-contain" />
            <span className="text-sm font-bold text-white">Admin Console</span>
          </div>
        </div>
        <div className="p-4 md:p-6 max-w-6xl mx-auto space-y-6">

          {/* Flash message */}
          {actionMsg.text && (
            <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-xl text-sm font-medium shadow-xl border flex items-center gap-2 max-w-[calc(100vw-2rem)] ${
              actionMsg.type === "error" ? "bg-red-900 border-red-700 text-red-200" : "bg-green-900 border-green-700 text-green-200"
            }`}>
              {actionMsg.type === "error" ? <AlertCircle size={14} /> : <CheckCircle2 size={14} />}
              {actionMsg.text}
            </div>
          )}

          {/* ─── DASHBOARD ─── */}
          {view === "dashboard" && (
            <>
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-xl font-bold text-white">Dashboard</h1>
                  <p className="text-xs text-gray-500 mt-0.5">Platform overview · {new Date().toLocaleDateString("en-KE", { day: "2-digit", month: "long", year: "numeric" })}</p>
                </div>
                <button onClick={loadStats} className="text-gray-500 hover:text-gray-300 p-1.5 rounded-lg hover:bg-gray-800"><RefreshCw size={15} /></button>
              </div>

              {stats ? (
                <>
                  {/* Top KPIs */}
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                    <StatCard
                      label="Monthly Recurring Revenue"
                      value={fmtKES(stats.mrr_kes)}
                      sub={stats.mrr_kes === 0 ? `Potential: ${fmtKES(stats.potential_mrr ?? 0)} if trials convert` : `Potential: ${fmtKES(stats.potential_mrr ?? 0)}`}
                      icon={DollarSign}
                      color={stats.mrr_kes > 0 ? "text-green-400" : "text-gray-500"}
                    />
                    <StatCard label="Annual Run Rate" value={fmtKES(stats.arr_kes)} sub="MRR × 12" icon={TrendingUp} color={stats.arr_kes > 0 ? "text-emerald-400" : "text-gray-500"} />
                    <StatCard label="Revenue This Month" value={fmtKES(stats.revenue_this_month_kes)} sub="Actual payments received" icon={CreditCard} color={stats.revenue_this_month_kes > 0 ? "text-blue-400" : "text-gray-500"} />
                    <StatCard label="Total Revenue" value={fmtKES(stats.total_revenue_kes)} sub="All payments all-time" icon={BarChart2} color={stats.total_revenue_kes > 0 ? "text-purple-400" : "text-gray-500"} />
                  </div>

                  {/* Org & user stats */}
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                    <StatCard label="Total Organisations" value={stats.total_orgs?.toLocaleString()} icon={Building2} color="text-gray-300" />
                    <StatCard
                      label="New (Last 30 days)"
                      value={stats.new_orgs_last_30_days ?? stats.new_orgs_this_month}
                      sub={`This calendar month: ${stats.new_orgs_this_month}`}
                      icon={PlusCircle}
                      color="text-cyan-400"
                    />
                    <StatCard
                      label="Active Orgs (30d)"
                      value={stats.active_orgs_30d ?? stats.active_orgs}
                      sub="Invoiced or quoted in 30 days"
                      icon={Activity}
                      color={(stats.active_orgs_30d ?? stats.active_orgs) > 0 ? "text-yellow-400" : "text-gray-500"}
                    />
                    <StatCard label="Total Users" value={stats.total_users?.toLocaleString()} icon={Users} color="text-gray-300" />
                  </div>

                  {/* Platform usage stats */}
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                    <StatCard label="Total Invoices" value={stats.total_invoices?.toLocaleString()} icon={FileText} color="text-green-400" />
                    <StatCard label="Total Quotations" value={stats.total_quotations?.toLocaleString()} icon={FileText} color="text-blue-400" />
                    <StatCard label="Total Suppliers" value={stats.total_suppliers?.toLocaleString()} icon={Building2} color="text-pink-400" />
                    <StatCard label="Price Requests" value={stats.total_supplier_requests?.toLocaleString()} icon={FileText} color="text-orange-400" />
                  </div>

                  {/* Trial & health stats */}
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                    <StatCard label="Active Trials" value={stats.trials_active} icon={Clock} color="text-orange-400" />
                    <StatCard label="Trials Expiring (7d)" value={stats.trials_expiring_7d} icon={AlertCircle} color={stats.trials_expiring_7d > 0 ? "text-red-400" : "text-gray-500"} />
                    <StatCard label="Complimentary Accounts" value={stats.complimentary_count} sub="Not in MRR" icon={Gift} color="text-pink-400" />
                    <StatCard label="Suspended Orgs" value={stats.suspended_orgs} icon={ShieldAlert} color={stats.suspended_orgs > 0 ? "text-red-400" : "text-gray-500"} />
                  </div>

                  {/* Plan distribution + Conversion funnel + Feature adoption */}
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
                      <SectionTitle title="Paid Plan Distribution" />
                      <div className="space-y-3">
                        {["starter", "business", "premium"].map((plan) => {
                          const count = stats.plan_distribution?.[plan] ?? 0;
                          const max = Math.max(...["starter", "business", "premium"].map((p) => stats.plan_distribution?.[p] ?? 0), 1);
                          return (
                            <div key={plan}>
                              <div className="flex justify-between text-xs mb-1">
                                <span className="text-gray-300 capitalize">{plan}</span>
                                <span className="text-gray-400">{count} orgs · {fmtKES(count * { starter: 1500, business: 3000, premium: 5500 }[plan])}/mo</span>
                              </div>
                              <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                                <div className={`h-full rounded-full transition-all ${plan === "starter" ? "bg-blue-500" : plan === "business" ? "bg-green-500" : "bg-purple-500"}`}
                                  style={{ width: `${(count / max) * 100}%` }} />
                              </div>
                            </div>
                          );
                        })}
                        <div className="pt-1 border-t border-gray-700 flex justify-between text-xs text-gray-500">
                          <span>Free: {stats.plan_distribution?.free ?? 0}</span>
                          <span>Trials: {Object.values(stats.trial_distribution ?? {}).reduce((a, b) => a + b, 0)}</span>
                        </div>
                      </div>
                    </div>

                    {/* Conversion funnel */}
                    <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
                      <SectionTitle title="Conversion Funnel" />
                      <div className="space-y-3">
                        {[
                          { label: "Free", value: stats.free_orgs ?? 0, color: "bg-gray-500" },
                          { label: "Trial", value: Object.values(stats.trial_distribution ?? {}).reduce((a, b) => a + b, 0), color: "bg-yellow-500" },
                          { label: "Paid", value: stats.paid_orgs ?? 0, color: "bg-green-500" },
                          { label: "Complimentary", value: stats.complimentary_count ?? 0, color: "bg-pink-500" },
                        ].map(({ label, value, color }) => {
                          const total = stats.total_orgs || 1;
                          const pct = Math.round((value / total) * 100);
                          return (
                            <div key={label}>
                              <div className="flex justify-between text-xs mb-1">
                                <span className="text-gray-300">{label}</span>
                                <span className="text-gray-400">{value} orgs · {pct}%</span>
                              </div>
                              <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                                <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    {/* Feature adoption */}
                    <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
                      <SectionTitle title="Feature Adoption" />
                      <div className="space-y-2.5">
                        {[
                          { label: "Expenses", value: stats.orgs_using_expenses ?? 0 },
                          { label: "Suppliers", value: stats.orgs_using_suppliers ?? 0 },
                          { label: "eTIMS / KRA", value: stats.orgs_with_etims ?? 0 },
                        ].map(({ label, value }) => {
                          const total = stats.total_orgs || 1;
                          const pct = Math.round((value / total) * 100);
                          return (
                            <div key={label}>
                              <div className="flex justify-between text-xs mb-1">
                                <span className="text-gray-300">{label}</span>
                                <span className="text-gray-400">{value} orgs · {pct}%</span>
                              </div>
                              <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                                <div className="h-full rounded-full bg-indigo-500" style={{ width: `${pct}%` }} />
                              </div>
                            </div>
                          );
                        })}
                        <div className="pt-2 border-t border-gray-700 space-y-1 text-xs text-gray-500">
                          <div className="flex justify-between"><span>Price requests created</span><span className="text-gray-300">{stats.total_supplier_requests ?? 0}</span></div>
                          <div className="flex justify-between"><span>Active suppliers</span><span className="text-gray-300">{stats.total_suppliers ?? 0}</span></div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Trial distribution */}
                  {!Object.values(stats.trial_distribution ?? {}).every((v) => v === 0) && (
                    <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
                      <SectionTitle title="Trial Distribution" />
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                        {["starter", "business", "premium"].map((plan) => {
                          const count = stats.trial_distribution?.[plan] ?? 0;
                          return (
                            <div key={plan} className="flex items-center justify-between bg-gray-700/50 rounded-lg px-3 py-2">
                              <Badge text={plan} colorClass={PLAN_COLORS[plan]} />
                              <span className="text-white font-bold">{count} <span className="text-gray-400 font-normal text-xs">on trial</span></span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-center py-16 text-gray-500">Loading dashboard…</div>
              )}
            </>
          )}

          {/* ─── REVENUE ─── */}
          {view === "revenue" && (
            <>
              <div className="flex items-center justify-between">
                <h1 className="text-xl font-bold text-white">Revenue</h1>
                <button onClick={() => { loadRevenue(); loadPayments(); }} className="text-gray-500 hover:text-gray-300 p-1.5 rounded-lg hover:bg-gray-800"><RefreshCw size={15} /></button>
              </div>

              {/* Monthly breakdown */}
              {revenue && (
                <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
                  <SectionTitle title="Monthly Revenue (Last 6 Months)" />
                  {revenue.monthly.length === 0 ? (
                    <p className="text-gray-500 text-sm text-center py-6">No payment data yet — payments will appear here after the first subscription</p>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead><tr className="border-b border-gray-700">
                          <th className="text-left py-2 text-xs text-gray-400 font-semibold uppercase">Month</th>
                          <th className="text-right py-2 text-xs text-gray-400 font-semibold uppercase">M-Pesa</th>
                          <th className="text-right py-2 text-xs text-gray-400 font-semibold uppercase">Card (Paystack)</th>
                          <th className="text-right py-2 text-xs text-gray-400 font-semibold uppercase">Manual</th>
                          <th className="text-right py-2 text-xs text-gray-400 font-semibold uppercase">Total</th>
                        </tr></thead>
                        <tbody className="divide-y divide-gray-700/50">
                          {revenue.monthly.map((m) => (
                            <tr key={m.month}>
                              <td className="py-2.5 text-gray-200">{m.month}</td>
                              <td className="py-2.5 text-right text-gray-400">{m.mpesa ? fmtKES(m.mpesa) : "—"}</td>
                              <td className="py-2.5 text-right text-gray-400">{m.paystack ? fmtKES(m.paystack) : "—"}</td>
                              <td className="py-2.5 text-right text-gray-400">{m.manual ? fmtKES(m.manual) : "—"}</td>
                              <td className="py-2.5 text-right font-semibold text-green-400">{fmtKES(m.total)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}

              {/* Revenue by plan */}
              {revenue?.by_plan?.length > 0 && (
                <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
                  <SectionTitle title="Revenue by Plan (All Time)" />
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    {revenue.by_plan.map((p) => (
                      <div key={p.plan} className="bg-gray-700/50 rounded-xl p-4">
                        <Badge text={p.plan} colorClass={PLAN_COLORS[p.plan] || "bg-gray-600 text-gray-300"} />
                        <p className="text-xl font-bold text-white mt-2">{fmtKES(p.total_kes)}</p>
                        <p className="text-xs text-gray-400">{p.payment_count} payments</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Payment history */}
              <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
                <SectionTitle title="Payment History" />
                {loading ? (
                  <p className="text-center py-8 text-gray-500">Loading…</p>
                ) : (
                  <>
                    <Table
                      columns={[
                        { key: "created_at", label: "Date", render: (r) => <span className="text-xs">{fmtDateTime(r.created_at)}</span> },
                        { key: "org_name", label: "Organisation", render: (r) => <span className="text-gray-200">{r.org_name}</span> },
                        { key: "plan", label: "Plan", render: (r) => <Badge text={r.plan} colorClass={PLAN_COLORS[r.plan] || ""} /> },
                        { key: "payment_method", label: "Method", render: (r) => <Badge text={r.payment_method} colorClass={METHOD_COLORS[r.payment_method] || "bg-gray-700 text-gray-300"} /> },
                        { key: "amount_kes", label: "Amount", right: true, render: (r) => <span className="font-semibold text-green-400">{fmtKES(r.amount_kes)}</span> },
                        { key: "reference", label: "Ref", render: (r) => <span className="text-xs text-gray-500 font-mono">{r.reference || "—"}</span> },
                      ]}
                      rows={payments}
                      emptyMsg="No payments recorded yet"
                    />
                    <Pagination meta={paymentsMeta} page={paymentsPage} setPage={setPaymentsPage} />
                  </>
                )}
              </div>
            </>
          )}

          {/* ─── TRIALS ─── */}
          {view === "trials" && (
            <>
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-xl font-bold text-white">Active Trials</h1>
                  <p className="text-xs text-gray-500 mt-0.5">{trials.length} organisations on trial · sorted by expiry</p>
                </div>
                <button onClick={loadTrials} className="text-gray-500 hover:text-gray-300 p-1.5 rounded-lg hover:bg-gray-800"><RefreshCw size={15} /></button>
              </div>

              {trials.length === 0 ? (
                <div className="bg-gray-800 border border-gray-700 rounded-xl p-12 text-center text-gray-500">No active trials</div>
              ) : (
                <div className="space-y-2">
                  {trials.map((t) => (
                    <div key={t.id} className={`bg-gray-800 border rounded-xl px-4 py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${t.days_left <= 3 ? "border-red-700" : t.days_left <= 7 ? "border-yellow-700" : "border-gray-700"}`}>
                      <div>
                        <p className="font-semibold text-white">{t.name}</p>
                        <p className="text-xs text-gray-400">{t.email || "no email"} · Signed up {fmtDate(t.created_at)}</p>
                      </div>
                      <div className="flex items-center gap-3 shrink-0">
                        <Badge text={t.plan} colorClass={PLAN_COLORS[t.plan] || ""} />
                        <div className={`text-center px-3 py-1.5 rounded-lg ${t.days_left <= 3 ? "bg-red-900/50 text-red-300" : t.days_left <= 7 ? "bg-yellow-900/50 text-yellow-300" : "bg-gray-700 text-gray-300"}`}>
                          <p className="text-lg font-bold leading-none">{t.days_left}</p>
                          <p className="text-[9px] uppercase tracking-wide">days left</p>
                        </div>
                        <button
                          onClick={() => loadOrgDetail(t.id)}
                          className="text-xs bg-gray-700 hover:bg-gray-600 text-gray-200 px-3 py-1.5 rounded-lg transition"
                        >
                          Manage →
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}

          {/* ─── ORGANISATIONS ─── */}
          {view === "orgs" && (
            <>
              <div className="flex items-center justify-between flex-wrap gap-3">
                <h1 className="text-xl font-bold text-white">Organisations</h1>
                <div className="flex items-center gap-2 flex-wrap">
                  <div className="relative">
                    <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500" />
                    <input
                      className="bg-gray-800 border border-gray-700 text-white rounded-lg pl-8 pr-3 py-1.5 text-sm focus:outline-none focus:border-green-500 w-44"
                      placeholder="Search name…"
                      value={orgsSearch}
                      onChange={(e) => { setOrgsSearch(e.target.value); setOrgsPage(1); }}
                    />
                  </div>
                  {[
                    { label: "All plans", value: "", setter: setOrgsPlanFilter, current: orgsPlanFilter, options: ["free", "starter", "business", "premium"] },
                    { label: "All status", value: "", setter: setOrgsStatusFilter, current: orgsStatusFilter, options: ["active", "suspended", "complimentary"] },
                  ].map((f, i) => (
                    <select key={i}
                      className="bg-gray-800 border border-gray-700 text-gray-300 rounded-lg px-2 py-1.5 text-sm focus:outline-none focus:border-green-500"
                      value={f.current}
                      onChange={(e) => { f.setter(e.target.value); setOrgsPage(1); }}
                    >
                      <option value="">{f.label}</option>
                      {f.options.map((o) => <option key={o} value={o}>{o}</option>)}
                    </select>
                  ))}
                </div>
              </div>

              {loading ? (
                <div className="text-center py-16 text-gray-500">Loading…</div>
              ) : (
                <>
                  <Table
                    columns={[
                      { key: "name", label: "Organisation", render: (r) => (
                        <div>
                          <p className="font-medium text-gray-100">{r.name}</p>
                          <p className="text-xs text-gray-500">{r.email || "—"}</p>
                        </div>
                      )},
                      { key: "plan", label: "Plan", render: (r) => (
                        <div className="space-y-1">
                          <Badge text={r.plan} colorClass={PLAN_COLORS[r.plan] || ""} />
                          {r.is_trial && <span className="block text-[10px] text-yellow-400">{r.days_left_trial}d trial left</span>}
                          {!r.is_trial && r.days_until_renewal != null && r.days_until_renewal <= 5 && r.days_until_renewal >= 0 && (
                            <span className="block text-[10px] text-orange-400">Renews in {r.days_until_renewal}d</span>
                          )}
                          {!r.is_trial && r.days_until_renewal != null && r.days_until_renewal < 0 && (
                            <span className="block text-[10px] text-red-400">Overdue {Math.abs(r.days_until_renewal)}d</span>
                          )}
                        </div>
                      )},
                      { key: "plan_status", label: "Status", render: (r) => <Badge text={r.plan_status} colorClass={STATUS_COLORS[r.plan_status] || ""} /> },
                      { key: "user_count", label: "Users", right: true },
                      { key: "invoices_this_month", label: "Inv/mo", right: true },
                      { key: "created_at", label: "Joined", right: true, render: (r) => <span className="text-xs text-gray-500">{fmtDate(r.created_at)}</span> },
                    ]}
                    rows={orgs}
                    onRowClick={(r) => loadOrgDetail(r.id)}
                    emptyMsg="No organisations found"
                  />
                  <Pagination meta={orgsMeta} page={orgsPage} setPage={setOrgsPage} />
                </>
              )}
            </>
          )}

          {/* ─── HELPER: org filter dropdown ─── */}
          {/* reused across invoices/quotations/suppliers views */}

          {/* ─── INVOICES ─── */}
          {view === "invoices" && (
            <>
              <div className="flex items-center justify-between flex-wrap gap-3">
                <h1 className="text-xl font-bold text-white">All Invoices</h1>
                <button onClick={loadSaInvoices} className="text-gray-500 hover:text-gray-300 p-1.5 rounded-lg hover:bg-gray-800"><RefreshCw size={15} /></button>
              </div>
              <div className="flex flex-wrap gap-3">
                <select className="bg-gray-800 border border-gray-700 text-gray-300 text-sm rounded-lg px-3 py-2"
                  value={saInvoicesOrgFilter} onChange={(e) => { setSaInvoicesOrgFilter(e.target.value); setSaInvoicesPage(1); }}>
                  <option value="">All organisations</option>
                  {allOrgs.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
                </select>
                <select className="bg-gray-800 border border-gray-700 text-gray-300 text-sm rounded-lg px-3 py-2"
                  value={saInvoicesStatusFilter} onChange={(e) => { setSaInvoicesStatusFilter(e.target.value); setSaInvoicesPage(1); }}>
                  <option value="">All statuses</option>
                  <option value="unpaid">Unpaid</option>
                  <option value="partial">Partial</option>
                  <option value="paid">Paid</option>
                </select>
              </div>
              <Table
                columns={[
                  { key: "id", label: "Invoice ID", render: (r) => <span className="font-mono text-xs text-green-400">{r.id}</span> },
                  { key: "org_name", label: "Organisation", render: (r) => <button className="text-blue-400 hover:underline text-xs" onClick={() => loadOrgDetail(r.org_id)}>{r.org_name}</button> },
                  { key: "client_name", label: "Client" },
                  { key: "grand_total", label: "Amount", right: true, render: (r) => <span className="font-semibold text-green-400">{fmtKES(r.grand_total)}</span> },
                  { key: "payment_status", label: "Status", render: (r) => <Badge text={r.payment_status} colorClass={r.payment_status === "paid" ? "bg-green-900 text-green-300" : r.payment_status === "partial" ? "bg-blue-900 text-blue-300" : "bg-amber-900 text-amber-300"} /> },
                  { key: "created_at", label: "Date", render: (r) => <span className="text-xs text-gray-400">{fmtDate(r.created_at)}</span> },
                  { key: "_print", label: "", render: (r) => (
                    <button
                      onClick={() => openPdf("invoice", r.id)}
                      disabled={pdfLoading === r.id}
                      className="flex items-center gap-1 text-xs text-gray-400 hover:text-white px-2 py-1 rounded hover:bg-gray-700 transition"
                      title="Print / Download PDF"
                    >
                      <Printer size={13} /> {pdfLoading === r.id ? "…" : "Print"}
                    </button>
                  )},
                ]}
                rows={saInvoices}
              />
              {saInvoicesMeta && saInvoicesMeta.pages > 1 && (
                <Paginator meta={saInvoicesMeta} page={saInvoicesPage} setPage={setSaInvoicesPage} />
              )}
              {saInvoices.length === 0 && !loading && <p className="text-center text-gray-500 py-10">No invoices found.</p>}
            </>
          )}

          {/* ─── QUOTATIONS ─── */}
          {view === "quotations" && (
            <>
              <div className="flex items-center justify-between flex-wrap gap-3">
                <h1 className="text-xl font-bold text-white">All Quotations</h1>
                <button onClick={loadSaQuotations} className="text-gray-500 hover:text-gray-300 p-1.5 rounded-lg hover:bg-gray-800"><RefreshCw size={15} /></button>
              </div>
              <div className="flex flex-wrap gap-3">
                <select className="bg-gray-800 border border-gray-700 text-gray-300 text-sm rounded-lg px-3 py-2"
                  value={saQuotationsOrgFilter} onChange={(e) => { setSaQuotationsOrgFilter(e.target.value); setSaQuotationsPage(1); }}>
                  <option value="">All organisations</option>
                  {allOrgs.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
                </select>
                <select className="bg-gray-800 border border-gray-700 text-gray-300 text-sm rounded-lg px-3 py-2"
                  value={saQuotationsStatusFilter} onChange={(e) => { setSaQuotationsStatusFilter(e.target.value); setSaQuotationsPage(1); }}>
                  <option value="">All statuses</option>
                  <option value="draft">Draft</option>
                  <option value="pending">Pending</option>
                  <option value="accepted">Accepted</option>
                  <option value="declined">Declined</option>
                  <option value="converted">Converted</option>
                </select>
              </div>
              <Table
                columns={[
                  { key: "id", label: "Quotation ID", render: (r) => <span className="font-mono text-xs text-blue-400">{r.id}</span> },
                  { key: "org_name", label: "Organisation", render: (r) => <button className="text-blue-400 hover:underline text-xs" onClick={() => loadOrgDetail(r.org_id)}>{r.org_name}</button> },
                  { key: "client_name", label: "Client" },
                  { key: "grand_total", label: "Amount", right: true, render: (r) => <span className="font-semibold text-blue-400">{fmtKES(r.grand_total)}</span> },
                  { key: "status", label: "Status", render: (r) => <Badge text={r.status} colorClass={r.status === "accepted" ? "bg-green-900 text-green-300" : r.status === "converted" ? "bg-purple-900 text-purple-300" : r.status === "declined" ? "bg-red-900 text-red-300" : "bg-amber-900 text-amber-300"} /> },
                  { key: "created_at", label: "Date", render: (r) => <span className="text-xs text-gray-400">{fmtDate(r.created_at)}</span> },
                  { key: "_print", label: "", render: (r) => (
                    <button
                      onClick={() => openPdf("quotation", r.id)}
                      disabled={pdfLoading === r.id}
                      className="flex items-center gap-1 text-xs text-gray-400 hover:text-white px-2 py-1 rounded hover:bg-gray-700 transition"
                      title="Print / Download PDF"
                    >
                      <Printer size={13} /> {pdfLoading === r.id ? "…" : "Print"}
                    </button>
                  )},
                ]}
                rows={saQuotations}
              />
              {saQuotationsMeta && saQuotationsMeta.pages > 1 && (
                <Paginator meta={saQuotationsMeta} page={saQuotationsPage} setPage={setSaQuotationsPage} />
              )}
              {saQuotations.length === 0 && !loading && <p className="text-center text-gray-500 py-10">No quotations found.</p>}
            </>
          )}

          {/* ─── SUPPLIERS ─── */}
          {view === "suppliers" && (
            <>
              <div className="flex items-center justify-between flex-wrap gap-3">
                <h1 className="text-xl font-bold text-white">All Suppliers</h1>
                <button onClick={loadSaSuppliers} className="text-gray-500 hover:text-gray-300 p-1.5 rounded-lg hover:bg-gray-800"><RefreshCw size={15} /></button>
              </div>
              <div className="flex flex-wrap gap-3">
                <select className="bg-gray-800 border border-gray-700 text-gray-300 text-sm rounded-lg px-3 py-2"
                  value={saSuppliersOrgFilter} onChange={(e) => { setSaSuppliersOrgFilter(e.target.value); setSaSuppliersPage(1); }}>
                  <option value="">All organisations</option>
                  {allOrgs.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
                </select>
              </div>
              <Table
                columns={[
                  { key: "name", label: "Supplier Name" },
                  { key: "company_name", label: "Company", render: (r) => <span className="text-gray-400">{r.company_name || "—"}</span> },
                  { key: "org_name", label: "Organisation", render: (r) => <button className="text-blue-400 hover:underline text-xs" onClick={() => loadOrgDetail(r.org_id)}>{r.org_name}</button> },
                  { key: "phone", label: "Phone", render: (r) => <span className="text-gray-400 text-xs font-mono">{r.phone || "—"}</span> },
                  { key: "email", label: "Email", render: (r) => <span className="text-gray-400 text-xs">{r.email || "—"}</span> },
                  { key: "created_at", label: "Added", render: (r) => <span className="text-xs text-gray-400">{fmtDate(r.created_at)}</span> },
                ]}
                rows={saSuppliers}
              />
              {saSuppliersMeta && saSuppliersMeta.pages > 1 && (
                <Paginator meta={saSuppliersMeta} page={saSuppliersPage} setPage={setSaSuppliersPage} />
              )}
              {saSuppliers.length === 0 && !loading && <p className="text-center text-gray-500 py-10">No suppliers found.</p>}
            </>
          )}

          {/* ─── PRICE REQUESTS ─── */}
          {view === "supplier_requests" && (
            <>
              <div className="flex items-center justify-between flex-wrap gap-3">
                <h1 className="text-xl font-bold text-white">All Price Requests</h1>
                <button onClick={loadSaRequests} className="text-gray-500 hover:text-gray-300 p-1.5 rounded-lg hover:bg-gray-800"><RefreshCw size={15} /></button>
              </div>
              <div className="flex flex-wrap gap-3">
                <select className="bg-gray-800 border border-gray-700 text-gray-300 text-sm rounded-lg px-3 py-2"
                  value={saRequestsOrgFilter} onChange={(e) => { setSaRequestsOrgFilter(e.target.value); setSaRequestsPage(1); }}>
                  <option value="">All organisations</option>
                  {allOrgs.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
                </select>
              </div>
              <Table
                columns={[
                  { key: "title", label: "Request Title" },
                  { key: "org_name", label: "Organisation", render: (r) => <button className="text-blue-400 hover:underline text-xs" onClick={() => loadOrgDetail(r.org_id)}>{r.org_name}</button> },
                  { key: "status", label: "Status", render: (r) => <Badge text={r.status} colorClass={r.status === "open" ? "bg-green-900 text-green-300" : "bg-gray-700 text-gray-400"} /> },
                  { key: "invites", label: "Suppliers Sent", right: true, render: (r) => <span className="text-gray-300">{r.invites}</span> },
                  { key: "responses", label: "Responses", right: true, render: (r) => <span className={r.responses > 0 ? "text-green-400 font-semibold" : "text-gray-500"}>{r.responses}</span> },
                  { key: "created_at", label: "Created", render: (r) => <span className="text-xs text-gray-400">{fmtDate(r.created_at)}</span> },
                  { key: "_view", label: "", render: (r) => (
                    <button
                      onClick={() => openSupplierRequest(r.id)}
                      className="flex items-center gap-1 text-xs text-gray-400 hover:text-white px-2 py-1 rounded hover:bg-gray-700 transition"
                      title="View full request & responses"
                    >
                      <Eye size={13} /> View
                    </button>
                  )},
                ]}
                rows={saRequests}
              />
              {saRequestsMeta && saRequestsMeta.pages > 1 && (
                <Paginator meta={saRequestsMeta} page={saRequestsPage} setPage={setSaRequestsPage} />
              )}
              {saRequests.length === 0 && !loading && <p className="text-center text-gray-500 py-10">No price requests found.</p>}
            </>
          )}

          {/* ─── AUDIT LOG ─── */}
          {view === "audit" && (
            <>
              <div className="flex items-center justify-between">
                <h1 className="text-xl font-bold text-white">Audit Log</h1>
                <button onClick={loadAuditLog} className="text-gray-500 hover:text-gray-300 p-1.5 rounded-lg hover:bg-gray-800"><RefreshCw size={15} /></button>
              </div>
              <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
                {auditLog.length === 0 ? (
                  <p className="text-center py-12 text-gray-500">No audit entries yet</p>
                ) : (
                  <div className="divide-y divide-gray-700">
                    {auditLog.map((e) => (
                      <div key={e.id} className="px-5 py-3 flex items-start gap-3">
                        <div className={`mt-0.5 p-1.5 rounded-lg shrink-0 ${
                          e.action.includes("suspend") ? "bg-red-900/50 text-red-400" :
                          e.action.includes("payment") ? "bg-green-900/50 text-green-400" :
                          e.action.includes("trial") ? "bg-yellow-900/50 text-yellow-400" :
                          "bg-blue-900/50 text-blue-400"
                        }`}>
                          {ACTION_ICONS[e.action] || <Activity size={13} />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-xs font-mono font-semibold text-gray-200 uppercase">{e.action.replace(/_/g, " ")}</span>
                            <span className="text-xs text-gray-300">·</span>
                            <span className="text-xs text-gray-300 font-medium">{e.org_name}</span>
                          </div>
                          {e.details && (
                            <p className="text-xs text-gray-500 mt-0.5 font-mono">
                              {Object.entries(e.details).map(([k, v]) => `${k}: ${v}`).join(" · ")}
                            </p>
                          )}
                        </div>
                        <div className="text-right shrink-0">
                          <p className="text-[10px] text-gray-500">{fmtDateTime(e.created_at)}</p>
                          <p className="text-[9px] text-gray-600 mt-0.5">{e.performed_by}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <Pagination meta={auditMeta} page={auditPage} setPage={setAuditPage} />
            </>
          )}

          {/* ─── ORG DETAIL ─── */}
          {view === "org_detail" && selectedOrg && (
            <>
              <div className="flex items-center gap-3 flex-wrap">
                <button onClick={() => setView("orgs")} className="text-gray-500 hover:text-gray-300 p-1 rounded"><ChevronLeft size={20} /></button>
                <h1 className="text-xl font-bold text-white">{selectedOrg.name}</h1>
                <Badge text={selectedOrg.plan} colorClass={PLAN_COLORS[selectedOrg.plan] || ""} />
                <Badge text={selectedOrg.plan_status} colorClass={STATUS_COLORS[selectedOrg.plan_status] || ""} />
                {selectedOrg.is_trial && (
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${selectedOrg.days_left_trial <= 3 ? "bg-red-900 text-red-300" : "bg-yellow-900 text-yellow-300"}`}>
                    Trial · {selectedOrg.days_left_trial}d left
                  </span>
                )}
                {selectedOrg.plan_status === "complimentary" && (
                  <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-pink-900 text-pink-300 flex items-center gap-1">
                    <Gift size={10} /> Complimentary{selectedOrg.complimentary_ends_at ? ` · expires ${fmtDate(selectedOrg.complimentary_ends_at)}` : " · indefinite"}
                  </span>
                )}
              </div>

              {/* KPI row */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <StatCard label="Total Invoices" value={selectedOrg.total_invoices} icon={FileText} />
                <StatCard label="Total Quotations" value={selectedOrg.total_quotations} icon={FileText} color="text-blue-400" />
                <StatCard label="Invoices This Month" value={selectedOrg.invoices_this_month} icon={TrendingUp} color="text-yellow-400" />
                <StatCard label="Team Members" value={selectedOrg.users?.length} icon={Users} color="text-purple-400" />
                <StatCard label="Suppliers" value={selectedOrg.total_suppliers ?? 0} icon={Users} color="text-pink-400" />
                <StatCard label="Price Requests" value={selectedOrg.total_supplier_requests ?? 0} icon={FileText} color="text-orange-400" />
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                {/* Plan management */}
                <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
                  <SectionTitle title="Plan Management" />
                  <div className="space-y-1.5">
                    {["free", "starter", "business", "premium"].map((plan) => (
                      <button key={plan} onClick={() => changePlan(selectedOrg.id, plan)}
                        className={`w-full text-left px-3 py-2 rounded-lg text-sm border transition ${
                          selectedOrg.plan === plan && !selectedOrg.is_trial
                            ? "border-green-500 bg-green-900/30 text-white font-medium"
                            : "border-gray-700 text-gray-300 hover:border-green-700 hover:bg-gray-700"
                        }`}>
                        {selectedOrg.plan === plan && !selectedOrg.is_trial && <CheckCircle2 size={11} className="inline mr-1.5 text-green-400" />}
                        {plan.charAt(0).toUpperCase() + plan.slice(1)}
                        <span className="float-right text-gray-500 text-xs">{plan === "free" ? "KES 0" : `KES ${({ starter: "1,500", business: "3,000", premium: "5,500" })[plan]}/mo`}</span>
                      </button>
                    ))}
                  </div>

                  <div className="mt-4 space-y-2">
                    {selectedOrg.plan_status !== "suspended" ? (
                      <button onClick={() => suspendOrg(selectedOrg.id)}
                        className="w-full text-sm text-red-400 border border-red-800 rounded-lg py-2 hover:bg-red-900/30 transition">
                        Suspend Organisation
                      </button>
                    ) : (
                      <button onClick={() => unsuspendOrg(selectedOrg.id)}
                        className="w-full text-sm text-green-400 border border-green-800 rounded-lg py-2 hover:bg-green-900/30 transition">
                        Reactivate Organisation
                      </button>
                    )}
                    <button onClick={() => setExtendModal(true)}
                      className="w-full text-sm text-yellow-400 border border-yellow-800 rounded-lg py-2 hover:bg-yellow-900/30 transition">
                      Extend / Grant Trial
                    </button>
                    <button onClick={() => setPaymentModal(true)}
                      className="w-full text-sm text-blue-400 border border-blue-800 rounded-lg py-2 hover:bg-blue-900/30 transition">
                      Record Manual Payment
                    </button>
                    {selectedOrg.plan_status !== "complimentary" ? (
                      <button onClick={() => setCompModal(true)}
                        className="w-full text-sm text-pink-400 border border-pink-800 rounded-lg py-2 hover:bg-pink-900/30 transition flex items-center justify-center gap-1.5">
                        <Gift size={13} /> Grant Complimentary Access
                      </button>
                    ) : (
                      <button onClick={doRevokeComplimentary}
                        className="w-full text-sm text-gray-400 border border-gray-700 rounded-lg py-2 hover:bg-gray-700 transition">
                        Revoke Complimentary Access
                      </button>
                    )}
                    <button
                      onClick={() => {
                        const admin = selectedOrg.users?.find((u) => u.role === "admin") ?? selectedOrg.users?.[0];
                        setRequestForm({
                          email: selectedOrg.email ?? admin?.email ?? "",
                          name: admin?.display_name ?? selectedOrg.name ?? "",
                          role_hint: "",
                          phone: selectedOrg.phone ?? "",
                        });
                        setWhatsappLink(null);
                        setRequestModal(true);
                        setView("testimonials");
                        setTestimonialTab("pending");
                      }}
                      className="w-full text-sm text-green-400 border border-green-800 rounded-lg py-2 hover:bg-green-900/30 transition flex items-center justify-center gap-1.5"
                    >
                      <MessageSquare size={13} /> Request testimonial
                    </button>
                  </div>
                </div>

                {/* Users */}
                <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
                  <SectionTitle title={`Users (${selectedOrg.users?.length})`} />
                  <div className="space-y-2 max-h-72 overflow-y-auto">
                    {selectedOrg.users?.map((u) => (
                      <div key={u.id} className="flex items-center justify-between py-2 px-2 border-b border-gray-700/50 last:border-0 hover:bg-gray-750 rounded">
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-200 truncate">{u.display_name}</p>
                          <p className="text-xs text-gray-500 truncate">{u.email}</p>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${u.role === "admin" ? "bg-green-900 text-green-400" : "bg-gray-700 text-gray-400"}`}>{u.role}</span>
                          {!u.is_active && <span className="text-[10px] text-red-400">inactive</span>}
                          <button
                            onClick={() => { setUserActionModal({ type: "menu", user: u }); setRoleChangeForm(u.role); }}
                            className="text-gray-400 hover:text-white p-1 rounded hover:bg-gray-700"
                            title="Manage user"
                          >
                            <Shield size={14} />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Details */}
                <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
                  <SectionTitle title="Account Details" />
                  <dl className="space-y-2.5 text-sm">
                    {[
                      ["Email", selectedOrg.email],
                      ["Phone", selectedOrg.phone],
                      ["Joined", fmtDate(selectedOrg.created_at)],
                      ["Billing Start", fmtDate(selectedOrg.billing_cycle_start)],
                      ["Next Billing", fmtDate(selectedOrg.next_billing_date)],
                      ["Trial Ends", selectedOrg.trial_ends_at ? fmtDate(selectedOrg.trial_ends_at) : null],
                      ["Comp. Ends", selectedOrg.complimentary_ends_at ? fmtDate(selectedOrg.complimentary_ends_at) : (selectedOrg.plan_status === "complimentary" ? "Indefinite" : null)],
                      ["Comp. Reason", selectedOrg.complimentary_reason],
                      ["OCR Scans/mo", selectedOrg.ocr_scans_this_month],
                      ["AI Calls/mo", selectedOrg.ai_calls_this_month],
                      ["Quotations/mo", selectedOrg.quotations_this_month],
                    ].filter(([, v]) => v != null).map(([k, v]) => (
                      <div key={k} className="flex justify-between">
                        <dt className="text-gray-500">{k}</dt>
                        <dd className="text-gray-200 text-right">{v || "—"}</dd>
                      </div>
                    ))}
                  </dl>
                </div>
              </div>

              {/* Plan Features */}
              {selectedOrg.plan_features && (
                <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
                  <SectionTitle title={`Plan Features — ${selectedOrg.plan?.charAt(0).toUpperCase()}${selectedOrg.plan?.slice(1)}`} />
                  <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2 mt-2">
                    {[
                      ["Suppliers", "suppliers"],
                      ["Job Profitability", "job_profitability"],
                      ["Expenses", "expenses"],
                      ["Products", "products"],
                      ["Client Portal", "client_portal"],
                      ["Paystack", "paystack"],
                      ["Email Invoices", "email_invoices"],
                      ["Auto Reminders", "auto_reminders"],
                      ["SMS", "sms"],
                      ["Recurring Invoices", "recurring_invoices"],
                      ["eTIMS / KRA", "etims"],
                      ["Audit Logs", "audit_logs"],
                      ["Global Search", "global_search"],
                      ["Priority Support", "priority_support"],
                      ["White Label", "white_label"],
                      ["AI Features", "ai_features"],
                    ].map(([label, key]) => {
                      const enabled = selectedOrg.plan_features[key];
                      return (
                        <div key={key} className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium ${
                          enabled ? "bg-green-900/40 text-green-300 border border-green-800" : "bg-gray-700/50 text-gray-500 border border-gray-700"
                        }`}>
                          <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${enabled ? "bg-green-400" : "bg-gray-600"}`} />
                          {label}
                        </div>
                      );
                    })}
                  </div>
                  <div className="mt-3 flex flex-wrap gap-3 text-xs text-gray-500 border-t border-gray-700 pt-3">
                    <span>Invoices/mo: <span className="text-gray-300">{selectedOrg.plan_features.invoices_per_month === -1 ? "∞" : selectedOrg.plan_features.invoices_per_month}</span></span>
                    <span>Quotations/mo: <span className="text-gray-300">{selectedOrg.plan_features.quotations_per_month === -1 ? "∞" : selectedOrg.plan_features.quotations_per_month}</span></span>
                    <span>Clients: <span className="text-gray-300">{selectedOrg.plan_features.clients === -1 ? "∞" : selectedOrg.plan_features.clients}</span></span>
                    <span>Team: <span className="text-gray-300">{selectedOrg.plan_features.team_members === -1 ? "∞" : selectedOrg.plan_features.team_members}</span></span>
                    <span>OCR/mo: <span className="text-gray-300">{selectedOrg.plan_features.ocr_scans_per_month === -1 ? "∞" : selectedOrg.plan_features.ocr_scans_per_month}</span></span>
                    <span>AI calls/mo: <span className="text-gray-300">{selectedOrg.plan_features.ai_calls_per_month === -1 ? "∞" : selectedOrg.plan_features.ai_calls_per_month}</span></span>
                    <span>Reports: <span className="text-gray-300">{selectedOrg.plan_features.reports_months === -1 ? "∞" : selectedOrg.plan_features.reports_months === 0 ? "Dashboard only" : `${selectedOrg.plan_features.reports_months}mo`}</span></span>
                  </div>
                </div>
              )}

              {/* Payment history for this org */}
              {selectedOrg.recent_payments?.length > 0 && (
                <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
                  <SectionTitle title="Recent Payments" />
                  <Table
                    columns={[
                      { key: "created_at", label: "Date", render: (r) => <span className="text-xs">{fmtDateTime(r.created_at)}</span> },
                      { key: "plan", label: "Plan", render: (r) => <Badge text={r.plan} colorClass={PLAN_COLORS[r.plan] || ""} /> },
                      { key: "payment_method", label: "Method", render: (r) => <Badge text={r.payment_method} colorClass={METHOD_COLORS[r.payment_method] || "bg-gray-700 text-gray-300"} /> },
                      { key: "reference", label: "Reference", render: (r) => <span className="text-xs text-gray-500 font-mono">{r.reference || "—"}</span> },
                      { key: "amount_kes", label: "Amount", right: true, render: (r) => <span className="font-semibold text-green-400">{fmtKES(r.amount_kes)}</span> },
                    ]}
                    rows={selectedOrg.recent_payments}
                  />
                </div>
              )}
            </>
          )}

          {/* ─── TESTIMONIALS ─── */}
          {view === "testimonials" && (() => {
            const tabData = testimonials.filter((t) => t.status === testimonialTab);
            const pendingCount = testimonials.filter((t) => t.status === "pending" && t.submitted_at).length;
            return (
              <div className="space-y-4">
                {/* Header */}
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <SectionTitle title="Testimonials" onRefresh={loadTestimonials} />
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => { setRequestForm({ email: "", name: "", role_hint: "", phone: "" }); setWhatsappLink(null); setRequestModal(true); }}
                      className="flex items-center gap-1.5 bg-green-600 hover:bg-green-500 text-white text-xs font-semibold px-3 py-1.5 rounded-lg"
                    >
                      <Send size={13} /> Request from customer
                    </button>
                    <button
                      onClick={() => { setTestimonialForm({ name: "", role: "", text: "", stars: 5, is_active: true, sort_order: testimonials.length }); setTestimonialModal("create"); }}
                      className="flex items-center gap-1.5 bg-gray-700 hover:bg-gray-600 text-white text-xs font-semibold px-3 py-1.5 rounded-lg"
                    >
                      <PlusCircle size={13} /> Add manually
                    </button>
                  </div>
                </div>

                {/* Tabs */}
                <div className="flex gap-1 bg-gray-800 p-1 rounded-xl w-fit">
                  {[
                    { key: "pending",  label: "Pending",  count: pendingCount },
                    { key: "approved", label: "Approved", count: testimonials.filter((t) => t.status === "approved").length },
                    { key: "rejected", label: "Rejected", count: testimonials.filter((t) => t.status === "rejected").length },
                  ].map(({ key, label, count }) => (
                    <button
                      key={key}
                      onClick={() => setTestimonialTab(key)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition ${testimonialTab === key ? "bg-gray-700 text-white" : "text-gray-500 hover:text-gray-300"}`}
                    >
                      {label}
                      {count > 0 && (
                        <span className={`text-[10px] w-4 h-4 rounded-full flex items-center justify-center font-bold ${key === "pending" ? "bg-amber-500 text-white" : "bg-gray-600 text-gray-300"}`}>
                          {count}
                        </span>
                      )}
                    </button>
                  ))}
                </div>

                {testimonialLoading && <p className="text-gray-500 text-sm">Loading…</p>}

                {!testimonialLoading && tabData.length === 0 && (
                  <div className="text-center py-12 text-gray-500 text-sm">
                    {testimonialTab === "pending"
                      ? "No pending testimonials. Use \"Request from customer\" to send a link."
                      : `No ${testimonialTab} testimonials.`}
                  </div>
                )}

                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {tabData.map((t) => (
                    <div key={t.id} className={`rounded-xl border p-4 space-y-3 ${
                      t.status === "pending" && !t.submitted_at
                        ? "bg-gray-900 border-dashed border-gray-700 opacity-70"
                        : t.status === "approved"
                        ? "bg-gray-800 border-gray-700"
                        : "bg-gray-900 border-gray-800"
                    }`}>
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="text-sm font-semibold text-white truncate">{t.name}</p>
                          <p className="text-xs text-gray-400 truncate">{t.role || <span className="italic text-gray-600">Role not set yet</span>}</p>
                          {t.requested_email && (
                            <p className="text-[10px] text-gray-600 truncate mt-0.5">{t.requested_email}</p>
                          )}
                        </div>

                        {/* Actions per status */}
                        {t.status === "pending" && !t.submitted_at && (
                          <div className="flex items-center gap-1.5 shrink-0">
                            <button
                              title="Resend link"
                              onClick={async () => {
                                try {
                                  const { data } = await superadminResendTestimonial(token, t.id);
                                  flash(data.message ?? "Link resent");
                                  if (data.whatsapp_link) { setWhatsappLink(data.whatsapp_link); setRequestModal(true); }
                                } catch { flash("Error resending", "error"); }
                              }}
                              className="text-gray-500 hover:text-blue-400"
                            ><RefreshCw size={14} /></button>
                            <button title="Delete request" onClick={() => setConfirmModal({ title: "Delete Request", message: `Delete the pending request for "${t.name}"?`, onConfirm: async () => { try { await superadminDeleteTestimonial(token, t.id); flash("Deleted"); loadTestimonials(); } catch { flash("Error", "error"); } } })} className="text-gray-500 hover:text-red-400"><Trash2 size={14} /></button>
                          </div>
                        )}

                        {t.status === "pending" && t.submitted_at && (
                          <div className="flex items-center gap-1.5 shrink-0">
                            <button title="Approve" onClick={async () => { try { await superadminApproveTestimonial(token, t.id); flash("Approved — now live on landing page"); loadTestimonials(); } catch { flash("Error", "error"); } }} className="text-gray-500 hover:text-green-400"><ThumbsUp size={15} /></button>
                            <button title="Reject" onClick={() => { setRejectReason(""); setRejectModal(t.id); }} className="text-gray-500 hover:text-red-400"><ThumbsDown size={15} /></button>
                            <button title="Delete" onClick={() => setConfirmModal({ title: "Delete", message: `Delete this submitted testimonial from "${t.name}"?`, onConfirm: async () => { try { await superadminDeleteTestimonial(token, t.id); flash("Deleted"); loadTestimonials(); } catch { flash("Error", "error"); } } })} className="text-gray-500 hover:text-red-400"><Trash2 size={14} /></button>
                          </div>
                        )}

                        {t.status === "approved" && (
                          <div className="flex items-center gap-1.5 shrink-0">
                            <button title={t.is_active ? "Hide" : "Show"} onClick={async () => { try { await superadminUpdateTestimonial(token, t.id, { name: t.name, role: t.role || "", text: t.text || "", stars: t.stars || 5, is_active: !t.is_active, sort_order: t.sort_order }); loadTestimonials(); } catch { flash("Error", "error"); } }}>
                              {t.is_active ? <ToggleRight size={18} className="text-green-400" /> : <ToggleLeft size={18} className="text-gray-600" />}
                            </button>
                            <button title="Edit" onClick={() => { setTestimonialForm({ name: t.name, role: t.role || "", text: t.text || "", stars: t.stars || 5, is_active: t.is_active, sort_order: t.sort_order }); setTestimonialModal(t); }} className="text-gray-500 hover:text-blue-400"><Edit2 size={14} /></button>
                            <button title="Delete" onClick={() => setConfirmModal({ title: "Delete Testimonial", message: `Remove "${t.name}"'s testimonial?`, onConfirm: async () => { try { await superadminDeleteTestimonial(token, t.id); flash("Deleted"); loadTestimonials(); } catch { flash("Error", "error"); } } })} className="text-gray-500 hover:text-red-400"><Trash2 size={14} /></button>
                          </div>
                        )}

                        {t.status === "rejected" && (
                          <button title="Delete" onClick={() => setConfirmModal({ title: "Delete", message: `Delete this rejected testimonial?`, onConfirm: async () => { try { await superadminDeleteTestimonial(token, t.id); flash("Deleted"); loadTestimonials(); } catch { flash("Error", "error"); } } })} className="text-gray-500 hover:text-red-400 shrink-0"><Trash2 size={14} /></button>
                        )}
                      </div>

                      {/* Stars */}
                      <div className="flex gap-0.5">
                        {Array.from({ length: 5 }).map((_, i) => (
                          <Star key={i} size={12} className={i < (t.stars || 0) ? "fill-amber-400 text-amber-400" : "text-gray-700"} />
                        ))}
                      </div>

                      {/* Text or awaiting */}
                      {t.text
                        ? <p className="text-xs text-gray-300 leading-relaxed line-clamp-4">"{t.text}"</p>
                        : <p className="text-xs text-gray-600 italic">Awaiting customer response…</p>
                      }

                      {/* Footer */}
                      <div className="flex items-center justify-between text-[10px] text-gray-600">
                        {t.status === "approved" && (
                          <>
                            <span>Order: {t.sort_order}</span>
                            <span className={`px-1.5 py-0.5 rounded-full ${t.is_active ? "bg-green-900 text-green-400" : "bg-gray-800 text-gray-500"}`}>
                              {t.is_active ? "visible" : "hidden"}
                            </span>
                          </>
                        )}
                        {t.status === "pending" && t.submitted_at && (
                          <span className="text-amber-500">Submitted · awaiting approval</span>
                        )}
                        {t.status === "pending" && !t.submitted_at && (
                          <span>Request sent · awaiting response</span>
                        )}
                        {t.status === "rejected" && (
                          <span className="text-red-500">{t.rejection_reason ? `Rejected: ${t.rejection_reason}` : "Rejected"}</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })()}

        </div>
      </main>

      {/* ─── Testimonial add/edit modal ─── */}
      {testimonialModal && (
        <Modal
          title={testimonialModal === "create" ? "Add Testimonial" : "Edit Testimonial"}
          onClose={() => setTestimonialModal(null)}
        >
          <div className="space-y-3">
            {[
              { key: "name", label: "Customer Name", placeholder: "Grace Wanjiku" },
              { key: "role", label: "Title / Company", placeholder: "CEO, Wanjiku Consulting" },
            ].map(({ key, label, placeholder }) => (
              <div key={key}>
                <label className="block text-xs text-gray-400 mb-1">{label}</label>
                <input
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-green-500"
                  value={testimonialForm[key]}
                  onChange={(e) => setTestimonialForm({ ...testimonialForm, [key]: e.target.value })}
                  placeholder={placeholder}
                />
              </div>
            ))}
            <div>
              <label className="block text-xs text-gray-400 mb-1">Testimonial Text</label>
              <textarea
                rows={4}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-green-500 resize-none"
                value={testimonialForm.text}
                onChange={(e) => setTestimonialForm({ ...testimonialForm, text: e.target.value })}
                placeholder="What did the customer say?"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-gray-400 mb-1">Stars (1–5)</label>
                <input type="number" min={1} max={5}
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-green-500"
                  value={testimonialForm.stars}
                  onChange={(e) => setTestimonialForm({ ...testimonialForm, stars: Number(e.target.value) })}
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Sort Order</label>
                <input type="number" min={0}
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-green-500"
                  value={testimonialForm.sort_order}
                  onChange={(e) => setTestimonialForm({ ...testimonialForm, sort_order: Number(e.target.value) })}
                />
              </div>
            </div>
            <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
              <input type="checkbox" checked={testimonialForm.is_active} onChange={(e) => setTestimonialForm({ ...testimonialForm, is_active: e.target.checked })} className="accent-green-500" />
              Show on landing page
            </label>
            <div className="flex gap-2 pt-2">
              <button
                onClick={async () => {
                  if (!testimonialForm.name.trim() || !testimonialForm.text.trim()) { flash("Name and text are required", "error"); return; }
                  try {
                    if (testimonialModal === "create") {
                      await superadminCreateTestimonial(token, testimonialForm);
                      flash("Testimonial added");
                    } else {
                      await superadminUpdateTestimonial(token, testimonialModal.id, testimonialForm);
                      flash("Testimonial updated");
                    }
                    setTestimonialModal(null);
                    loadTestimonials();
                  } catch (e) { flash(e.response?.data?.detail ?? "Error saving testimonial", "error"); }
                }}
                className="flex-1 bg-green-600 hover:bg-green-500 text-white font-semibold py-2 rounded-lg text-sm"
              >
                {testimonialModal === "create" ? "Add" : "Save changes"}
              </button>
              <button onClick={() => setTestimonialModal(null)} className="px-4 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm">
                Cancel
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* ─── Request testimonial modal ─── */}
      {requestModal && (
        <Modal title="Request testimonial from customer" onClose={() => { setRequestModal(false); setWhatsappLink(null); }}>
          <div className="space-y-3">
            {whatsappLink ? (
              /* ── Post-send state: show WhatsApp button ── */
              <div className="space-y-4">
                <div className="bg-green-900/30 border border-green-700 rounded-lg px-3 py-3 text-sm text-green-300 flex items-start gap-2">
                  <CheckCircle2 size={15} className="mt-0.5 shrink-0" />
                  <div>
                    <p className="font-semibold">Request sent via email</p>
                    <p className="text-xs text-green-400 mt-0.5">Now send the same link on WhatsApp for a faster response.</p>
                  </div>
                </div>
                <a
                  href={whatsappLink}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center justify-center gap-2 w-full bg-[#25D366] hover:bg-[#1ebe5d] text-white font-semibold py-3 rounded-xl text-sm transition"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
                  Send on WhatsApp
                </a>
                <button onClick={() => { setRequestModal(false); setWhatsappLink(null); }} className="w-full py-2 text-gray-400 text-sm hover:text-white">Done</button>
              </div>
            ) : (
              /* ── Send form ── */
              <>
                <p className="text-xs text-gray-400">
                  The customer receives a unique link via <strong className="text-gray-300">email</strong> and optionally <strong className="text-gray-300">WhatsApp</strong>. They write their feedback and consent — it lands in Pending for your approval before going live.
                </p>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">
                    Customer email
                    <span className="text-gray-600 ml-1">(optional if WhatsApp number provided)</span>
                  </label>
                  <input type="email"
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-green-500"
                    value={requestForm.email}
                    onChange={(e) => setRequestForm({ ...requestForm, email: e.target.value })}
                    placeholder="grace@wanjikuconsulting.co.ke"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Customer name <span className="text-red-400">*</span></label>
                  <input
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-green-500"
                    value={requestForm.name}
                    onChange={(e) => setRequestForm({ ...requestForm, name: e.target.value })}
                    placeholder="Grace Wanjiku"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">
                    WhatsApp number
                    <span className="text-gray-600 ml-1">(optional — e.g. 0722000001 or +254722000001)</span>
                  </label>
                  <input
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-green-500"
                    value={requestForm.phone}
                    onChange={(e) => setRequestForm({ ...requestForm, phone: e.target.value })}
                    placeholder="0722000001"
                  />
                  <p className="text-[10px] text-gray-600 mt-1">A pre-filled WhatsApp link will open for you to send — or it will be sent automatically if your AT WhatsApp is configured.</p>
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Role hint <span className="text-gray-600">(optional)</span></label>
                  <input
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-green-500"
                    value={requestForm.role_hint}
                    onChange={(e) => setRequestForm({ ...requestForm, role_hint: e.target.value })}
                    placeholder="CEO, Wanjiku Consulting"
                  />
                </div>
                <div className="flex gap-2 pt-2">
                  <button
                    onClick={async () => {
                      if (!requestForm.name.trim()) { flash("Customer name is required", "error"); return; }
                      if (!requestForm.email.trim() && !requestForm.phone.trim()) { flash("Provide at least an email or WhatsApp number", "error"); return; }
                      try {
                        const { data } = await superadminRequestTestimonial(token, requestForm);
                        flash(data.message ?? `Request sent to ${requestForm.email}`);
                        setTestimonialTab("pending");
                        loadTestimonials();
                        if (data.whatsapp_link) {
                          setWhatsappLink(data.whatsapp_link);
                        } else {
                          setRequestModal(false);
                          setWhatsappLink(null);
                        }
                        setRequestForm({ email: "", name: "", role_hint: "", phone: "" });
                      } catch (e) { flash(e.response?.data?.detail ?? "Error sending request", "error"); }
                    }}
                    className="flex-1 bg-green-600 hover:bg-green-500 text-white font-semibold py-2 rounded-lg text-sm flex items-center justify-center gap-1.5"
                  >
                    <Send size={13} /> Send request
                  </button>
                  <button onClick={() => setRequestModal(false)} className="px-4 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm">Cancel</button>
                </div>
              </>
            )}
          </div>
        </Modal>
      )}

      {/* ─── Reject testimonial modal ─── */}
      {rejectModal && (
        <Modal title="Reject testimonial" onClose={() => setRejectModal(null)}>
          <div className="space-y-3">
            <p className="text-xs text-gray-400">The testimonial will not appear on the landing page. You can optionally note why.</p>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Reason <span className="text-gray-600">(optional, internal only)</span></label>
              <input
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-red-500"
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="e.g. Off-brand, duplicate, unclear"
              />
            </div>
            <div className="flex gap-2 pt-2">
              <button
                onClick={async () => {
                  try {
                    await superadminRejectTestimonial(token, rejectModal, rejectReason);
                    flash("Testimonial rejected");
                    setRejectModal(null);
                    loadTestimonials();
                  } catch { flash("Error rejecting", "error"); }
                }}
                className="flex-1 bg-red-700 hover:bg-red-600 text-white font-semibold py-2 rounded-lg text-sm"
              >
                Reject
              </button>
              <button onClick={() => setRejectModal(null)} className="px-4 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm">Cancel</button>
            </div>
          </div>
        </Modal>
      )}

      {/* ─── EXTEND TRIAL MODAL ─── */}
      {extendModal && (
        <Modal title="Extend / Grant Trial" onClose={() => setExtendModal(false)}>
          <div className="space-y-4">
            <div>
              <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wide">Days to add</label>
              <input type="number" min="1" max="90"
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-green-500"
                value={extendDays}
                onChange={(e) => setExtendDays(Number(e.target.value))}
              />
            </div>
            <p className="text-xs text-gray-500">Current trial ends: {selectedOrg?.trial_ends_at ? fmtDate(selectedOrg.trial_ends_at) : "no active trial"}</p>
            <div className="flex gap-2">
              <button onClick={() => setExtendModal(false)} className="flex-1 py-2 rounded-lg border border-gray-700 text-gray-400 hover:bg-gray-700 text-sm transition">Cancel</button>
              <button onClick={doExtendTrial} className="flex-1 py-2 rounded-lg bg-yellow-600 hover:bg-yellow-500 text-white text-sm font-semibold transition">Extend Trial</button>
            </div>
          </div>
        </Modal>
      )}

      {/* ─── GRANT COMPLIMENTARY MODAL ─── */}
      {compModal && (
        <Modal title="Grant Complimentary Access" onClose={() => setCompModal(false)}>
          <div className="space-y-3">
            <div className="bg-pink-900/20 border border-pink-800 rounded-lg px-3 py-2 text-xs text-pink-300 flex items-start gap-2">
              <Gift size={13} className="mt-0.5 shrink-0" />
              This grants full tier access at no charge. It will NOT appear in your MRR or revenue figures.
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wide">Plan</label>
              <select
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-pink-500"
                value={compForm.plan}
                onChange={(e) => setCompForm({ ...compForm, plan: e.target.value })}
              >
                {["starter", "business", "premium"].map((p) => <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wide">Reason <span className="text-red-400">*</span></label>
              <input
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-pink-500"
                placeholder="e.g. Beta tester, Partnership, Influencer, Press review"
                value={compForm.reason}
                onChange={(e) => setCompForm({ ...compForm, reason: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wide">Duration (days) — leave blank for indefinite</label>
              <input type="number" min="1"
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-pink-500"
                placeholder="e.g. 30, 90, 365 — blank = forever"
                value={compForm.days}
                onChange={(e) => setCompForm({ ...compForm, days: e.target.value })}
              />
            </div>
            <div className="flex gap-2 pt-1">
              <button onClick={() => setCompModal(false)} className="flex-1 py-2 rounded-lg border border-gray-700 text-gray-400 hover:bg-gray-700 text-sm transition">Cancel</button>
              <button onClick={doGrantComplimentary} className="flex-1 py-2 rounded-lg bg-pink-700 hover:bg-pink-600 text-white text-sm font-semibold transition flex items-center justify-center gap-1.5">
                <Gift size={13} /> Grant Access
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* ─── RECORD PAYMENT MODAL ─── */}
      {paymentModal && (
        <Modal title="Record Manual Payment" onClose={() => setPaymentModal(false)}>
          <div className="space-y-3">
            {[
              { label: "Plan", key: "plan", type: "select", options: ["starter", "business", "premium"] },
              { label: "Amount (KES)", key: "amount_kes", type: "number" },
              { label: "Payment Method", key: "payment_method", type: "select", options: ["manual", "mpesa", "paystack", "bank_transfer", "cash"] },
              { label: "Reference / Receipt No.", key: "reference", type: "text" },
              { label: "Internal Note", key: "note", type: "text" },
            ].map(({ label, key, type, options }) => (
              <div key={key}>
                <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wide">{label}</label>
                {type === "select" ? (
                  <select
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-green-500"
                    value={paymentForm[key]}
                    onChange={(e) => setPaymentForm({ ...paymentForm, [key]: e.target.value })}
                  >
                    {options.map((o) => <option key={o} value={o}>{o}</option>)}
                  </select>
                ) : (
                  <input type={type}
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-green-500"
                    value={paymentForm[key]}
                    onChange={(e) => setPaymentForm({ ...paymentForm, [key]: type === "number" ? Number(e.target.value) : e.target.value })}
                  />
                )}
              </div>
            ))}
            <div className="flex gap-2 pt-1">
              <button onClick={() => setPaymentModal(false)} className="flex-1 py-2 rounded-lg border border-gray-700 text-gray-400 hover:bg-gray-700 text-sm transition">Cancel</button>
              <button onClick={doRecordPayment} className="flex-1 py-2 rounded-lg bg-green-600 hover:bg-green-500 text-white text-sm font-semibold transition">Record & Activate</button>
            </div>
          </div>
        </Modal>
      )}

      {/* ─── USER ACTION MODAL ─── */}
      {userActionModal && (
        <Modal title={`Manage User: ${userActionModal.user.display_name}`} onClose={() => setUserActionModal(null)}>
          <div className="space-y-3">
            <div className="bg-gray-900 rounded-lg p-3 text-xs">
              <p className="text-gray-400">Email</p>
              <p className="text-white font-mono">{userActionModal.user.email}</p>
              <p className="text-gray-400 mt-2">Current Role</p>
              <p className="text-white capitalize">{userActionModal.user.role}</p>
              <p className="text-gray-400 mt-2">Status</p>
              <p className={userActionModal.user.is_active ? "text-green-400" : "text-red-400"}>
                {userActionModal.user.is_active ? "Active" : "Inactive"}
              </p>
            </div>

            {userActionModal.type === "menu" && (
              <div className="space-y-2">
                {!userActionModal.user.google_id && (
                  <button
                    onClick={() => doResetUserPassword(userActionModal.user.id)}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-yellow-400 border border-yellow-800 rounded-lg hover:bg-yellow-900/30 transition"
                  >
                    <Key size={14} /> Reset Password
                  </button>
                )}
                {userActionModal.user.google_id && (
                  <div className="text-xs text-gray-500 px-3 py-2 bg-gray-900 rounded-lg border border-gray-700">
                    <Shield size={12} className="inline mr-1" /> Google OAuth user — password reset not available
                  </div>
                )}
                <button
                  onClick={() => setUserActionModal({ type: "change_role", user: userActionModal.user })}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-blue-400 border border-blue-800 rounded-lg hover:bg-blue-900/30 transition"
                >
                  <Shield size={14} /> Change Role
                </button>
                {userActionModal.user.is_active ? (
                  <button
                    onClick={() => doDeactivateUser(userActionModal.user.id)}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-400 border border-red-800 rounded-lg hover:bg-red-900/30 transition"
                  >
                    <UserX size={14} /> Deactivate User
                  </button>
                ) : (
                  <button
                    onClick={() => doReactivateUser(userActionModal.user.id)}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-green-400 border border-green-800 rounded-lg hover:bg-green-900/30 transition"
                  >
                    <UserCheck size={14} /> Reactivate User
                  </button>
                )}
              </div>
            )}

            {userActionModal.type === "change_role" && (
              <div className="space-y-3">
                <div>
                  <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wide">New Role</label>
                  <select
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                    value={roleChangeForm}
                    onChange={(e) => setRoleChangeForm(e.target.value)}
                  >
                    <option value="admin">Admin</option>
                    <option value="manager">Manager</option>
                    <option value="field_agent">Field Agent</option>
                    <option value="viewer">Viewer</option>
                  </select>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setUserActionModal({ type: "menu", user: userActionModal.user })}
                    className="flex-1 py-2 rounded-lg border border-gray-700 text-gray-400 hover:bg-gray-700 text-sm transition"
                  >
                    Back
                  </button>
                  <button
                    onClick={() => doChangeUserRole(userActionModal.user.id)}
                    className="flex-1 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold transition"
                  >
                    Change Role
                  </button>
                </div>
              </div>
            )}
          </div>
        </Modal>
      )}

      {/* Confirm action modal */}
      {confirmModal && (
        <Modal title={confirmModal.title} onClose={() => setConfirmModal(null)}>
          <p className="text-sm text-gray-300">{confirmModal.message}</p>
          <div className="flex gap-2 mt-5">
            <button
              onClick={() => setConfirmModal(null)}
              className="flex-1 py-2 rounded-lg border border-gray-700 text-gray-400 hover:bg-gray-700 text-sm transition"
            >
              Cancel
            </button>
            <button
              onClick={() => { confirmModal.onConfirm(); setConfirmModal(null); }}
              className="flex-1 py-2 rounded-lg bg-red-600 hover:bg-red-500 text-white text-sm font-semibold transition"
            >
              Confirm
            </button>
          </div>
        </Modal>
      )}

      {/* Supplier request detail modal */}
      {viewingRequest && (
        <Modal title={`Price Request — ${viewingRequest.title}`} onClose={() => setViewingRequest(null)}>
          <div className="space-y-4 max-h-[75vh] overflow-y-auto pr-1">
            <div className="flex items-center gap-3 flex-wrap">
              <span className="text-xs text-gray-400">{viewingRequest.org_name}</span>
              <Badge text={viewingRequest.status} colorClass={viewingRequest.status === "open" ? "bg-green-900 text-green-300" : "bg-gray-700 text-gray-400"} />
            </div>
            {viewingRequest.notes && (
              <p className="text-sm text-gray-400 bg-gray-800 rounded-lg px-3 py-2">{viewingRequest.notes}</p>
            )}

            {/* Items requested */}
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Items Requested</p>
              <table className="w-full text-sm border border-gray-700 rounded-lg overflow-hidden">
                <thead className="bg-gray-800">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs text-gray-400">Description</th>
                    <th className="px-3 py-2 text-right text-xs text-gray-400">Qty</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700">
                  {viewingRequest.items.map((item, i) => (
                    <tr key={i}>
                      <td className="px-3 py-2 text-gray-200">{item.description}</td>
                      <td className="px-3 py-2 text-right text-gray-400">{item.quantity ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Supplier responses */}
            {viewingRequest.invites.length > 0 && (
              <div className="space-y-3">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Supplier Responses</p>
                {viewingRequest.invites.map((inv, i) => {
                  const grandTotal = inv.response_items.reduce((s, r) => s + r.unit_price * (r.quantity || 1), 0);
                  return (
                    <div key={i} className={`rounded-xl border overflow-hidden ${inv.status === "responded" ? "border-green-800" : "border-gray-700"}`}>
                      <div className={`px-3 py-2 flex items-center justify-between ${inv.status === "responded" ? "bg-green-900/40" : "bg-gray-800"}`}>
                        <div>
                          <p className="text-sm font-semibold text-gray-200">{inv.supplier_name}</p>
                          {inv.supplier_company && <p className="text-xs text-gray-500">{inv.supplier_company}</p>}
                        </div>
                        <Badge text={inv.status} colorClass={inv.status === "responded" ? "bg-green-900 text-green-300" : "bg-gray-700 text-gray-400"} />
                      </div>
                      {inv.status === "responded" && inv.response_items.length > 0 && (
                        <table className="w-full text-sm bg-gray-900">
                          <thead className="bg-gray-800">
                            <tr>
                              <th className="px-3 py-1.5 text-left text-xs text-gray-500">Item</th>
                              <th className="px-3 py-1.5 text-right text-xs text-gray-500">Qty</th>
                              <th className="px-3 py-1.5 text-right text-xs text-gray-500">Unit Price</th>
                              <th className="px-3 py-1.5 text-right text-xs text-gray-500">Total</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-800">
                            {inv.response_items.map((r, j) => (
                              <tr key={j}>
                                <td className="px-3 py-2 text-gray-300">{r.description}</td>
                                <td className="px-3 py-2 text-right text-gray-400">{r.quantity ?? "—"}</td>
                                <td className="px-3 py-2 text-right text-gray-300">{fmtKES(r.unit_price)}</td>
                                <td className="px-3 py-2 text-right text-green-400 font-semibold">{fmtKES(r.unit_price * (r.quantity || 1))}</td>
                              </tr>
                            ))}
                          </tbody>
                          <tfoot>
                            <tr className="border-t border-gray-700 bg-gray-800">
                              <td colSpan={3} className="px-3 py-2 text-right text-xs font-bold text-gray-400">Grand Total</td>
                              <td className="px-3 py-2 text-right font-extrabold text-green-400">{fmtKES(grandTotal)}</td>
                            </tr>
                          </tfoot>
                        </table>
                      )}
                      {inv.supplier_notes && (
                        <p className="px-3 py-2 text-xs text-gray-500 italic bg-gray-900">Note: "{inv.supplier_notes}"</p>
                      )}
                      {inv.status === "pending" && (
                        <p className="px-3 py-2 text-xs text-gray-600 bg-gray-900">No response submitted yet.</p>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </Modal>
      )}
    </div>
  );
}
