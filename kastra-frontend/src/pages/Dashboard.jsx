import { useEffect, useState } from "react";
import { getDashboardStats } from "../api/dashboard";
import { getCashFlowForecast } from "../api/ai";
import { ksh, date } from "../utils/formatters";
import { statusBadgeClass } from "../utils/formatters";
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { FileText, Receipt, TrendingUp, TrendingDown, Users, DollarSign, Sparkles, RefreshCw, AlertTriangle } from "lucide-react";
import Spinner from "../components/ui/Spinner";
import TeamOverview from "../components/dashboard/TeamOverview";

function CashFlowWidget() {
  const [forecast, setForecast] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await getCashFlowForecast();
      setForecast(data);
    } catch (err) {
      setError(err.response?.data?.detail ?? "Could not generate forecast.");
    } finally {
      setLoading(false);
    }
  };

  if (!forecast && !loading && !error) {
    return (
      <div className="card p-5 flex flex-col items-center justify-center gap-3 text-center min-h-[140px]">
        <div className="h-10 w-10 rounded-xl bg-purple-100 flex items-center justify-center">
          <Sparkles size={20} className="text-purple-600" />
        </div>
        <div>
          <p className="text-sm font-semibold text-gray-800">AI Cash Flow Forecast</p>
          <p className="text-xs text-gray-400 mt-0.5">30-day projection based on your invoices</p>
        </div>
        <button onClick={load} className="btn-secondary text-xs flex items-center gap-1.5">
          <Sparkles size={13} /> Generate Forecast
        </button>
      </div>
    );
  }

  return (
    <div className="card p-5 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-purple-100 flex items-center justify-center">
            <Sparkles size={16} className="text-purple-600" />
          </div>
          <h2 className="text-sm font-semibold text-gray-700">AI Cash Flow Forecast</h2>
        </div>
        <button onClick={load} disabled={loading} className="text-gray-400 hover:text-gray-600 disabled:opacity-40">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {loading && <div className="flex justify-center py-4"><Spinner /></div>}

      {error && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 text-xs text-amber-800">
          {error}
        </div>
      )}

      {forecast && !loading && (
        <>
          <div className="grid grid-cols-3 gap-3 text-center">
            <div className="bg-red-50 rounded-lg p-3">
              <p className="text-xs text-red-500 font-medium">Overdue</p>
              <p className="text-base font-bold text-red-700 mt-0.5">{ksh(forecast.overdue_amount)}</p>
            </div>
            <div className="bg-green-50 rounded-lg p-3">
              <p className="text-xs text-green-600 font-medium">Expected In</p>
              <p className="text-base font-bold text-green-700 mt-0.5">{ksh(forecast.expected_inflow_30d)}</p>
            </div>
            <div className={`rounded-lg p-3 ${forecast.net_30_days >= 0 ? "bg-blue-50" : "bg-orange-50"}`}>
              <p className={`text-xs font-medium ${forecast.net_30_days >= 0 ? "text-blue-600" : "text-orange-600"}`}>Net 30d</p>
              <p className={`text-base font-bold mt-0.5 ${forecast.net_30_days >= 0 ? "text-blue-700" : "text-orange-700"}`}>{ksh(forecast.net_30_days)}</p>
            </div>
          </div>
          <p className="text-xs text-gray-600 leading-relaxed">{forecast.summary}</p>
          {forecast.warnings?.length > 0 && (
            <ul className="space-y-1">
              {forecast.warnings.map((w, i) => (
                <li key={i} className="flex items-start gap-1.5 text-xs text-amber-700">
                  <AlertTriangle size={12} className="mt-0.5 shrink-0" />
                  {w}
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}

function KpiCard({ label, value, icon: Icon, color }) {
  return (
    <div className="card p-5 flex items-center gap-4">
      <div className={`h-11 w-11 rounded-xl flex items-center justify-center ${color}`}>
        <Icon size={20} className="text-white" />
      </div>
      <div>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
        <p className="text-sm text-gray-500">{label}</p>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDashboardStats()
      .then(({ data }) => setStats(data))
      .finally(() => setLoading(false));
  }, []);

  if (loading)
    return <div className="flex h-96 items-center justify-center"><Spinner size="lg" /></div>;

  if (!stats) return null;
  const { kpis, monthly_bars, yearly_trend, top_clients, recent_quotations, recent_invoices } = stats;

  return (
    <div className="p-4 md:p-6 space-y-6 max-w-7xl mx-auto">
      <h1 className="text-xl font-bold text-gray-900">Dashboard</h1>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        <KpiCard label="Pending Quotes" value={kpis.pending_quotations} icon={FileText} color="bg-orange-500" />
        <KpiCard label="Unpaid Invoices" value={kpis.unpaid_invoices} icon={Receipt} color="bg-red-500" />
        <KpiCard label="Active Clients" value={kpis.active_clients} icon={Users} color="bg-blue-500" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <KpiCard label="Monthly Revenue" value={ksh(kpis.monthly_revenue)} icon={TrendingUp} color="bg-green-600" />
        <KpiCard label="Monthly Expenses" value={ksh(kpis.monthly_expenses ?? 0)} icon={TrendingDown} color="bg-red-500" />
        <div className="card p-5 flex items-center gap-4">
          <div className={`h-11 w-11 rounded-xl flex items-center justify-center ${(kpis.monthly_net_profit ?? 0) >= 0 ? "bg-emerald-600" : "bg-red-500"}`}>
            <DollarSign size={20} className="text-white" />
          </div>
          <div>
            <p className={`text-2xl font-bold ${(kpis.monthly_net_profit ?? 0) >= 0 ? "text-emerald-700" : "text-red-600"}`}>{ksh(kpis.monthly_net_profit ?? 0)}</p>
            <p className="text-sm text-gray-500">Net Profit (this month)</p>
          </div>
        </div>
      </div>

      {/* AI Cash Flow Forecast */}
      <CashFlowWidget />

      {/* Charts */}
      <div className="grid md:grid-cols-2 gap-4">
        <div className="card p-4">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Monthly Revenue (Last 6 Months)</h2>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={monthly_bars} barSize={28}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="month" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
              <Tooltip formatter={(v) => ksh(v)} />
              <Bar dataKey="revenue" fill="#16a34a" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card p-4">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Yearly Revenue Trend</h2>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={yearly_trend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="year" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
              <Tooltip formatter={(v) => ksh(v)} />
              <Line type="monotone" dataKey="revenue" stroke="#16a34a" strokeWidth={2} dot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Top Clients + Recent Activity */}
      <div className="grid md:grid-cols-2 gap-4">
        <div className="card">
          <div className="p-4 border-b border-gray-100">
            <h2 className="text-sm font-semibold text-gray-700">Top Clients</h2>
          </div>
          <ul className="divide-y divide-gray-100">
            {top_clients.map((c, i) => (
              <li key={c.id} className="flex items-center gap-3 px-4 py-3">
                <span className="h-6 w-6 rounded-full bg-green-100 text-green-700 text-xs font-bold flex items-center justify-center">
                  {i + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{c.name}</p>
                  <p className="text-xs text-gray-400">{c.invoice_count} invoices</p>
                </div>
                <span className="text-sm font-semibold text-gray-900">{ksh(c.total_billed)}</span>
              </li>
            ))}
            {top_clients.length === 0 && <li className="px-4 py-6 text-sm text-gray-400 text-center">No clients yet</li>}
          </ul>
        </div>

        <div className="card">
          <div className="p-4 border-b border-gray-100">
            <h2 className="text-sm font-semibold text-gray-700">Recent Activity</h2>
          </div>
          <div className="divide-y divide-gray-100">
            {recent_quotations.map((q) => (
              <div key={q.id} className="flex items-center gap-3 px-4 py-3">
                <FileText size={15} className="text-gray-400 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{q.id}</p>
                  <p className="text-xs text-gray-400">{q.client_name} · {q.created_at}</p>
                </div>
                <span className={statusBadgeClass(q.status)}>{q.status}</span>
              </div>
            ))}
            {recent_invoices.map((inv) => (
              <div key={inv.id} className="flex items-center gap-3 px-4 py-3">
                <Receipt size={15} className="text-gray-400 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{inv.id}</p>
                  <p className="text-xs text-gray-400">{inv.client_name} · {inv.created_at}</p>
                </div>
                <span className={statusBadgeClass(inv.payment_status)}>{inv.payment_status}</span>
              </div>
            ))}
            {recent_quotations.length === 0 && recent_invoices.length === 0 && (
              <div className="px-4 py-6 text-sm text-gray-400 text-center">No activity yet</div>
            )}
          </div>
        </div>
      </div>

      {/* Team Overview */}
      <TeamOverview />
    </div>
  );
}
