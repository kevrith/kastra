import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getQuotations } from "../../api/quotations";
import { ksh, date } from "../../utils/formatters";
import { Plus, RefreshCw } from "lucide-react";
import Spinner from "../../components/ui/Spinner";

const COLUMNS = [
  { status: "draft",    label: "Draft",       color: "bg-gray-100 text-gray-600",    dot: "bg-gray-400" },
  { status: "pending",  label: "Sent / Pending", color: "bg-blue-50 text-blue-700",  dot: "bg-blue-500" },
  { status: "accepted", label: "Won ✓",        color: "bg-green-50 text-green-700",  dot: "bg-green-500" },
  { status: "declined", label: "Lost",         color: "bg-red-50 text-red-600",      dot: "bg-red-400" },
];

export default function Pipeline() {
  const navigate = useNavigate();
  const [columns, setColumns] = useState({ draft: [], pending: [], accepted: [], declined: [] });
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const results = await Promise.all(
        COLUMNS.map((c) => getQuotations({ status: c.status, limit: 100 }))
      );
      const next = {};
      COLUMNS.forEach((c, i) => { next[c.status] = results[i].data.data; });
      setColumns(next);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const totalValue = (list) => list.reduce((s, q) => s + Number(q.grand_total), 0);

  return (
    <div className="p-4 md:p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Pipeline</h1>
          <p className="text-xs text-gray-400 mt-0.5">Track every deal from draft to won</p>
        </div>
        <div className="flex gap-2">
          <button className="btn-secondary" onClick={load}><RefreshCw size={14} /></button>
          <button className="btn-primary" onClick={() => navigate("/quotations/new")}>
            <Plus size={15} /> New Quotation
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex h-64 items-center justify-center"><Spinner /></div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 items-start">
          {COLUMNS.map(({ status, label, color, dot }) => {
            const list = columns[status] ?? [];
            return (
              <div key={status} className="bg-gray-50 rounded-xl border border-gray-200 flex flex-col">
                {/* Column header */}
                <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${dot}`} />
                    <span className="text-sm font-semibold text-gray-700">{label}</span>
                    <span className="text-xs bg-white border border-gray-200 text-gray-500 rounded-full px-1.5 py-0.5 font-medium">{list.length}</span>
                  </div>
                  <span className="text-xs font-semibold text-gray-500">{ksh(totalValue(list))}</span>
                </div>

                {/* Cards */}
                <div className="p-3 space-y-2 min-h-[120px]">
                  {list.length === 0 && (
                    <p className="text-xs text-gray-400 text-center py-6">No quotations</p>
                  )}
                  {list.map((q) => (
                    <div
                      key={q.id}
                      onClick={() => navigate(`/quotations/${q.id}`)}
                      className="bg-white border border-gray-200 rounded-lg p-3 cursor-pointer hover:border-green-400 hover:shadow-sm transition-all space-y-1.5"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm font-semibold text-gray-900 leading-tight">
                          {q.client?.name ?? "—"}
                        </p>
                        <span className="text-xs font-bold text-green-700 shrink-0">{ksh(q.grand_total)}</span>
                      </div>
                      {q.project_description && (
                        <p className="text-xs text-gray-500 line-clamp-2">{q.project_description}</p>
                      )}
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-mono text-gray-400">{q.id}</span>
                        <span className="text-[10px] text-gray-400">{date(q.created_at)}</span>
                      </div>
                      {q.expires_at && q.is_expired && (
                        <span className="text-[10px] text-orange-500 font-medium">Expired</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Summary bar */}
      {!loading && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
          {COLUMNS.map(({ status, label, color }) => {
            const list = columns[status] ?? [];
            return (
              <div key={status} className={`rounded-lg px-4 py-3 ${color}`}>
                <p className="text-xs font-medium opacity-75">{label}</p>
                <p className="text-lg font-bold mt-0.5">{ksh(totalValue(list))}</p>
                <p className="text-xs opacity-60">{list.length} deal{list.length !== 1 ? "s" : ""}</p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
