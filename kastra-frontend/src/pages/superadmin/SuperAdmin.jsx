import { useState, useEffect, useCallback } from "react";
import {
  superadminLogin,
  superadminStats,
  superadminOrgs,
  superadminOrgDetail,
  superadminChangePlan,
  superadminSuspendOrg,
} from "../../api/subscriptions";
import {
  LayoutDashboard, Building2, LogOut, Search, ChevronLeft, ChevronRight,
  TrendingUp, Users, FileText, RefreshCw, AlertCircle, CheckCircle2,
} from "lucide-react";

const PLAN_COLORS = {
  free: "bg-gray-100 text-gray-700",
  starter: "bg-blue-100 text-blue-700",
  business: "bg-green-100 text-green-700",
  premium: "bg-purple-100 text-purple-700",
};

const STATUS_COLORS = {
  active: "bg-emerald-100 text-emerald-700",
  suspended: "bg-red-100 text-red-700",
  cancelled: "bg-gray-100 text-gray-500",
};

function StatCard({ label, value, sub, icon: Icon, color = "text-green-600" }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 flex items-start gap-4">
      <div className={`p-2 rounded-lg bg-gray-50 ${color}`}>
        <Icon size={20} />
      </div>
      <div>
        <p className="text-2xl font-bold text-gray-900">{value?.toLocaleString() ?? "—"}</p>
        <p className="text-sm text-gray-500">{label}</p>
        {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

export default function SuperAdmin() {
  const [token, setToken] = useState(() => sessionStorage.getItem("sa_token") || "");
  const [loginForm, setLoginForm] = useState({ username: "", password: "" });
  const [loginError, setLoginError] = useState("");
  const [loginLoading, setLoginLoading] = useState(false);

  const [view, setView] = useState("dashboard"); // dashboard | orgs | org_detail
  const [stats, setStats] = useState(null);
  const [orgs, setOrgs] = useState([]);
  const [orgsMeta, setOrgsMeta] = useState({ page: 1, pages: 1, total: 0 });
  const [orgsPage, setOrgsPage] = useState(1);
  const [orgsSearch, setOrgsSearch] = useState("");
  const [orgsPlanFilter, setOrgsPlanFilter] = useState("");
  const [selectedOrg, setSelectedOrg] = useState(null);
  const [loading, setLoading] = useState(false);
  const [actionMsg, setActionMsg] = useState("");

  const isAuthed = Boolean(token);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginError("");
    setLoginLoading(true);
    try {
      const { data } = await superadminLogin(loginForm.username, loginForm.password);
      const t = data.access_token;
      sessionStorage.setItem("sa_token", t);
      setToken(t);
    } catch {
      setLoginError("Invalid credentials");
    } finally {
      setLoginLoading(false);
    }
  };

  const logout = () => {
    sessionStorage.removeItem("sa_token");
    setToken("");
    setStats(null);
    setOrgs([]);
  };

  const loadStats = useCallback(async () => {
    if (!token) return;
    try {
      const { data } = await superadminStats(token);
      setStats(data);
    } catch {
      logout();
    }
  }, [token]);

  const loadOrgs = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const { data } = await superadminOrgs(token, {
        page: orgsPage,
        limit: 20,
        ...(orgsSearch ? { search: orgsSearch } : {}),
        ...(orgsPlanFilter ? { plan: orgsPlanFilter } : {}),
      });
      setOrgs(data.data);
      setOrgsMeta(data.meta);
    } catch {
      logout();
    } finally {
      setLoading(false);
    }
  }, [token, orgsPage, orgsSearch, orgsPlanFilter]);

  const loadOrgDetail = async (orgId) => {
    setLoading(true);
    try {
      const { data } = await superadminOrgDetail(token, orgId);
      setSelectedOrg(data);
      setView("org_detail");
    } finally {
      setLoading(false);
    }
  };

  const changePlan = async (orgId, plan) => {
    try {
      await superadminChangePlan(token, orgId, plan);
      setActionMsg(`Plan changed to ${plan}`);
      await loadOrgDetail(orgId);
      setTimeout(() => setActionMsg(""), 3000);
    } catch (e) {
      setActionMsg(e.response?.data?.detail ?? "Error changing plan");
    }
  };

  const suspendOrg = async (orgId) => {
    if (!window.confirm("Suspend this organisation?")) return;
    try {
      await superadminSuspendOrg(token, orgId);
      setActionMsg("Organisation suspended");
      await loadOrgDetail(orgId);
      setTimeout(() => setActionMsg(""), 3000);
    } catch {
      setActionMsg("Error suspending org");
    }
  };

  useEffect(() => {
    if (isAuthed) loadStats();
  }, [isAuthed, loadStats]);

  useEffect(() => {
    if (isAuthed && view === "orgs") loadOrgs();
  }, [isAuthed, view, loadOrgs]);

  if (!isAuthed) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center px-4">
        <div className="w-full max-w-sm">
          <div className="text-center mb-6">
            <img src="/kastra.png" alt="Kastra" className="h-12 w-12 object-contain mx-auto mb-2" />
            <h1 className="text-xl font-bold text-white">Kastra Super Admin</h1>
            <p className="text-gray-400 text-sm">Restricted access</p>
          </div>
          <form onSubmit={handleLogin} className="bg-gray-800 rounded-xl p-6 space-y-4">
            {loginError && (
              <div className="bg-red-900/50 text-red-300 text-sm px-3 py-2 rounded-lg flex items-center gap-2">
                <AlertCircle size={14} /> {loginError}
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Username</label>
              <input
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white placeholder-gray-400 text-sm focus:outline-none focus:border-green-500"
                placeholder="superadmin"
                value={loginForm.username}
                onChange={(e) => setLoginForm({ ...loginForm, username: e.target.value })}
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Password</label>
              <input
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white placeholder-gray-400 text-sm focus:outline-none focus:border-green-500"
                type="password"
                placeholder="••••••••"
                value={loginForm.password}
                onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
                required
              />
            </div>
            <button
              type="submit"
              className="w-full bg-green-600 hover:bg-green-700 text-white font-medium py-2 rounded-lg text-sm transition"
              disabled={loginLoading}
            >
              {loginLoading ? "Signing in…" : "Sign in"}
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <aside className="w-52 bg-gray-900 text-white flex flex-col shrink-0">
        <div className="p-4 border-b border-gray-800">
          <div className="flex items-center gap-2">
            <img src="/kastra.png" alt="" className="h-7 w-7 object-contain" />
            <div>
              <p className="text-sm font-bold">Kastra</p>
              <p className="text-[10px] text-gray-400 uppercase tracking-wider">Super Admin</p>
            </div>
          </div>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          <button
            onClick={() => setView("dashboard")}
            className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition ${view === "dashboard" ? "bg-green-600 text-white" : "text-gray-300 hover:bg-gray-800"}`}
          >
            <LayoutDashboard size={16} /> Dashboard
          </button>
          <button
            onClick={() => setView("orgs")}
            className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition ${view === "orgs" || view === "org_detail" ? "bg-green-600 text-white" : "text-gray-300 hover:bg-gray-800"}`}
          >
            <Building2 size={16} /> Organisations
          </button>
        </nav>
        <div className="p-3 border-t border-gray-800">
          <button onClick={logout} className="w-full flex items-center gap-2 px-3 py-2 text-gray-400 hover:text-white text-sm rounded-lg hover:bg-gray-800">
            <LogOut size={15} /> Sign out
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto">
        <div className="p-6 max-w-5xl mx-auto space-y-6">

          {/* Dashboard */}
          {view === "dashboard" && (
            <>
              <div className="flex items-center justify-between">
                <h1 className="text-xl font-bold text-gray-900">Dashboard</h1>
                <button onClick={loadStats} className="text-gray-400 hover:text-gray-600"><RefreshCw size={16} /></button>
              </div>
              {stats ? (
                <>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                    <StatCard label="Total Organisations" value={stats.total_orgs} icon={Building2} />
                    <StatCard label="Total Users" value={stats.total_users} icon={Users} />
                    <StatCard label="Total Invoices" value={stats.total_invoices} icon={FileText} />
                    <StatCard label="Invoices This Month" value={stats.invoices_this_month} icon={TrendingUp} color="text-blue-600" />
                    <StatCard label="MRR" value={`KES ${stats.mrr_kes?.toLocaleString()}`} icon={TrendingUp} color="text-purple-600" sub="Monthly Recurring Revenue" />
                  </div>
                  <div className="bg-white rounded-xl border border-gray-200 p-5">
                    <h2 className="font-semibold text-gray-700 mb-4">Plan Distribution</h2>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      {Object.entries(stats.plan_distribution || {}).map(([plan, count]) => (
                        <div key={plan} className="text-center bg-gray-50 rounded-lg p-3">
                          <p className="text-2xl font-bold text-gray-900">{count}</p>
                          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${PLAN_COLORS[plan] || "bg-gray-100 text-gray-700"}`}>{plan}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              ) : (
                <div className="text-center py-12 text-gray-400">Loading stats…</div>
              )}
            </>
          )}

          {/* Org list */}
          {view === "orgs" && (
            <>
              <div className="flex items-center justify-between flex-wrap gap-3">
                <h1 className="text-xl font-bold text-gray-900">Organisations</h1>
                <div className="flex items-center gap-2">
                  <div className="relative">
                    <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
                    <input
                      className="border border-gray-200 rounded-lg pl-8 pr-3 py-1.5 text-sm focus:outline-none focus:border-green-500"
                      placeholder="Search name…"
                      value={orgsSearch}
                      onChange={(e) => { setOrgsSearch(e.target.value); setOrgsPage(1); }}
                    />
                  </div>
                  <select
                    className="border border-gray-200 rounded-lg px-2 py-1.5 text-sm focus:outline-none focus:border-green-500"
                    value={orgsPlanFilter}
                    onChange={(e) => { setOrgsPlanFilter(e.target.value); setOrgsPage(1); }}
                  >
                    <option value="">All plans</option>
                    {["free", "starter", "business", "premium"].map((p) => (
                      <option key={p} value={p}>{p}</option>
                    ))}
                  </select>
                </div>
              </div>

              {loading ? (
                <div className="text-center py-12 text-gray-400">Loading…</div>
              ) : (
                <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 border-b border-gray-200">
                      <tr>
                        <th className="text-left px-4 py-3 font-medium text-gray-600">Organisation</th>
                        <th className="text-left px-4 py-3 font-medium text-gray-600">Plan</th>
                        <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
                        <th className="text-right px-4 py-3 font-medium text-gray-600">Users</th>
                        <th className="text-right px-4 py-3 font-medium text-gray-600">Inv/mo</th>
                        <th className="text-right px-4 py-3 font-medium text-gray-600">Joined</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {orgs.map((org) => (
                        <tr
                          key={org.id}
                          className="hover:bg-gray-50 cursor-pointer"
                          onClick={() => loadOrgDetail(org.id)}
                        >
                          <td className="px-4 py-3">
                            <p className="font-medium text-gray-900">{org.name}</p>
                            <p className="text-xs text-gray-400">{org.email}</p>
                          </td>
                          <td className="px-4 py-3">
                            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${PLAN_COLORS[org.plan] || "bg-gray-100"}`}>{org.plan}</span>
                          </td>
                          <td className="px-4 py-3">
                            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${STATUS_COLORS[org.plan_status] || "bg-gray-100"}`}>{org.plan_status}</span>
                          </td>
                          <td className="px-4 py-3 text-right text-gray-600">{org.user_count}</td>
                          <td className="px-4 py-3 text-right text-gray-600">{org.invoices_this_month}</td>
                          <td className="px-4 py-3 text-right text-gray-400 text-xs">{new Date(org.created_at).toLocaleDateString("en-KE")}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {orgs.length === 0 && (
                    <div className="text-center py-12 text-gray-400">No organisations found</div>
                  )}
                </div>
              )}

              {/* Pagination */}
              {orgsMeta.pages > 1 && (
                <div className="flex items-center justify-between text-sm text-gray-500">
                  <span>{orgsMeta.total} total</span>
                  <div className="flex items-center gap-2">
                    <button onClick={() => setOrgsPage((p) => Math.max(1, p - 1))} disabled={orgsPage === 1} className="p-1 rounded hover:bg-gray-100 disabled:opacity-40">
                      <ChevronLeft size={16} />
                    </button>
                    <span>Page {orgsPage} of {orgsMeta.pages}</span>
                    <button onClick={() => setOrgsPage((p) => Math.min(orgsMeta.pages, p + 1))} disabled={orgsPage === orgsMeta.pages} className="p-1 rounded hover:bg-gray-100 disabled:opacity-40">
                      <ChevronRight size={16} />
                    </button>
                  </div>
                </div>
              )}
            </>
          )}

          {/* Org detail */}
          {view === "org_detail" && selectedOrg && (
            <>
              <div className="flex items-center gap-3">
                <button onClick={() => setView("orgs")} className="text-gray-400 hover:text-gray-600"><ChevronLeft size={20} /></button>
                <h1 className="text-xl font-bold text-gray-900">{selectedOrg.name}</h1>
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${PLAN_COLORS[selectedOrg.plan] || ""}`}>{selectedOrg.plan}</span>
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${STATUS_COLORS[selectedOrg.plan_status] || ""}`}>{selectedOrg.plan_status}</span>
              </div>

              {actionMsg && (
                <div className="bg-green-50 text-green-700 text-sm px-3 py-2 rounded-lg flex items-center gap-2">
                  <CheckCircle2 size={14} /> {actionMsg}
                </div>
              )}

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatCard label="Total Invoices" value={selectedOrg.total_invoices} icon={FileText} />
                <StatCard label="Total Quotations" value={selectedOrg.total_quotations} icon={FileText} color="text-blue-600" />
                <StatCard label="Invoices This Month" value={selectedOrg.invoices_this_month} icon={TrendingUp} />
                <StatCard label="Team Members" value={selectedOrg.users?.length} icon={Users} color="text-purple-600" />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Plan management */}
                <div className="bg-white rounded-xl border border-gray-200 p-5">
                  <h2 className="font-semibold text-gray-700 mb-4">Change Plan</h2>
                  <div className="space-y-2">
                    {["free", "starter", "business", "premium"].map((plan) => (
                      <button
                        key={plan}
                        onClick={() => changePlan(selectedOrg.id, plan)}
                        className={`w-full text-left px-3 py-2 rounded-lg text-sm border transition ${selectedOrg.plan === plan ? "border-green-500 bg-green-50 font-medium" : "border-gray-200 hover:border-green-300"}`}
                      >
                        {selectedOrg.plan === plan && <CheckCircle2 size={12} className="inline mr-1.5 text-green-600" />}
                        {plan.charAt(0).toUpperCase() + plan.slice(1)}
                      </button>
                    ))}
                  </div>
                  {selectedOrg.plan_status !== "suspended" && (
                    <button
                      onClick={() => suspendOrg(selectedOrg.id)}
                      className="mt-4 w-full text-sm text-red-600 border border-red-200 rounded-lg py-2 hover:bg-red-50 transition"
                    >
                      Suspend Organisation
                    </button>
                  )}
                </div>

                {/* Users */}
                <div className="bg-white rounded-xl border border-gray-200 p-5">
                  <h2 className="font-semibold text-gray-700 mb-4">Users ({selectedOrg.users?.length})</h2>
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {selectedOrg.users?.map((u) => (
                      <div key={u.id} className="flex items-center justify-between py-1">
                        <div>
                          <p className="text-sm font-medium text-gray-900">{u.display_name}</p>
                          <p className="text-xs text-gray-400">{u.email}</p>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span className="text-xs text-gray-500">{u.role}</span>
                          {!u.is_active && <span className="text-xs text-red-500">inactive</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <h2 className="font-semibold text-gray-700 mb-2">Details</h2>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
                  <div><p className="text-gray-500 text-xs">Email</p><p>{selectedOrg.email || "—"}</p></div>
                  <div><p className="text-gray-500 text-xs">Phone</p><p>{selectedOrg.phone || "—"}</p></div>
                  <div><p className="text-gray-500 text-xs">Joined</p><p>{new Date(selectedOrg.created_at).toLocaleDateString("en-KE")}</p></div>
                  <div><p className="text-gray-500 text-xs">Billing Start</p><p>{selectedOrg.billing_cycle_start ? new Date(selectedOrg.billing_cycle_start).toLocaleDateString("en-KE") : "—"}</p></div>
                  <div><p className="text-gray-500 text-xs">Next Billing</p><p>{selectedOrg.next_billing_date ? new Date(selectedOrg.next_billing_date).toLocaleDateString("en-KE") : "—"}</p></div>
                  <div><p className="text-gray-500 text-xs">OCR Scans/mo</p><p>{selectedOrg.ocr_scans_this_month}</p></div>
                </div>
              </div>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
