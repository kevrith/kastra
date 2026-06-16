import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft, Send, Check, X, Truck, Receipt, Copy, TrendingUp, TrendingDown,
  MessageSquare, Trash2, Ban,
} from "lucide-react";
import {
  getPurchaseOrder, sendPurchaseOrder, acceptPurchaseOrder, rejectPurchaseOrder,
  cancelPurchaseOrder, addPONote, receiveGoods, deletePurchaseOrder,
} from "../../api/purchaseOrders";
import { createBillFromPO } from "../../api/supplierBills";
import { ksh } from "../../utils/formatters";
import { StatusBadge } from "./PurchaseOrders";
import Spinner from "../../components/ui/Spinner";
import Modal from "../../components/ui/Modal";
import ConfirmDialog from "../../components/ui/ConfirmDialog";

function PriceFlag({ pct }) {
  if (pct == null || pct === 0) return null;
  const up = pct > 0;
  const Icon = up ? TrendingUp : TrendingDown;
  // Up = supplier charging more = bad (red); down = cheaper = good (green)
  return (
    <span className={`inline-flex items-center gap-0.5 text-xs font-medium ${up ? "text-red-600" : "text-green-600"}`}>
      <Icon size={12} /> {up ? "+" : ""}{pct}%
    </span>
  );
}

export default function PurchaseOrderDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [po, setPo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const [rejectOpen, setRejectOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [noteOpen, setNoteOpen] = useState(false);
  const [noteBody, setNoteBody] = useState("");
  const [receiveOpen, setReceiveOpen] = useState(false);
  const [receiveQty, setReceiveQty] = useState({});
  const [billOpen, setBillOpen] = useState(false);
  const [billForm, setBillForm] = useState({ supplier_ref: "", due_date: "", total: "", post_to_expenses: false });
  const [confirmCancel, setConfirmCancel] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const load = async () => {
    const { data } = await getPurchaseOrder(id);
    setPo(data.data);
    setLoading(false);
  };
  useEffect(() => { load(); }, [id]);

  const run = async (fn) => {
    setBusy(true); setErr("");
    try { await fn(); await load(); }
    catch (e) { setErr(e?.response?.data?.detail ?? "Something went wrong."); }
    finally { setBusy(false); }
  };

  const copyLink = () => navigator.clipboard.writeText(`${window.location.origin}/supplier-order/${po.portal_token}`);

  const openReceive = () => {
    const init = {};
    po.items.forEach((i) => {
      const target = Number(i.confirmed_qty ?? i.ordered_qty);
      init[i.id] = Math.max(0, target - Number(i.received_qty));
    });
    setReceiveQty(init); setReceiveOpen(true);
  };

  const submitReceive = () => run(async () => {
    const items = Object.entries(receiveQty)
      .filter(([, q]) => Number(q) > 0)
      .map(([purchase_order_item_id, quantity]) => ({ purchase_order_item_id, quantity: Number(quantity) }));
    if (!items.length) throw { response: { data: { detail: "Enter at least one received quantity." } } };
    await receiveGoods(id, { items });
    setReceiveOpen(false);
  });

  const submitBill = () => run(async () => {
    await createBillFromPO(id, {
      supplier_ref: billForm.supplier_ref || null,
      due_date: billForm.due_date || null,
      total: billForm.total ? Number(billForm.total) : null,
      post_to_expenses: billForm.post_to_expenses,
    });
    setBillOpen(false);
  });

  if (loading) return <div className="flex h-64 items-center justify-center"><Spinner size="lg" /></div>;
  if (!po) return null;

  const negotiable = ["supplier_confirmed", "supplier_revised"].includes(po.status);
  const canReceive = ["accepted", "receiving"].includes(po.status);
  const canBill = ["received", "receiving"].includes(po.status) && !po.bill_id;

  return (
    <div className="p-4 md:p-6 max-w-3xl mx-auto space-y-5">
      <button onClick={() => navigate("/purchase-orders")} className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800">
        <ArrowLeft size={15} /> Purchase Orders
      </button>

      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-xl font-bold text-gray-900">{po.supplier_name}</h1>
            <StatusBadge status={po.status} />
          </div>
          <p className="text-xs text-gray-400 font-mono mt-0.5">{po.id}</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          {po.status === "draft" && (
            <>
              <button className="btn-secondary" onClick={() => navigate(`/purchase-orders/${id}/edit`)}>Edit</button>
              <button className="btn-primary" disabled={busy} onClick={() => run(() => sendPurchaseOrder(id))}><Send size={15} /> Send to supplier</button>
            </>
          )}
          {["sent", "rejected", "supplier_confirmed", "supplier_revised"].includes(po.status) && (
            <button className="btn-secondary" onClick={copyLink}><Copy size={14} /> Copy supplier link</button>
          )}
          {negotiable && (
            <>
              <button className="btn-secondary text-red-600" disabled={busy} onClick={() => setRejectOpen(true)}><X size={15} /> Reject</button>
              <button className="btn-primary" disabled={busy} onClick={() => run(() => acceptPurchaseOrder(id))}><Check size={15} /> Accept prices</button>
            </>
          )}
          {canReceive && <button className="btn-primary" onClick={openReceive}><Truck size={15} /> Receive goods</button>}
          {canBill && <button className="btn-primary" onClick={() => setBillOpen(true)}><Receipt size={15} /> Create bill</button>}
          {po.bill_id && <button className="btn-secondary" onClick={() => navigate("/supplier-bills")}><Receipt size={14} /> View bill</button>}
        </div>
      </div>

      {err && <div className="bg-red-50 text-red-700 text-sm px-4 py-2.5 rounded-lg">{err}</div>}

      {po.notes && <div className="card p-4 text-sm text-gray-600"><span className="text-gray-400">Order notes: </span>{po.notes}</div>}
      {po.supplier_notes && <div className="card p-4 text-sm bg-amber-50 border-amber-100"><span className="font-medium text-amber-800">Supplier note: </span>{po.supplier_notes}</div>}

      {/* Items table with price flags */}
      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500">
            <tr>
              <th className="text-left px-4 py-2 font-medium">Item</th>
              <th className="text-right px-2 py-2 font-medium">Ordered</th>
              <th className="text-right px-2 py-2 font-medium">Confirmed</th>
              <th className="text-right px-4 py-2 font-medium">vs last</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {po.items.map((i) => {
              return (
                <tr key={i.id}>
                  <td className="px-4 py-2.5">
                    <p className="text-gray-900">{i.description}</p>
                    <p className="text-xs text-gray-400">{Number(i.received_qty) > 0 && `Received ${Number(i.received_qty)} • `}{i.unit}</p>
                  </td>
                  <td className="text-right px-2 py-2.5 text-gray-500">
                    {Number(i.ordered_qty)} × {ksh(i.ordered_unit_price)}
                  </td>
                  <td className="text-right px-2 py-2.5">
                    {i.confirmed_unit_price != null ? (
                      <div>
                        <span className="text-gray-900">{Number(i.confirmed_qty)} × {ksh(i.confirmed_unit_price)}</span>
                        <div><PriceFlag pct={i.price_delta_pct} /></div>
                      </div>
                    ) : <span className="text-gray-300">—</span>}
                  </td>
                  <td className="text-right px-4 py-2.5">
                    {i.last_price != null
                      ? <div className="text-xs text-gray-400">was {ksh(i.last_price)}<div><PriceFlag pct={i.history_delta_pct} /></div></div>
                      : <span className="text-xs text-gray-300">first order</span>}
                  </td>
                </tr>
              );
            })}
          </tbody>
          <tfoot className="bg-gray-50 text-sm">
            <tr>
              <td className="px-4 py-2.5 text-gray-500" colSpan={2}>Total</td>
              <td className="text-right px-2 py-2.5 font-bold text-gray-900" colSpan={2}>
                {ksh(po.confirmed_total ?? po.total)}
                {po.confirmed_total != null && Number(po.confirmed_total) !== Number(po.total) &&
                  <span className="ml-2 text-xs text-gray-400 line-through">{ksh(po.total)}</span>}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>

      {/* Negotiation thread */}
      <div className="card p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-gray-900 flex items-center gap-2"><MessageSquare size={15} /> Negotiation</h2>
          <button className="btn-secondary text-sm" onClick={() => setNoteOpen(true)}>Add note</button>
        </div>
        {po.notes_thread.length === 0 ? (
          <p className="text-sm text-gray-400">No messages yet. Reject with a reason or add a note to negotiate.</p>
        ) : (
          <div className="space-y-2">
            {po.notes_thread.map((n) => (
              <div key={n.id} className={`text-sm rounded-lg px-3 py-2 ${n.author_type === "supplier" ? "bg-amber-50" : "bg-gray-50"}`}>
                <div className="flex justify-between text-xs text-gray-400 mb-0.5">
                  <span className="font-medium text-gray-600">{n.author_name} <span className="font-normal">({n.author_type})</span></span>
                  <span>{new Date(n.created_at).toLocaleString("en-KE", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}</span>
                </div>
                <p className="text-gray-700">{n.body}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Receipts */}
      {po.receipts.length > 0 && (
        <div className="card p-4 space-y-2">
          <h2 className="font-semibold text-gray-900 flex items-center gap-2"><Truck size={15} /> Deliveries received</h2>
          {po.receipts.map((g) => (
            <div key={g.id} className="text-sm border-b border-gray-100 pb-2">
              <div className="flex justify-between text-xs text-gray-400">
                <span className="font-mono">{g.id}</span>
                <span>{new Date(g.received_date).toLocaleDateString("en-KE", { day: "2-digit", month: "short", year: "numeric" })}</span>
              </div>
              {g.items.map((it) => (
                <div key={it.id} className="flex justify-between text-gray-600">
                  <span>{it.description}</span>
                  <span>{Number(it.quantity)} × {ksh(it.unit_price)}</span>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}

      {/* Danger actions */}
      <div className="flex justify-end gap-2">
        {po.status === "draft" && (
          <button className="text-sm text-red-500 hover:text-red-700 flex items-center gap-1" onClick={() => setConfirmDelete(true)}>
            <Trash2 size={14} /> Delete
          </button>
        )}
        {!["received", "billed", "paid", "cancelled", "draft"].includes(po.status) && (
          <button className="text-sm text-red-500 hover:text-red-700 flex items-center gap-1" onClick={() => setConfirmCancel(true)}>
            <Ban size={14} /> Cancel order
          </button>
        )}
      </div>

      {/* Reject modal */}
      <Modal open={rejectOpen} onClose={() => setRejectOpen(false)} title="Reject supplier prices">
        <div className="space-y-3">
          <p className="text-sm text-gray-500">Give a reason. The supplier can revise and resubmit.</p>
          <textarea className="input" rows={3} value={rejectReason} onChange={(e) => setRejectReason(e.target.value)} placeholder="e.g. Cement price is 12% above market — please review." />
          <div className="flex justify-end gap-2">
            <button className="btn-secondary" onClick={() => setRejectOpen(false)}>Cancel</button>
            <button className="btn-primary" disabled={busy || !rejectReason.trim()} onClick={() => run(async () => { await rejectPurchaseOrder(id, rejectReason.trim()); setRejectOpen(false); setRejectReason(""); })}>Send back to supplier</button>
          </div>
        </div>
      </Modal>

      {/* Note modal */}
      <Modal open={noteOpen} onClose={() => setNoteOpen(false)} title="Add a note">
        <div className="space-y-3">
          <textarea className="input" rows={3} value={noteBody} onChange={(e) => setNoteBody(e.target.value)} placeholder="Message to keep on this order…" />
          <div className="flex justify-end gap-2">
            <button className="btn-secondary" onClick={() => setNoteOpen(false)}>Cancel</button>
            <button className="btn-primary" disabled={busy || !noteBody.trim()} onClick={() => run(async () => { await addPONote(id, noteBody.trim()); setNoteOpen(false); setNoteBody(""); })}>Add note</button>
          </div>
        </div>
      </Modal>

      {/* Receive modal */}
      <Modal open={receiveOpen} onClose={() => setReceiveOpen(false)} title="Receive goods">
        <div className="space-y-3">
          <p className="text-sm text-gray-500">Enter the quantity that arrived. Partial deliveries are fine — you can receive again later.</p>
          {po.items.map((i) => (
            <div key={i.id} className="flex items-center gap-3">
              <div className="flex-1">
                <p className="text-sm text-gray-800">{i.description}</p>
                <p className="text-xs text-gray-400">Ordered {Number(i.confirmed_qty ?? i.ordered_qty)} • received {Number(i.received_qty)}</p>
              </div>
              <input type="number" min="0" step="0.01" className="input w-24"
                value={receiveQty[i.id] ?? 0}
                onChange={(e) => setReceiveQty({ ...receiveQty, [i.id]: e.target.value })} />
            </div>
          ))}
          <div className="flex justify-end gap-2 pt-1">
            <button className="btn-secondary" onClick={() => setReceiveOpen(false)}>Cancel</button>
            <button className="btn-primary" disabled={busy} onClick={submitReceive}>Confirm receipt</button>
          </div>
        </div>
      </Modal>

      {/* Bill modal */}
      <Modal open={billOpen} onClose={() => setBillOpen(false)} title="Create supplier bill">
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Supplier invoice no.</label>
              <input className="input" value={billForm.supplier_ref} onChange={(e) => setBillForm({ ...billForm, supplier_ref: e.target.value })} placeholder="optional" />
            </div>
            <div>
              <label className="label">Due date</label>
              <input type="date" className="input" value={billForm.due_date} onChange={(e) => setBillForm({ ...billForm, due_date: e.target.value })} />
            </div>
          </div>
          <div>
            <label className="label">Billed total <span className="text-gray-400 font-normal">(blank = received value)</span></label>
            <input type="number" min="0" step="0.01" className="input" value={billForm.total} onChange={(e) => setBillForm({ ...billForm, total: e.target.value })} placeholder="auto from goods received" />
          </div>
          <label className="flex items-start gap-2 text-sm text-gray-600">
            <input type="checkbox" className="mt-0.5" checked={billForm.post_to_expenses} onChange={(e) => setBillForm({ ...billForm, post_to_expenses: e.target.checked })} />
            <span>Post to expenses (P&L). <span className="text-gray-400">Only for non-resale purchases — goods for resale already hit profit via cost of sales.</span></span>
          </label>
          <div className="flex justify-end gap-2">
            <button className="btn-secondary" onClick={() => setBillOpen(false)}>Cancel</button>
            <button className="btn-primary" disabled={busy} onClick={submitBill}>Create bill</button>
          </div>
        </div>
      </Modal>

      <ConfirmDialog open={confirmCancel} onClose={() => setConfirmCancel(false)} danger
        onConfirm={() => run(async () => { await cancelPurchaseOrder(id); setConfirmCancel(false); })}
        title="Cancel order" message="Cancel this purchase order? This cannot be undone." />
      <ConfirmDialog open={confirmDelete} onClose={() => setConfirmDelete(false)} danger
        onConfirm={async () => { await deletePurchaseOrder(id); navigate("/purchase-orders"); }}
        title="Delete draft" message="Delete this draft order?" />
    </div>
  );
}
