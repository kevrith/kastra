import { useState, useEffect, useCallback } from "react";
import {
  superadminLogin, superadminStats, superadminRevenue, superadminPayments,
  superadminTrials, superadminAuditLog, superadminOrgs, superadminOrgDetail,
  superadminChangePlan, superadminSuspendOrg, superadminUnsuspendOrg,
  superadminExtendTrial, superadminRecordPayment,
  superadminGrantComplimentary, superadminRevokeComplimentary,
} from "../../api/subscriptions";
import {
  LayoutDashboard, Building2, LogOut, Search, ChevronLeft, ChevronRight,
  TrendingUp, Users, FileText, RefreshCw, AlertCircle, CheckCircle2,
  CreditCard, Clock, Activity, DollarSign, BarChart2, ShieldAlert,
  PlusCircle, X, Gift,
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
    <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
      <table className="w-full text-sm">
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

  // Modal states
  const [extendModal, setExtendModal] = useState(false);
  const [extendDays, setExtendDays] = useState(7);
  const [paymentModal, setPaymentModal] = useState(false);
  const [paymentForm, setPaymentForm] = useState({ plan: "starter", amount_kes: 1500, payment_method: "manual", reference: "", note: "" });
  const [compModal, setCompModal] = useState(false);
  const [compForm, setCompForm] = useState({ plan: "starter", reason: "", days: "" });

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

  // ── Effects ───────────────────────────────────────────────────────────────────
  useEffect(() => { if (isAuthed) loadStats(); }, [isAuthed, loadStats]);
  useEffect(() => { if (isAuthed && view === "revenue") { loadRevenue(); loadPayments(); } }, [isAuthed, view, loadRevenue, loadPayments]);
  useEffect(() => { if (isAuthed && view === "revenue") loadPayments(); }, [paymentsPage]);
  useEffect(() => { if (isAuthed && view === "trials") loadTrials(); }, [isAuthed, view, loadTrials]);
  useEffect(() => { if (isAuthed && view === "audit") loadAuditLog(); }, [isAuthed, view, auditPage, loadAuditLog]);
  useEffect(() => { if (isAuthed && view === "orgs") loadOrgs(); }, [isAuthed, view, loadOrgs]);

  // ── Org actions ───────────────────────────────────────────────────────────────
  const changePlan = async (orgId, plan) => {
    try {
      await superadminChangePlan(token, orgId, plan);
      flash(`Plan changed to ${plan}`);
      await loadOrgDetail(orgId);
    } catch (e) { flash(e.response?.data?.detail ?? "Error changing plan", "error"); }
  };

  const suspendOrg = async (orgId) => {
    if (!window.confirm("Suspend this organisation?")) return;
    try {
      await superadminSuspendOrg(token, orgId);
      flash("Organisation suspended");
      await loadOrgDetail(orgId);
    } catch { flash("Error suspending org", "error"); }
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

  const doRevokeComplimentary = async () => {
    if (!window.confirm("Revoke complimentary access? The org will move to the free plan.")) return;
    try {
      await superadminRevokeComplimentary(token, selectedOrg.id);
      flash("Complimentary access revoked");
      await loadOrgDetail(selectedOrg.id);
    } catch { flash("Error revoking access", "error"); }
  };

  const doRecordPayment = async () => {
    try {
      await superadminRecordPayment(token, selectedOrg.id, paymentForm);
      flash("Payment recorded and plan activated");
      setPaymentModal(false);
      await loadOrgDetail(selectedOrg.id);
    } catch (e) { flash(e.response?.data?.detail ?? "Error recording payment", "error"); }
  };

  // ── Login screen ──────────────────────────────────────────────────────────────
  if (!isAuthed) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4">
        <div className="w-full max-w-sm">
          <div className="text-center mb-8">
            <img src="/kastra.png" alt="Kastra" className="h-12 w-12 object-contain mx-auto mb-3" />
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
    { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
    { id: "revenue",   label: "Revenue",   icon: DollarSign },
    { id: "trials",    label: "Trials",    icon: Clock, badge: stats?.trials_expiring_7d > 0 ? stats.trials_expiring_7d : null },
    { id: "orgs",      label: "Organisations", icon: Building2 },
    { id: "audit",     label: "Audit Log", icon: Activity },
  ];

  return (
    <div className="min-h-screen bg-gray-950 flex">
      {/* Sidebar */}
      <aside className="w-56 bg-gray-900 border-r border-gray-800 flex flex-col shrink-0">
        <div className="p-4 border-b border-gray-800">
          <div className="flex items-center gap-2.5">
            <img src="/kastra.png" alt="" className="h-8 w-8 object-contain" />
            <div>
              <p className="text-sm font-bold text-white">Kastra</p>
              <p className="text-[10px] text-green-500 uppercase tracking-widest">Admin Console</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 p-3 space-y-0.5">
          {navItems.map(({ id, label, icon: Icon, badge }) => (
            <button
              key={id}
              onClick={() => setView(id)}
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
      <main className="flex-1 overflow-auto bg-gray-950">
        <div className="p-6 max-w-6xl mx-auto space-y-6">

          {/* Flash message */}
          {actionMsg.text && (
            <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-xl text-sm font-medium shadow-xl border flex items-center gap-2 ${
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
                    <StatCard label="Monthly Recurring Revenue" value={fmtKES(stats.mrr_kes)} icon={DollarSign} color="text-green-400" />
                    <StatCard label="Annual Run Rate" value={fmtKES(stats.arr_kes)} sub="MRR × 12" icon={TrendingUp} color="text-emerald-400" />
                    <StatCard label="Revenue This Month" value={fmtKES(stats.revenue_this_month_kes)} icon={CreditCard} color="text-blue-400" />
                    <StatCard label="Total Revenue" value={fmtKES(stats.total_revenue_kes)} sub="All payments" icon={BarChart2} color="text-purple-400" />
                  </div>

                  {/* Org & user stats */}
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                    <StatCard label="Total Organisations" value={stats.total_orgs?.toLocaleString()} icon={Building2} color="text-gray-300" />
                    <StatCard label="New This Month" value={stats.new_orgs_this_month} icon={PlusCircle} color="text-cyan-400" />
                    <StatCard label="Active Orgs" value={stats.active_orgs} sub="Created invoice this month" icon={Activity} color="text-yellow-400" />
                    <StatCard label="Total Users" value={stats.total_users?.toLocaleString()} icon={Users} color="text-gray-300" />
                  </div>

                  {/* Trial & health stats */}
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                    <StatCard label="Active Trials" value={stats.trials_active} icon={Clock} color="text-orange-400" />
                    <StatCard label="Trials Expiring (7d)" value={stats.trials_expiring_7d} icon={AlertCircle} color={stats.trials_expiring_7d > 0 ? "text-red-400" : "text-gray-500"} />
                    <StatCard label="Complimentary Accounts" value={stats.complimentary_count} sub="Not in MRR" icon={Gift} color="text-pink-400" />
                    <StatCard label="Suspended Orgs" value={stats.suspended_orgs} icon={ShieldAlert} color={stats.suspended_orgs > 0 ? "text-red-400" : "text-gray-500"} />
                  </div>

                  {/* Plan distribution */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
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

                    <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
                      <SectionTitle title="Trial Distribution" />
                      {Object.entries(stats.trial_distribution ?? {}).every(([, v]) => v === 0) ? (
                        <p className="text-gray-500 text-sm text-center py-6">No active trials</p>
                      ) : (
                        <div className="space-y-2">
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
                      )}
                    </div>
                  </div>
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
                    <div key={t.id} className={`bg-gray-800 border rounded-xl px-5 py-4 flex items-center justify-between gap-4 ${t.days_left <= 3 ? "border-red-700" : t.days_left <= 7 ? "border-yellow-700" : "border-gray-700"}`}>
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
                    { label: "All status", value: "", setter: setOrgsStatusFilter, current: orgsStatusFilter, options: ["active", "suspended"] },
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
                  </div>
                </div>

                {/* Users */}
                <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
                  <SectionTitle title={`Users (${selectedOrg.users?.length})`} />
                  <div className="space-y-2 max-h-72 overflow-y-auto">
                    {selectedOrg.users?.map((u) => (
                      <div key={u.id} className="flex items-center justify-between py-1.5 border-b border-gray-700/50 last:border-0">
                        <div>
                          <p className="text-sm font-medium text-gray-200">{u.display_name}</p>
                          <p className="text-xs text-gray-500">{u.email}</p>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${u.role === "admin" ? "bg-green-900 text-green-400" : "bg-gray-700 text-gray-400"}`}>{u.role}</span>
                          {!u.is_active && <span className="text-[10px] text-red-400">inactive</span>}
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
        </div>
      </main>

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
    </div>
  );
}
