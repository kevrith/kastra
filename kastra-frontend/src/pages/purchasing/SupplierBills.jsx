import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, AlertTriangle, CheckCircle } from "lucide-react";
import { getSupplierBills, getPayablesSummary, recordBillPayment } from "../../api/supplierBills";
import { ksh } from "../../utils/formatters";
import Spinner from "../../components/ui/Spinner";
import Modal from "../../components/ui/Modal";
import UpgradeGate from "../../components/ui/UpgradeGate";

const BILL_STATUS = {
  unpaid: "bg-red-100 text-red-700",
  partial: "bg-amber-100 text-amber-700",
  paid: "bg-green-100 text-green-700",
};

export default function SupplierBills() {
  const navigate = useNavigate();
  const [rows, setRows] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [payTarget, setPayTarget] = useState(null);
  const [payAmount, setPayAmount] = useState("");
  const [busy, setBusy] = useState(false);

  const load = async () => {
    const [{ data }, { data: sum }] = await Promise.all([getSupplierBills({ limit: 100 }), getPayablesSummary()]);
    setRows(data.data ?? []);
    setSummary(sum);
    setLoading(false);
  };
  useEffect(() => { load(); }, []);

  const pay = async () => {
    setBusy(true);
    try {
      await recordBillPayment(payTarget.id, { amount: Number(payAmount) });
      setPayTarget(null); setPayAmount("");
      await load();
    } finally { setBusy(false); }
  };

  return (
    <UpgradeGate feature="suppliers" title="Supplier Bills"
      description="Track what you owe suppliers, due dates and payments."
      bullets={["See outstanding payables and aging", "3-way matched to your orders and deliveries", "Record payments and stay on top of due dates"]}>
      <div className="p-4 md:p-6 max-w-4xl mx-auto space-y-5">
        <button onClick={() => navigate("/purchase-orders")} className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800">
          <ArrowLeft size={15} /> Purchase Orders
        </button>
        <div>
          <h1 className="text-xl font-bold text-gray-900">Supplier Bills</h1>
          <p className="text-xs text-gray-400">Accounts payable — what your business owes suppliers.</p>
        </div>

        {summary && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="card p-3">
              <p className="text-xs text-gray-400">Outstanding</p>
              <p className="text-lg font-bold text-gray-900">{ksh(summary.total_outstanding)}</p>
            </div>
            <div className="card p-3">
              <p className="text-xs text-gray-400">Not yet due</p>
              <p className="text-lg font-bold text-gray-700">{ksh(summary.aging.current)}</p>
            </div>
            <div className="card p-3">
              <p className="text-xs text-gray-400">1–30 days late</p>
              <p className="text-lg font-bold text-amber-600">{ksh(summary.aging.overdue_1_30)}</p>
            </div>
            <div className="card p-3">
              <p className="text-xs text-gray-400">60+ days late</p>
              <p className="text-lg font-bold text-red-600">{ksh(summary.aging.overdue_60_plus)}</p>
            </div>
          </div>
        )}

        {loading ? (
          <div className="flex h-48 items-center justify-center"><Spinner size="lg" /></div>
        ) : rows.length === 0 ? (
          <div className="card p-10 text-center text-sm text-gray-400">No supplier bills yet. Create one from a received purchase order.</div>
        ) : (
          <div className="card divide-y divide-gray-100">
            {rows.map((b) => (
              <div key={b.id} className="flex items-center gap-4 px-4 py-3.5">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="font-medium text-gray-900">{b.supplier_name}</p>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${BILL_STATUS[b.status]}`}>{b.status}</span>
                    {b.match_status === "matched"
                      ? <span className="inline-flex items-center gap-0.5 text-xs text-green-600"><CheckCircle size={11} /> matched</span>
                      : b.match_status === "mismatch"
                      ? <span className="inline-flex items-center gap-0.5 text-xs text-amber-600"><AlertTriangle size={11} /> check totals</span>
                      : null}
                  </div>
                  <div className="flex gap-4 text-xs text-gray-400 mt-0.5">
                    <span className="font-mono">{b.id}</span>
                    {b.due_date && <span>Due {new Date(b.due_date).toLocaleDateString("en-KE", { day: "2-digit", month: "short" })}</span>}
                    {b.days_overdue > 0 && <span className="text-red-500 font-medium">{b.days_overdue}d overdue</span>}
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <p className="font-semibold text-gray-900">{ksh(b.balance)}</p>
                  <p className="text-xs text-gray-400">of {ksh(b.total)}</p>
                </div>
                {b.status !== "paid" && (
                  <button className="btn-secondary text-sm shrink-0" onClick={() => { setPayTarget(b); setPayAmount(String(b.balance)); }}>Pay</button>
                )}
              </div>
            ))}
          </div>
        )}

        <Modal open={!!payTarget} onClose={() => setPayTarget(null)} title="Record payment">
          <div className="space-y-3">
            <p className="text-sm text-gray-500">Paying <span className="font-medium">{payTarget?.supplier_name}</span> — balance {ksh(payTarget?.balance ?? 0)}.</p>
            <div>
              <label className="label">Amount</label>
              <input type="number" min="0" step="0.01" className="input" value={payAmount} onChange={(e) => setPayAmount(e.target.value)} />
            </div>
            <div className="flex justify-end gap-2">
              <button className="btn-secondary" onClick={() => setPayTarget(null)}>Cancel</button>
              <button className="btn-primary" disabled={busy || !payAmount} onClick={pay}>Record payment</button>
            </div>
          </div>
        </Modal>
      </div>
    </UpgradeGate>
  );
}
