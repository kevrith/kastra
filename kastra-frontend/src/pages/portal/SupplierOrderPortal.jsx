import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { CheckCircle, PackageSearch, Building2, ClipboardList, AlertCircle } from "lucide-react";
import { getSupplierOrder, respondSupplierOrder } from "../../api/purchaseOrders";
import Spinner from "../../components/ui/Spinner";

function ksh(val) {
  return `KSh ${Number(val || 0).toLocaleString("en-KE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

const CLOSED = ["accepted", "receiving", "received", "billed", "paid", "cancelled"];

export default function SupplierOrderPortal() {
  const { token } = useParams();
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [rows, setRows] = useState([]);
  const [notes, setNotes] = useState("");
  const [reply, setReply] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getSupplierOrder(token)
      .then(({ data }) => {
        setOrder(data);
        setNotes(data.supplier_notes ?? "");
        setRows(data.items.map((i) => ({
          id: i.id, description: i.description, unit: i.unit,
          ordered_qty: Number(i.ordered_qty), ordered_unit_price: Number(i.ordered_unit_price),
          confirmed_qty: String(i.confirmed_qty ?? i.ordered_qty),
          confirmed_unit_price: String(i.confirmed_unit_price ?? i.ordered_unit_price),
        })));
        setLoading(false);
      })
      .catch(() => { setNotFound(true); setLoading(false); });
  }, [token]);

  const setRow = (id, k, v) => setRows((prev) => prev.map((r) => (r.id === id ? { ...r, [k]: v } : r)));

  const submit = async () => {
    setSubmitting(true); setError("");
    try {
      await respondSupplierOrder(token, {
        items: rows.map((r) => ({
          id: r.id, confirmed_qty: parseFloat(r.confirmed_qty) || 0,
          confirmed_unit_price: parseFloat(r.confirmed_unit_price) || 0,
        })),
        supplier_notes: notes || null,
        reply: reply || null,
      });
      setDone(true);
    } catch (e) {
      setError(e?.response?.data?.detail ?? "Could not submit. Please try again.");
    } finally { setSubmitting(false); }
  };

  if (loading) return <div className="flex h-screen items-center justify-center"><Spinner size="lg" /></div>;

  if (notFound) return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-12 max-w-sm w-full text-center space-y-4">
        <PackageSearch size={48} className="mx-auto text-gray-300" />
        <h1 className="text-xl font-bold text-gray-800">Link Not Found</h1>
        <p className="text-sm text-gray-500">This order link is invalid or has expired.</p>
      </div>
    </div>
  );

  if (done) return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-12 max-w-sm w-full text-center space-y-4">
        <div className="h-20 w-20 rounded-full bg-green-100 flex items-center justify-center mx-auto">
          <CheckCircle size={40} className="text-green-600" />
        </div>
        <h1 className="text-2xl font-bold text-gray-900">Response Sent!</h1>
        <p className="text-sm text-gray-500">Thank you, <strong>{order.supplier.name}</strong>. Your prices and quantities have been sent to <strong>{order.organization_name}</strong> for approval.</p>
        <p className="text-xs text-gray-400">You can close this page now.</p>
      </div>
    </div>
  );

  const closed = CLOSED.includes(order.status);
  const grandTotal = rows.reduce((s, r) => s + (parseFloat(r.confirmed_qty) || 0) * (parseFloat(r.confirmed_unit_price) || 0), 0);
  const lastReject = [...order.notes_thread].reverse().find((n) => n.author_type === "buyer");

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b border-gray-200 px-4 py-3 md:py-4">
        <div className="max-w-4xl mx-auto flex items-center gap-3">
          <div className="h-9 w-9 md:h-10 md:w-10 rounded-xl bg-green-600 flex items-center justify-center shrink-0">
            <ClipboardList size={18} className="text-white" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="font-bold text-gray-900 text-base md:text-lg leading-tight truncate">{order.organization_name}</p>
            <p className="text-xs text-gray-400">Purchase Order {order.po_id}</p>
          </div>
          {order.status === "supplier_revised" || order.status === "supplier_confirmed" ? (
            <span className="shrink-0 inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full bg-green-100 text-green-700 font-semibold">
              <CheckCircle size={11} /> Response sent
            </span>
          ) : null}
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-3 sm:px-4 py-4 md:py-8 space-y-4">
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4 md:p-6 space-y-3">
          <div className="flex items-start gap-2">
            <Building2 size={15} className="text-gray-400 mt-0.5 shrink-0" />
            <div>
              <p className="text-sm font-semibold text-gray-800">{order.supplier.name}</p>
              {order.supplier.company_name && <p className="text-xs text-gray-400">{order.supplier.company_name}</p>}
            </div>
          </div>
          {order.notes && <p className="text-sm text-gray-600 border-t border-gray-100 pt-3">{order.notes}</p>}
          {order.expected_delivery && (
            <p className="text-xs text-gray-400">Expected delivery: {new Date(order.expected_delivery).toLocaleDateString("en-KE", { day: "2-digit", month: "long", year: "numeric" })}</p>
          )}
        </div>

        {/* Buyer's revision request, if any */}
        {order.status === "rejected" && lastReject && (
          <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 flex gap-3">
            <AlertCircle size={18} className="text-amber-600 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-amber-800">{order.organization_name} asked you to revise:</p>
              <p className="text-sm text-amber-700 mt-0.5">{lastReject.body}</p>
            </div>
          </div>
        )}

        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="px-4 md:px-6 py-3 border-b border-gray-100 bg-gray-50">
            <h3 className="text-sm font-semibold text-gray-700">
              {closed ? "This order has been finalised." : "Confirm the quantity you can supply and your price for each item."}
            </h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-left text-xs text-gray-500 uppercase tracking-wide">
                  <th className="px-4 py-3 font-semibold">Item</th>
                  <th className="px-3 py-3 font-semibold text-center">Ordered</th>
                  <th className="px-3 py-3 font-semibold w-24">Your qty</th>
                  <th className="px-3 py-3 font-semibold w-32">Your price</th>
                  <th className="px-3 py-3 font-semibold text-right w-32">Line total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {rows.map((r) => {
                  const line = (parseFloat(r.confirmed_qty) || 0) * (parseFloat(r.confirmed_unit_price) || 0);
                  return (
                    <tr key={r.id}>
                      <td className="px-4 py-3">
                        <p className="text-gray-900">{r.description}</p>
                        {r.unit && <p className="text-xs text-gray-400">{r.unit}</p>}
                      </td>
                      <td className="px-3 py-3 text-center text-gray-400 whitespace-nowrap">
                        {r.ordered_qty} × {ksh(r.ordered_unit_price)}
                      </td>
                      <td className="px-3 py-3">
                        <input className="input text-sm text-center bg-gray-50" type="number" min="0" step="0.01" disabled={closed}
                          value={r.confirmed_qty} onChange={(e) => setRow(r.id, "confirmed_qty", e.target.value)} />
                      </td>
                      <td className="px-3 py-3">
                        <input className="input text-sm font-semibold" type="number" min="0" step="0.01" disabled={closed}
                          value={r.confirmed_unit_price} onChange={(e) => setRow(r.id, "confirmed_unit_price", e.target.value)} />
                      </td>
                      <td className="px-3 py-3 text-right font-bold text-green-700 whitespace-nowrap">{line > 0 ? ksh(line) : "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
              <tfoot>
                <tr className="border-t-2 border-gray-200 bg-gray-50">
                  <td colSpan={4} className="px-4 py-3 text-sm font-bold text-gray-700 text-right">Your Total</td>
                  <td className="px-3 py-3 text-right text-base font-extrabold text-green-700">{ksh(grandTotal)}</td>
                </tr>
              </tfoot>
            </table>
          </div>

          {!closed && (
            <div className="px-4 md:px-6 pb-5 pt-4 space-y-4 border-t border-gray-100">
              {error && <div className="bg-red-50 text-red-700 text-sm px-4 py-3 rounded-xl">{error}</div>}
              {order.status === "rejected" && (
                <div>
                  <label className="label">Reply to the buyer <span className="text-gray-400 font-normal">(optional)</span></label>
                  <textarea className="input" rows={2} value={reply} onChange={(e) => setReply(e.target.value)} placeholder="Explain your revision…" />
                </div>
              )}
              <div>
                <label className="label">Notes <span className="text-gray-400 font-normal">(optional)</span></label>
                <textarea className="input" rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Availability, lead time, delivery terms…" />
              </div>
              <button className="btn-primary w-full py-3 text-base" disabled={submitting} onClick={submit}>
                {submitting ? "Sending…" : "Confirm & send to buyer"}
              </button>
              <p className="text-xs text-gray-400 text-center">Your response goes to {order.organization_name} for approval. You can re-open this link to update it until they accept.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
