import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, ArrowRight, Receipt } from "lucide-react";
import { getPurchaseOrders } from "../../api/purchaseOrders";
import { ksh } from "../../utils/formatters";
import Spinner from "../../components/ui/Spinner";
import UpgradeGate from "../../components/ui/UpgradeGate";

export const PO_STATUS = {
  draft: { label: "Draft", cls: "bg-gray-100 text-gray-600" },
  sent: { label: "Sent to supplier", cls: "bg-blue-100 text-blue-700" },
  supplier_confirmed: { label: "Supplier confirmed", cls: "bg-teal-100 text-teal-700" },
  supplier_revised: { label: "Supplier revised", cls: "bg-amber-100 text-amber-700" },
  rejected: { label: "Awaiting revision", cls: "bg-orange-100 text-orange-700" },
  accepted: { label: "Accepted", cls: "bg-green-100 text-green-700" },
  receiving: { label: "Partially received", cls: "bg-indigo-100 text-indigo-700" },
  received: { label: "Received", cls: "bg-green-100 text-green-700" },
  billed: { label: "Billed", cls: "bg-purple-100 text-purple-700" },
  paid: { label: "Paid", cls: "bg-green-600 text-white" },
  cancelled: { label: "Cancelled", cls: "bg-red-100 text-red-600" },
};

export function StatusBadge({ status }) {
  const s = PO_STATUS[status] ?? { label: status, cls: "bg-gray-100 text-gray-600" };
  return <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${s.cls}`}>{s.label}</span>;
}

export default function PurchaseOrders() {
  const navigate = useNavigate();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    const { data } = await getPurchaseOrders({ limit: 100 });
    setRows(data.data ?? []);
    setLoading(false);
  };
  useEffect(() => { load(); }, []);

  return (
    <UpgradeGate
      feature="suppliers"
      title="Purchase Orders"
      description="Order from your suppliers, negotiate prices, receive goods and track what you owe."
      bullets={["Send orders suppliers confirm or revise online", "Get flagged when a price changes", "Receive goods and keep your costs & profit accurate"]}
    >
      <div className="p-4 md:p-6 max-w-4xl mx-auto space-y-5">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Purchase Orders</h1>
            <p className="text-xs text-gray-400">Order from suppliers and track delivery, billing and payments.</p>
          </div>
          <div className="flex gap-2">
            <button className="btn-secondary" onClick={() => navigate("/supplier-bills")}>
              <Receipt size={15} /> Bills
            </button>
            <button className="btn-primary" onClick={() => navigate("/purchase-orders/new")}>
              <Plus size={15} /> New Order
            </button>
          </div>
        </div>

        {loading ? (
          <div className="flex h-48 items-center justify-center"><Spinner size="lg" /></div>
        ) : rows.length === 0 ? (
          <div className="card p-10 text-center text-sm text-gray-400">
            No purchase orders yet. Create one to order from a supplier.
          </div>
        ) : (
          <div className="card divide-y divide-gray-100">
            {rows.map((p) => (
              <div key={p.id}
                className="flex items-center gap-4 px-4 py-3.5 hover:bg-gray-50 cursor-pointer group"
                onClick={() => navigate(`/purchase-orders/${p.id}`)}>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="font-medium text-gray-900">{p.supplier_name}</p>
                    <StatusBadge status={p.status} />
                  </div>
                  <div className="flex gap-4 text-xs text-gray-400 mt-0.5">
                    <span className="font-mono">{p.id}</span>
                    {p.expected_delivery && <span>Due {new Date(p.expected_delivery).toLocaleDateString("en-KE", { day: "2-digit", month: "short" })}</span>}
                    <span>{new Date(p.created_at).toLocaleDateString("en-KE", { day: "2-digit", month: "short", year: "numeric" })}</span>
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <p className="font-semibold text-gray-900">{ksh(p.confirmed_total ?? p.total)}</p>
                  {p.confirmed_total != null && Number(p.confirmed_total) !== Number(p.total) && (
                    <p className="text-xs text-gray-400 line-through">{ksh(p.total)}</p>
                  )}
                </div>
                <ArrowRight size={16} className="text-gray-300 group-hover:text-gray-500 shrink-0" />
              </div>
            ))}
          </div>
        )}
      </div>
    </UpgradeGate>
  );
}
