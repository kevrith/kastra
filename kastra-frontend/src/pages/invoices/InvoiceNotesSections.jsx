import { useEffect, useState } from "react";
import {
  FileDown, FileMinus, Loader, Plus, ShieldCheck, Trash2, Truck, CheckCircle,
} from "lucide-react";
import Modal from "../../components/ui/Modal";
import ConfirmDialog from "../../components/ui/ConfirmDialog";
import { money, date } from "../../utils/formatters";
import {
  listCreditNotes, createCreditNote, voidCreditNote,
  submitCreditNoteEtims, downloadCreditNotePdf,
} from "../../api/creditNotes";
import {
  listDeliveryNotes, createDeliveryNote, updateDeliveryNote,
  deleteDeliveryNote, downloadDeliveryNotePdf,
} from "../../api/deliveryNotes";

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// ── Credit Notes ────────────────────────────────────────────────────────────

function CreditNoteForm({ invoice, onSave, onClose }) {
  const [reason, setReason] = useState("");
  const [items, setItems] = useState(
    invoice.items.map((i) => ({
      description: i.description,
      quantity: String(i.quantity),
      unit_price: String(i.unit_price),
      vat_exempt: i.vat_exempt ?? false,
      included: true,
    }))
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const setItem = (idx, field, value) =>
    setItems((prev) => prev.map((it, i) => (i === idx ? { ...it, [field]: value } : it)));

  const included = items.filter((i) => i.included);
  const subtotal = included.reduce(
    (s, i) => s + (parseFloat(i.quantity) || 0) * (parseFloat(i.unit_price) || 0), 0
  );

  const handleSave = async () => {
    if (!reason.trim()) { setError("A reason is required — KRA requires it for credit notes."); return; }
    if (included.length === 0) { setError("Select at least one item to credit."); return; }
    setSaving(true);
    setError("");
    try {
      await createCreditNote({
        invoice_id: invoice.id,
        reason: reason.trim(),
        items: included.map((i) => ({
          description: i.description,
          quantity: parseFloat(i.quantity) || 0,
          unit_price: parseFloat(i.unit_price) || 0,
          vat_exempt: i.vat_exempt,
        })),
      });
      onSave();
    } catch (err) {
      setError(err.response?.data?.detail ?? "Failed to create credit note");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      {error && <div className="bg-red-50 text-red-700 text-sm px-3 py-2 rounded-lg">{error}</div>}

      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">Reason for credit *</label>
        <input
          className="input w-full"
          placeholder="e.g. Goods returned, overbilling correction…"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
        />
      </div>

      <div>
        <p className="text-xs font-medium text-gray-600 mb-2">Items to credit (adjust quantities for partial credits)</p>
        <div className="space-y-2">
          {items.map((item, idx) => (
            <div key={idx} className={`flex items-center gap-2 ${item.included ? "" : "opacity-40"}`}>
              <input
                type="checkbox"
                checked={item.included}
                onChange={(e) => setItem(idx, "included", e.target.checked)}
                className="shrink-0"
              />
              <span className="flex-1 text-sm text-gray-700 truncate" title={item.description}>{item.description}</span>
              <input
                type="number" min="0" step="any"
                className="input w-20 text-right"
                value={item.quantity}
                onChange={(e) => setItem(idx, "quantity", e.target.value)}
                disabled={!item.included}
              />
              <input
                type="number" min="0" step="any"
                className="input w-28 text-right"
                value={item.unit_price}
                onChange={(e) => setItem(idx, "unit_price", e.target.value)}
                disabled={!item.included}
              />
            </div>
          ))}
        </div>
      </div>

      <div className="flex justify-between text-sm font-semibold text-gray-800 border-t pt-3">
        <span>Credit subtotal (before VAT)</span>
        <span>{money(subtotal, invoice.currency)}</span>
      </div>

      <div className="flex justify-end gap-2">
        <button className="btn-secondary" onClick={onClose}>Cancel</button>
        <button className="btn-primary" onClick={handleSave} disabled={saving}>
          {saving ? <Loader size={15} className="animate-spin" /> : <FileMinus size={15} />}
          {saving ? "Issuing…" : "Issue Credit Note"}
        </button>
      </div>
    </div>
  );
}

export function CreditNotesSection({ invoice, org, onRefresh }) {
  const [notes, setNotes] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [voidTarget, setVoidTarget] = useState(null);
  const [etimsBusy, setEtimsBusy] = useState(null);
  const [etimsError, setEtimsError] = useState("");

  const loadNotes = () =>
    listCreditNotes({ invoice_id: invoice.id }).then(({ data }) => setNotes(data.data)).catch(() => {});

  useEffect(() => { loadNotes(); }, [invoice.id]);

  const handlePdf = async (cn) => {
    const { data } = await downloadCreditNotePdf(cn.id);
    downloadBlob(data, `${cn.id}.pdf`);
  };

  const handleEtims = async (cn) => {
    setEtimsBusy(cn.id);
    setEtimsError("");
    try {
      await submitCreditNoteEtims(cn.id);
      loadNotes();
    } catch (err) {
      setEtimsError(err.response?.data?.detail ?? "eTIMS submission failed");
    } finally {
      setEtimsBusy(null);
    }
  };

  const handleVoid = async () => {
    await voidCreditNote(voidTarget.id);
    setVoidTarget(null);
    loadNotes();
    onRefresh();
  };

  return (
    <div className="card overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileMinus size={15} className="text-gray-500" />
          <h2 className="text-sm font-semibold text-gray-800">Credit Notes</h2>
        </div>
        <button className="btn-secondary text-xs py-1.5 px-3" onClick={() => setShowForm(true)}>
          <Plus size={13} /> Issue Credit Note
        </button>
      </div>

      {etimsError && <div className="mx-4 mt-3 bg-red-50 text-red-700 text-sm px-3 py-2 rounded-lg">{etimsError}</div>}

      {notes.length === 0 ? (
        <div className="px-4 py-5 text-center text-sm text-gray-400">
          No credit notes. Use one to correct or reverse this invoice — eTIMS invoices can't be edited.
        </div>
      ) : (
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left text-xs text-gray-500 uppercase tracking-wide">
            <tr>
              <th className="px-4 py-2">Number</th>
              <th className="px-4 py-2 hidden sm:table-cell">Reason</th>
              <th className="px-4 py-2">Date</th>
              <th className="px-4 py-2 text-right">Amount</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {notes.map((cn) => (
              <tr key={cn.id}>
                <td className="px-4 py-2.5 font-mono text-xs">
                  {cn.id}
                  {cn.etims_cu_invoice_no && (
                    <span className="ml-1.5 inline-flex items-center gap-0.5 text-[10px] text-green-600">
                      <ShieldCheck size={10} /> eTIMS
                    </span>
                  )}
                </td>
                <td className="px-4 py-2.5 text-gray-500 hidden sm:table-cell truncate max-w-[200px]" title={cn.reason}>{cn.reason}</td>
                <td className="px-4 py-2.5 text-gray-500">{date(cn.created_at)}</td>
                <td className="px-4 py-2.5 text-right font-semibold text-red-600">− {money(cn.grand_total, cn.currency)}</td>
                <td className="px-4 py-2.5">
                  <div className="flex gap-1 justify-end">
                    <button onClick={() => handlePdf(cn)} className="p-1 text-gray-300 hover:text-gray-600" title="Download PDF">
                      <FileDown size={13} />
                    </button>
                    {org?.etims_enabled && !cn.etims_cu_invoice_no && (
                      <button
                        onClick={() => handleEtims(cn)}
                        className="p-1 text-gray-300 hover:text-green-600"
                        title="Submit to KRA eTIMS"
                        disabled={etimsBusy === cn.id}
                      >
                        {etimsBusy === cn.id ? <Loader size={13} className="animate-spin" /> : <ShieldCheck size={13} />}
                      </button>
                    )}
                    {!cn.etims_cu_invoice_no && (
                      <button onClick={() => setVoidTarget(cn)} className="p-1 text-gray-300 hover:text-red-500" title="Void">
                        <Trash2 size={13} />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <Modal open={showForm} onClose={() => setShowForm(false)} title={`Credit Note — ${invoice.id}`} size="lg">
        <CreditNoteForm
          invoice={invoice}
          onSave={() => { setShowForm(false); loadNotes(); onRefresh(); }}
          onClose={() => setShowForm(false)}
        />
      </Modal>

      <ConfirmDialog
        open={!!voidTarget}
        onClose={() => setVoidTarget(null)}
        onConfirm={handleVoid}
        title="Void Credit Note"
        message={`Void ${voidTarget?.id}? The credited amount will be restored to the invoice balance.`}
        danger
      />
    </div>
  );
}

// ── Delivery Notes ──────────────────────────────────────────────────────────

function DeliveryNoteForm({ invoice, onSave, onClose }) {
  const [form, setForm] = useState({
    driver_name: "", vehicle_reg: "",
    delivery_date: new Date().toISOString().slice(0, 10),
    notes: "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSave = async () => {
    setSaving(true);
    setError("");
    try {
      await createDeliveryNote({
        invoice_id: invoice.id,
        driver_name: form.driver_name || null,
        vehicle_reg: form.vehicle_reg || null,
        delivery_date: form.delivery_date ? new Date(form.delivery_date).toISOString() : null,
        notes: form.notes || null,
      });
      onSave();
    } catch (err) {
      setError(err.response?.data?.detail ?? "Failed to create delivery note");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      {error && <div className="bg-red-50 text-red-700 text-sm px-3 py-2 rounded-lg">{error}</div>}
      <p className="text-xs text-gray-500">
        Items are copied from the invoice (quantities only, no prices). The PDF includes signature
        lines for the driver and the receiving party.
      </p>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Driver name</label>
          <input className="input w-full" value={form.driver_name}
            onChange={(e) => setForm({ ...form, driver_name: e.target.value })} />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Vehicle registration</label>
          <input className="input w-full" placeholder="KDA 123A" value={form.vehicle_reg}
            onChange={(e) => setForm({ ...form, vehicle_reg: e.target.value })} />
        </div>
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">Delivery date</label>
        <input type="date" className="input w-full" value={form.delivery_date}
          onChange={(e) => setForm({ ...form, delivery_date: e.target.value })} />
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">Notes</label>
        <textarea className="input w-full" rows={2} value={form.notes}
          onChange={(e) => setForm({ ...form, notes: e.target.value })} />
      </div>
      <div className="flex justify-end gap-2">
        <button className="btn-secondary" onClick={onClose}>Cancel</button>
        <button className="btn-primary" onClick={handleSave} disabled={saving}>
          {saving ? <Loader size={15} className="animate-spin" /> : <Truck size={15} />}
          {saving ? "Creating…" : "Create Delivery Note"}
        </button>
      </div>
    </div>
  );
}

export function DeliveryNotesSection({ invoice }) {
  const [notes, setNotes] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);

  const loadNotes = () =>
    listDeliveryNotes({ invoice_id: invoice.id }).then(({ data }) => setNotes(data.data)).catch(() => {});

  useEffect(() => { loadNotes(); }, [invoice.id]);

  const handlePdf = async (dn) => {
    const { data } = await downloadDeliveryNotePdf(dn.id);
    downloadBlob(data, `${dn.id}.pdf`);
  };

  const handleMarkDelivered = async (dn) => {
    await updateDeliveryNote(dn.id, { status: "delivered" });
    loadNotes();
  };

  const handleDelete = async () => {
    await deleteDeliveryNote(deleteTarget.id);
    setDeleteTarget(null);
    loadNotes();
  };

  return (
    <div className="card overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Truck size={15} className="text-gray-500" />
          <h2 className="text-sm font-semibold text-gray-800">Delivery Notes</h2>
        </div>
        <button className="btn-secondary text-xs py-1.5 px-3" onClick={() => setShowForm(true)}>
          <Plus size={13} /> Delivery Note
        </button>
      </div>

      {notes.length === 0 ? (
        <div className="px-4 py-5 text-center text-sm text-gray-400">
          No delivery notes. Create one for goods deliveries — prices are not shown on the document.
        </div>
      ) : (
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left text-xs text-gray-500 uppercase tracking-wide">
            <tr>
              <th className="px-4 py-2">Number</th>
              <th className="px-4 py-2 hidden sm:table-cell">Driver</th>
              <th className="px-4 py-2">Date</th>
              <th className="px-4 py-2">Status</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {notes.map((dn) => (
              <tr key={dn.id}>
                <td className="px-4 py-2.5 font-mono text-xs">{dn.id}</td>
                <td className="px-4 py-2.5 text-gray-500 hidden sm:table-cell">{dn.driver_name || "—"}</td>
                <td className="px-4 py-2.5 text-gray-500">{date(dn.delivery_date || dn.created_at)}</td>
                <td className="px-4 py-2.5">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs capitalize ${
                    dn.status === "delivered" ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"
                  }`}>
                    {dn.status}
                  </span>
                </td>
                <td className="px-4 py-2.5">
                  <div className="flex gap-1 justify-end">
                    <button onClick={() => handlePdf(dn)} className="p-1 text-gray-300 hover:text-gray-600" title="Download PDF">
                      <FileDown size={13} />
                    </button>
                    {dn.status !== "delivered" && (
                      <button onClick={() => handleMarkDelivered(dn)} className="p-1 text-gray-300 hover:text-green-600" title="Mark delivered">
                        <CheckCircle size={13} />
                      </button>
                    )}
                    <button onClick={() => setDeleteTarget(dn)} className="p-1 text-gray-300 hover:text-red-500" title="Delete">
                      <Trash2 size={13} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <Modal open={showForm} onClose={() => setShowForm(false)} title={`Delivery Note — ${invoice.id}`}>
        <DeliveryNoteForm
          invoice={invoice}
          onSave={() => { setShowForm(false); loadNotes(); }}
          onClose={() => setShowForm(false)}
        />
      </Modal>

      <ConfirmDialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
        title="Delete Delivery Note"
        message={`Delete ${deleteTarget?.id}? This cannot be undone.`}
        danger
      />
    </div>
  );
}
