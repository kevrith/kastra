import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getQuotations, deleteQuotation } from "../../api/quotations";
import { ksh, date, statusBadgeClass } from "../../utils/formatters";
import { Plus, Trash2, FileText } from "lucide-react";
import Spinner from "../../components/ui/Spinner";
import ConfirmDialog from "../../components/ui/ConfirmDialog";
import Pagination from "../../components/ui/Pagination";
import EmptyState from "../../components/ui/EmptyState";

export default function QuotationList() {
  const navigate = useNavigate();
  const [quotations, setQuotations] = useState([]);
  const [meta, setMeta] = useState(null);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [deleteTarget, setDeleteTarget] = useState(null);

  const load = () => {
    setLoading(true);
    getQuotations({ page, limit: 20, status: statusFilter || undefined })
      .then(({ data }) => { setQuotations(data.data); setMeta(data.meta); })
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [page, statusFilter]);

  const handleDelete = async (id) => {
    await deleteQuotation(id);
    load();
  };

  return (
    <div className="p-4 md:p-6 max-w-5xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Quotations</h1>
        <button className="btn-primary" onClick={() => navigate("/quotations/new")}>
          <Plus size={16} /> New Quotation
        </button>
      </div>

      <div className="flex gap-2">
        {["", "draft", "pending", "accepted", "declined"].map((s) => (
          <button key={s} onClick={() => { setStatusFilter(s); setPage(1); }}
            className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
              statusFilter === s
                ? "bg-green-600 text-white border-green-600"
                : "bg-white text-gray-600 border-gray-300 hover:border-gray-400"
            }`}>
            {s || "All"}
          </button>
        ))}
      </div>

      <div className="card overflow-hidden">
        {loading ? (
          <div className="flex h-48 items-center justify-center"><Spinner /></div>
        ) : quotations.length === 0 ? (
          <EmptyState icon={FileText} title="No quotations" description="Create your first quotation"
            action={<button className="btn-primary" onClick={() => navigate("/quotations/new")}><Plus size={16} />New Quotation</button>} />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-left text-xs text-gray-500 uppercase tracking-wide">
                  <tr>
                    <th className="px-4 py-3">ID</th>
                    <th className="px-4 py-3">Client</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3 text-right">Total</th>
                    <th className="px-4 py-3 hidden md:table-cell">Date</th>
                    <th className="px-4 py-3 w-12" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {quotations.map((q) => (
                    <tr key={q.id} className="hover:bg-gray-50 cursor-pointer"
                      onClick={() => navigate(`/quotations/${q.id}`)}>
                      <td className="px-4 py-3 font-mono text-xs text-green-700 font-medium">{q.id}</td>
                      <td className="px-4 py-3 font-medium text-gray-900">{q.client.name}</td>
                      <td className="px-4 py-3"><span className={statusBadgeClass(q.status)}>{q.status}</span></td>
                      <td className="px-4 py-3 text-right font-semibold">{ksh(q.grand_total)}</td>
                      <td className="px-4 py-3 text-gray-400 hidden md:table-cell">{date(q.created_at)}</td>
                      <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                        {!q.converted_to_invoice && (
                          <button className="p-1 text-gray-400 hover:text-red-600"
                            onClick={() => setDeleteTarget(q)}>
                            <Trash2 size={15} />
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination meta={meta} onPageChange={setPage} />
          </>
        )}
      </div>

      <ConfirmDialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => handleDelete(deleteTarget.id)}
        title="Delete Quotation"
        message={`Delete ${deleteTarget?.id}? This cannot be undone.`}
        danger
      />
    </div>
  );
}
