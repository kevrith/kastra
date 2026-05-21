import { useEffect, useState } from "react";
import { getRecurring, createRecurring, toggleRecurring, deleteRecurring } from "../../api/recurring";
import { getClients } from "../../api/clients";
import { Plus, Trash2, Power, RefreshCw } from "lucide-react";
import Modal from "../../components/ui/Modal";
import ConfirmDialog from "../../components/ui/ConfirmDialog";
import ProductAutocomplete from "../../components/ui/ProductAutocomplete";
import Spinner from "../../components/ui/Spinner";

function ksh(val) {
  return `KSh ${Number(val).toLocaleString("en-KE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
function fmtDate(iso) {
  return new Date(iso).toLocaleDateString("en-KE", { day: "2-digit", month: "short", year: "numeric" });
}

const emptyItem = () => ({ description: "", quantity: "1", unit_price: "" });
const FREQUENCIES = ["weekly", "monthly", "quarterly", "yearly"];

export default function RecurringInvoices() {
  const [rows, setRows] = useState([]);
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ client_id: "", frequency: "monthly", next_run_at: "", items: [emptyItem()] });
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);

  const load = async () => {
    setLoading(true);
    const [rRes, cRes] = await Promise.all([getRecurring(), getClients({ limit: 100 })]);
    setRows(rRes.data);
    setClients(cRes.data.data);
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const setItem = (i, field, value) =>
    setForm((f) => ({ ...f, items: f.items.map((it, idx) => idx === i ? { ...it, [field]: value } : it) }));

  const subtotalFor = (items) => items.reduce((s, it) => s + (parseFloat(it.quantity) || 0) * (parseFloat(it.unit_price) || 0), 0);

  const handleSave = async () => {
    if (!form.client_id || !form.next_run_at) return;
    setSaving(true);
    try {
      await createRecurring({
        client_id: form.client_id,
        frequency: form.frequency,
        next_run_at: new Date(form.next_run_at).toISOString(),
        items: form.items.map((it) => ({ description: it.description, quantity: parseFloat(it.quantity), unit_price: parseFloat(it.unit_price) })),
      });
      setShowModal(false);
      load();
    } finally {
      setSaving(false);
    }
  };

  const handleToggle = async (id) => {
    await toggleRecurring(id);
    load();
  };

  return (
    <div className="p-4 md:p-6 max-w-4xl mx-auto space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Recurring Invoices</h1>
          <p className="text-xs text-gray-400">Invoices generated automatically on a schedule.</p>
        </div>
        <button className="btn-primary" onClick={() => { setForm({ client_id: "", frequency: "monthly", next_run_at: new Date().toISOString().slice(0, 10), items: [emptyItem()] }); setShowModal(true); }}>
          <Plus size={16} /> New Recurring
        </button>
      </div>

      {loading ? (
        <div className="flex h-48 items-center justify-center"><Spinner size="lg" /></div>
      ) : rows.length === 0 ? (
        <div className="card p-10 text-center text-sm text-gray-400">No recurring invoices. Create one to automate monthly billing.</div>
      ) : (
        <div className="space-y-3">
          {rows.map((r) => {
            const sub = subtotalFor(r.items);
            const total = sub * 1.16;
            return (
              <div key={r.id} className="card p-4 flex items-center gap-4">
                <div className={`h-10 w-10 rounded-xl flex items-center justify-center shrink-0 ${r.is_active ? "bg-green-100" : "bg-gray-100"}`}>
                  <RefreshCw size={18} className={r.is_active ? "text-green-600" : "text-gray-400"} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-gray-900">{r.client_name}</p>
                  <p className="text-xs text-gray-400 capitalize">{r.frequency} · Next: {fmtDate(r.next_run_at)}{r.last_run_at ? ` · Last: ${fmtDate(r.last_run_at)}` : ""}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{r.items.length} line item{r.items.length !== 1 ? "s" : ""}</p>
                </div>
                <div className="text-right shrink-0">
                  <p className="font-bold text-gray-900">{ksh(total)}</p>
                  <span className={`text-xs font-medium ${r.is_active ? "text-green-600" : "text-gray-400"}`}>{r.is_active ? "Active" : "Paused"}</span>
                </div>
                <div className="flex gap-2 shrink-0">
                  <button onClick={() => handleToggle(r.id)} title={r.is_active ? "Pause" : "Resume"} className={`p-2 rounded-lg border transition-colors ${r.is_active ? "border-green-200 text-green-600 hover:bg-green-50" : "border-gray-200 text-gray-400 hover:bg-gray-50"}`}>
                    <Power size={14} />
                  </button>
                  <button onClick={() => setDeleteTarget(r)} className="p-2 rounded-lg border border-gray-200 text-gray-400 hover:text-red-500 hover:border-red-200 transition-colors">
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create Modal */}
      <Modal open={showModal} onClose={() => setShowModal(false)} title="New Recurring Invoice" size="md">
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Client *</label>
              <select className="input" value={form.client_id} onChange={(e) => setForm((f) => ({ ...f, client_id: e.target.value }))}>
                <option value="">Select…</option>
                {clients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Frequency</label>
              <select className="input capitalize" value={form.frequency} onChange={(e) => setForm((f) => ({ ...f, frequency: e.target.value }))}>
                {FREQUENCIES.map((fr) => <option key={fr} value={fr} className="capitalize">{fr}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="label">First Invoice Date *</label>
            <input className="input" type="date" value={form.next_run_at} onChange={(e) => setForm((f) => ({ ...f, next_run_at: e.target.value }))} />
          </div>

          <div className="space-y-2">
            <label className="label">Line Items</label>
            {form.items.map((item, i) => (
              <div key={i} className="grid grid-cols-12 gap-2 items-center">
                <div className="col-span-6">
                  <ProductAutocomplete
                    value={item.description}
                    onChange={(v) => setItem(i, "description", v)}
                    onSelect={({ description, unit_price }) => setForm((f) => ({
                      ...f,
                      items: f.items.map((it, idx) => idx === i ? { ...it, description, unit_price: String(unit_price) } : it)
                    }))}
                    placeholder="Description"
                  />
                </div>
                <div className="col-span-2">
                  <input className="input" type="number" placeholder="Qty" min="0.01" step="any" value={item.quantity} onChange={(e) => setItem(i, "quantity", e.target.value)} />
                </div>
                <div className="col-span-3">
                  <input className="input" type="number" placeholder="Price" min="0" step="any" value={item.unit_price} onChange={(e) => setItem(i, "unit_price", e.target.value)} />
                </div>
                <div className="col-span-1 flex justify-center">
                  {form.items.length > 1 && (
                    <button type="button" onClick={() => setForm((f) => ({ ...f, items: f.items.filter((_, idx) => idx !== i) }))} className="text-gray-400 hover:text-red-500">✕</button>
                  )}
                </div>
              </div>
            ))}
            <button type="button" className="btn-secondary text-sm" onClick={() => setForm((f) => ({ ...f, items: [...f.items, emptyItem()] }))}>
              <Plus size={14} /> Add Item
            </button>
          </div>

          <div className="flex gap-2 justify-end pt-2 border-t">
            <button className="btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
            <button className="btn-primary" onClick={handleSave} disabled={saving}>{saving ? "Creating…" : "Create"}</button>
          </div>
        </div>
      </Modal>

      <ConfirmDialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={async () => { await deleteRecurring(deleteTarget.id); setDeleteTarget(null); load(); }}
        title="Delete Recurring Invoice"
        message={`Stop recurring invoices for ${deleteTarget?.client_name}? This won't delete existing invoices.`}
        danger
      />
    </div>
  );
}
