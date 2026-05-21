import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getInvoices } from "../../api/invoices";
import { ksh, date, statusBadgeClass } from "../../utils/formatters";
import { Receipt } from "lucide-react";
import Spinner from "../../components/ui/Spinner";
import Pagination from "../../components/ui/Pagination";
import EmptyState from "../../components/ui/EmptyState";

const FILTERS = [
  { label: "All", value: "" },
  { label: "Unpaid", value: "unpaid" },
  { label: "Paid", value: "paid" },
  { label: "Overdue", value: "overdue" },
];

export default function InvoiceList() {
  const navigate = useNavigate();
  const [invoices, setInvoices] = useState([]);
  const [meta, setMeta] = useState(null);
  const [page, setPage] = useState(1);
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    const params = { page, limit: 20 };
    if (filter === "overdue") {
      params.overdue = true;
    } else if (filter) {
      params.payment_status = filter;
    }
    getInvoices(params)
      .then(({ data }) => { setInvoices(data.data); setMeta(data.meta); })
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [page, filter]);

  return (
    <div className="p-4 md:p-6 max-w-5xl mx-auto space-y-4">
      <h1 className="text-xl font-bold text-gray-900">Invoices</h1>

      <div className="flex gap-2 flex-wrap">
        {FILTERS.map(({ label, value }) => (
          <button key={value} onClick={() => { setFilter(value); setPage(1); }}
            className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
              filter === value
                ? value === "overdue"
                  ? "bg-red-600 text-white border-red-600"
                  : "bg-green-600 text-white border-green-600"
                : "bg-white text-gray-600 border-gray-300 hover:border-gray-400"
            }`}>
            {label}
          </button>
        ))}
      </div>

      <div className="card overflow-hidden">
        {loading ? (
          <div className="flex h-48 items-center justify-center"><Spinner /></div>
        ) : invoices.length === 0 ? (
          <EmptyState icon={Receipt} title="No invoices" description="Convert an accepted quotation to create an invoice" />
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
                    <th className="px-4 py-3 hidden md:table-cell">Due Date</th>
                    <th className="px-4 py-3 hidden md:table-cell">Created</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {invoices.map((inv) => (
                    <tr key={inv.id} className="hover:bg-gray-50 cursor-pointer"
                      onClick={() => navigate(`/invoices/${inv.id}`)}>
                      <td className="px-4 py-3 font-mono text-xs text-green-700 font-medium">{inv.id}</td>
                      <td className="px-4 py-3 font-medium text-gray-900">{inv.client.name}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className={statusBadgeClass(inv.payment_status)}>{inv.payment_status}</span>
                          {inv.is_overdue && (
                            <span className="badge-overdue">Overdue</span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right font-semibold">{ksh(inv.grand_total)}</td>
                      <td className="px-4 py-3 text-gray-400 hidden md:table-cell">
                        {inv.due_date
                          ? <span className={inv.is_overdue ? "text-red-600 font-medium" : ""}>{date(inv.due_date)}</span>
                          : <span className="text-gray-300">—</span>}
                      </td>
                      <td className="px-4 py-3 text-gray-400 hidden md:table-cell">{date(inv.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination meta={meta} onPageChange={setPage} />
          </>
        )}
      </div>
    </div>
  );
}
