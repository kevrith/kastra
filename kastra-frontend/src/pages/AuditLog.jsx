import { useEffect, useState } from "react";
import { getAuditLogs, exportAuditCsv } from "../api/auditLogs";
import { Download, ShieldCheck, Filter } from "lucide-react";
import Spinner from "../components/ui/Spinner";
import Pagination from "../components/ui/Pagination";

const ACTION_COLORS = {
  create: "bg-green-100 text-green-700",
  update: "bg-blue-100 text-blue-700",
  delete: "bg-red-100 text-red-700",
  payment: "bg-purple-100 text-purple-700",
  login: "bg-gray-100 text-gray-700",
};

function fmtTs(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("en-KE", {
    day: "2-digit", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

export default function AuditLog() {
  const [logs, setLogs] = useState([]);
  const [meta, setMeta] = useState(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({ action: "", resource_type: "", from_date: "", to_date: "" });

  const load = (p = page) => {
    setLoading(true);
    const params = { page: p, limit: 50, ...Object.fromEntries(Object.entries(filters).filter(([, v]) => v)) };
    getAuditLogs(params)
      .then(({ data }) => { setLogs(data.data); setMeta(data.meta); })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(1); setPage(1); }, [filters]);
  useEffect(() => { load(page); }, [page]);

  const handleExport = async () => {
    setExporting(true);
    try {
      const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v));
      const { data } = await exportAuditCsv(params);
      const url = URL.createObjectURL(data);
      const a = document.createElement("a");
      a.href = url;
      a.download = "kastra-audit-log.csv";
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="p-4 md:p-6 max-w-6xl mx-auto space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <ShieldCheck size={20} className="text-green-600" />
          <h1 className="text-xl font-bold text-gray-900">Audit Log</h1>
        </div>
        <button className="btn-secondary" onClick={handleExport} disabled={exporting}>
          <Download size={15} /> {exporting ? "Exporting…" : "Export CSV"}
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center bg-white border border-gray-100 rounded-xl p-3 shadow-sm">
        <Filter size={14} className="text-gray-400 shrink-0" />
        <select
          className="input w-auto text-sm"
          value={filters.action}
          onChange={(e) => setFilters((f) => ({ ...f, action: e.target.value }))}
        >
          <option value="">All actions</option>
          {["create", "update", "delete", "payment", "login"].map((a) => (
            <option key={a} value={a}>{a}</option>
          ))}
        </select>
        <select
          className="input w-auto text-sm"
          value={filters.resource_type}
          onChange={(e) => setFilters((f) => ({ ...f, resource_type: e.target.value }))}
        >
          <option value="">All resources</option>
          {["invoice", "quotation", "client", "expense", "auth", "organization"].map((r) => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
        <input
          type="date"
          className="input w-auto text-sm"
          value={filters.from_date}
          onChange={(e) => setFilters((f) => ({ ...f, from_date: e.target.value }))}
          placeholder="From"
        />
        <input
          type="date"
          className="input w-auto text-sm"
          value={filters.to_date}
          onChange={(e) => setFilters((f) => ({ ...f, to_date: e.target.value }))}
          placeholder="To"
        />
        {(filters.action || filters.resource_type || filters.from_date || filters.to_date) && (
          <button
            className="text-xs text-gray-400 hover:text-gray-600 underline"
            onClick={() => setFilters({ action: "", resource_type: "", from_date: "", to_date: "" })}
          >
            Clear
          </button>
        )}
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex h-48 items-center justify-center"><Spinner /></div>
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm min-w-[600px]">
            <thead className="bg-gray-50 text-left text-xs text-gray-500 uppercase tracking-wide">
              <tr>
                <th className="px-4 py-3">Timestamp</th>
                <th className="px-4 py-3">Action</th>
                <th className="px-4 py-3">Resource</th>
                <th className="px-4 py-3">Detail</th>
                <th className="px-4 py-3">IP</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {logs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-gray-400 text-sm">
                    No audit log entries found.
                  </td>
                </tr>
              ) : logs.map((log) => (
                <tr key={log.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2.5 text-xs text-gray-500 whitespace-nowrap">{fmtTs(log.created_at)}</td>
                  <td className="px-4 py-2.5">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold capitalize ${ACTION_COLORS[log.action] ?? "bg-gray-100 text-gray-600"}`}>
                      {log.action}
                    </span>
                  </td>
                  <td className="px-4 py-2.5">
                    <p className="text-xs font-medium text-gray-700 capitalize">{log.resource_type}</p>
                    {log.resource_id && <p className="text-xs text-gray-400 font-mono">{log.resource_id}</p>}
                  </td>
                  <td className="px-4 py-2.5 text-xs text-gray-600 max-w-xs truncate" title={log.detail ?? ""}>
                    {log.detail || "—"}
                  </td>
                  <td className="px-4 py-2.5 text-xs text-gray-400 font-mono">{log.ip_address || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {meta && meta.pages > 1 && (
            <div className="px-4 py-3 border-t border-gray-100">
              <Pagination page={meta.page} pages={meta.pages} onPage={setPage} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
