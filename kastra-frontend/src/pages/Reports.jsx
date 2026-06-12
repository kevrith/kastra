import { useEffect, useState } from "react";
import { getIncomeReport, getClientReport, exportCsv, getAgingReport } from "../api/reports";
import { ksh } from "../utils/formatters";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { Download } from "lucide-react";
import Spinner from "../components/ui/Spinner";
import UpgradeGate from "../components/ui/UpgradeGate";

const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

export default function Reports() {
  const currentYear = new Date().getFullYear();
  const [year, setYear] = useState(currentYear);
  const [income, setIncome] = useState([]);
  const [clients, setClients] = useState([]);
  const [aging, setAging] = useState(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);

  const load = () => {
    setLoading(true);
    getAgingReport().then(({ data }) => setAging(data)).catch(() => {});
    Promise.all([getIncomeReport({ year }), getClientReport()])
      .then(([incRes, cliRes]) => {
        const monthMap = Object.fromEntries(incRes.data.data.map((r) => [r.month, r]));
        setIncome(
          Array.from({ length: 12 }, (_, i) => ({
            month: MONTHS[i],
            total: Number(monthMap[i + 1]?.total ?? 0),
            count: monthMap[i + 1]?.count ?? 0,
          }))
        );
        setClients(cliRes.data.data);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [year]);

  const handleExport = async () => {
    setExporting(true);
    try {
      const { data } = await exportCsv(year);
      const url = URL.createObjectURL(data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `kastra-invoices-${year}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  };

  return (
    <UpgradeGate
      feature="reports"
      title="Full Reports"
      description="Get detailed income, expense, and client reports to understand your business performance."
      bullets={["Monthly income & expense breakdown with charts", "Top clients by revenue", "Export to CSV for your accountant"]}
    >
    <div className="p-4 md:p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-xl font-bold text-gray-900">Reports</h1>
        <div className="flex items-center gap-3">
          <select className="input w-auto" value={year} onChange={(e) => setYear(Number(e.target.value))}>
            {[currentYear - 2, currentYear - 1, currentYear].map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
          <button className="btn-secondary" onClick={handleExport} disabled={exporting}>
            <Download size={15} /> {exporting ? "Exporting…" : "Export CSV"}
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex h-48 items-center justify-center"><Spinner /></div>
      ) : (
        <>
          {/* Monthly Income Chart */}
          <div className="card p-4">
            <h2 className="text-sm font-semibold text-gray-700 mb-4">Monthly Revenue — {year}</h2>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={income} barSize={28}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                <Tooltip formatter={(v) => ksh(v)} />
                <Bar dataKey="total" fill="#16a34a" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Monthly Table */}
          <div className="card overflow-hidden">
            <div className="p-4 border-b border-gray-100">
              <h2 className="text-sm font-semibold text-gray-700">Income Breakdown</h2>
            </div>
            <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[320px]">
              <thead className="bg-gray-50 text-left text-xs text-gray-500 uppercase tracking-wide">
                <tr>
                  <th className="px-4 py-3">Month</th>
                  <th className="px-4 py-3 text-right">Invoices Paid</th>
                  <th className="px-4 py-3 text-right">Revenue</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {income.map((row) => (
                  <tr key={row.month} className={row.total > 0 ? "" : "text-gray-400"}>
                    <td className="px-4 py-2.5 font-medium">{row.month}</td>
                    <td className="px-4 py-2.5 text-right">{row.count || "—"}</td>
                    <td className="px-4 py-2.5 text-right font-semibold">{row.total > 0 ? ksh(row.total) : "—"}</td>
                  </tr>
                ))}
                <tr className="bg-gray-50 font-bold">
                  <td className="px-4 py-2.5">Total</td>
                  <td className="px-4 py-2.5 text-right">{income.reduce((s, r) => s + r.count, 0)}</td>
                  <td className="px-4 py-2.5 text-right">{ksh(income.reduce((s, r) => s + r.total, 0))}</td>
                </tr>
              </tbody>
            </table>
            </div>
          </div>

          {/* Debtor Aging */}
          <div className="card overflow-hidden">
            <div className="p-4 border-b border-gray-100">
              <h2 className="text-sm font-semibold text-gray-700">Debtor Aging — Outstanding Balances</h2>
              <p className="text-xs text-gray-400 mt-0.5">Who owes you, and for how long (KES equivalent)</p>
            </div>
            {!aging || aging.data.length === 0 ? (
              <div className="px-4 py-6 text-center text-sm text-gray-400">
                Nothing outstanding — all invoices are paid. 🎉
              </div>
            ) : (
              <div className="overflow-x-auto">
              <table className="w-full text-sm min-w-[560px]">
                <thead className="bg-gray-50 text-left text-xs text-gray-500 uppercase tracking-wide">
                  <tr>
                    <th className="px-4 py-3">Client</th>
                    <th className="px-4 py-3 text-right">Current</th>
                    <th className="px-4 py-3 text-right">1–30 days</th>
                    <th className="px-4 py-3 text-right">31–60 days</th>
                    <th className="px-4 py-3 text-right">61–90 days</th>
                    <th className="px-4 py-3 text-right">90+ days</th>
                    <th className="px-4 py-3 text-right">Total</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {aging.data.map((c) => (
                    <tr key={c.client_id}>
                      <td className="px-4 py-2.5 font-medium text-gray-900">{c.client_name}</td>
                      <td className="px-4 py-2.5 text-right text-gray-600">{c.current > 0 ? ksh(c.current) : "—"}</td>
                      <td className="px-4 py-2.5 text-right text-amber-600">{c.d1_30 > 0 ? ksh(c.d1_30) : "—"}</td>
                      <td className="px-4 py-2.5 text-right text-orange-600">{c.d31_60 > 0 ? ksh(c.d31_60) : "—"}</td>
                      <td className="px-4 py-2.5 text-right text-red-500">{c.d61_90 > 0 ? ksh(c.d61_90) : "—"}</td>
                      <td className="px-4 py-2.5 text-right text-red-700 font-medium">{c.d90_plus > 0 ? ksh(c.d90_plus) : "—"}</td>
                      <td className="px-4 py-2.5 text-right font-semibold">{ksh(c.total)}</td>
                    </tr>
                  ))}
                  <tr className="bg-gray-50 font-bold">
                    <td className="px-4 py-2.5">Total</td>
                    <td className="px-4 py-2.5 text-right">{ksh(aging.totals.current)}</td>
                    <td className="px-4 py-2.5 text-right">{ksh(aging.totals.d1_30)}</td>
                    <td className="px-4 py-2.5 text-right">{ksh(aging.totals.d31_60)}</td>
                    <td className="px-4 py-2.5 text-right">{ksh(aging.totals.d61_90)}</td>
                    <td className="px-4 py-2.5 text-right">{ksh(aging.totals.d90_plus)}</td>
                    <td className="px-4 py-2.5 text-right">{ksh(aging.totals.total)}</td>
                  </tr>
                </tbody>
              </table>
              </div>
            )}
          </div>

          {/* Client Revenue Table */}
          <div className="card overflow-hidden">
            <div className="p-4 border-b border-gray-100">
              <h2 className="text-sm font-semibold text-gray-700">Client Revenue (All Time)</h2>
            </div>
            <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[380px]">
              <thead className="bg-gray-50 text-left text-xs text-gray-500 uppercase tracking-wide">
                <tr>
                  <th className="px-4 py-3">Client</th>
                  <th className="px-4 py-3 text-right">Invoices</th>
                  <th className="px-4 py-3 text-right">Paid</th>
                  <th className="px-4 py-3 text-right">Total Billed</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {clients.map((c) => (
                  <tr key={c.id}>
                    <td className="px-4 py-2.5 font-medium text-gray-900">{c.name}</td>
                    <td className="px-4 py-2.5 text-right text-gray-600">{c.invoice_count}</td>
                    <td className="px-4 py-2.5 text-right text-gray-600">{c.paid_count}</td>
                    <td className="px-4 py-2.5 text-right font-semibold">{ksh(c.total_billed)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          </div>
        </>
      )}
    </div>
    </UpgradeGate>
  );
}
