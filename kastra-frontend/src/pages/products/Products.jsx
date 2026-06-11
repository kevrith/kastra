import { useEffect, useState } from "react";
import { getProducts, createProduct, updateProduct, deleteProduct } from "../../api/products";
import { Plus, Edit2, Trash2 } from "lucide-react";
import Modal from "../../components/ui/Modal";
import ConfirmDialog from "../../components/ui/ConfirmDialog";
import Spinner from "../../components/ui/Spinner";
import UpgradeGate from "../../components/ui/UpgradeGate";

function ksh(val) {
  return `KSh ${Number(val).toLocaleString("en-KE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

const EMPTY = { name: "", description: "", unit_price: "", cost_price: "" };

export default function Products() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [editId, setEditId] = useState(null);
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);

  const load = async () => {
    setLoading(true);
    const { data } = await getProducts();
    setProducts(data);
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const openAdd = () => { setForm(EMPTY); setEditId(null); setShowModal(true); };
  const openEdit = (p) => { setForm({ name: p.name, description: p.description ?? "", unit_price: String(p.unit_price), cost_price: String(p.cost_price ?? "") }); setEditId(p.id); setShowModal(true); };

  const handleSave = async () => {
    if (!form.name || !form.unit_price) return;
    setSaving(true);
    const payload = {
      name: form.name,
      description: form.description || null,
      unit_price: parseFloat(form.unit_price),
      cost_price: parseFloat(form.cost_price) || 0,
    };
    try {
      if (editId) await updateProduct(editId, payload);
      else await createProduct(payload);
      setShowModal(false);
      load();
    } finally {
      setSaving(false);
    }
  };

  return (
    <UpgradeGate
      feature="products"
      title="Products & Services"
      description="Build a catalogue of your products and services so line items fill in automatically on invoices."
      bullets={["Auto-fill prices when creating invoices", "Track cost price for profit margins", "Remember per-client agreed rates"]}
    >
    <div className="p-4 md:p-6 max-w-3xl mx-auto space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Products &amp; Services</h1>
          <p className="text-xs text-gray-400">Saved items autofill your invoice and quotation line items.</p>
        </div>
        <button className="btn-primary" onClick={openAdd}><Plus size={16} /> Add Product</button>
      </div>

      {loading ? (
        <div className="flex h-48 items-center justify-center"><Spinner size="lg" /></div>
      ) : products.length === 0 ? (
        <div className="card p-10 text-center text-sm text-gray-400">
          No products yet. Add your first product or service to speed up invoicing.
        </div>
      ) : (
        <div className="card divide-y divide-gray-100">
          {products.map((p) => (
            <div key={p.id} className="flex items-center gap-4 px-4 py-3">
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-900">{p.name}</p>
                {p.description && <p className="text-xs text-gray-400 truncate">{p.description}</p>}
              </div>
              <div className="text-right shrink-0">
                <p className="font-semibold text-gray-700">{ksh(p.unit_price)}</p>
                {Number(p.cost_price) > 0 && (
                  <p className="text-xs text-gray-400">Cost: {ksh(p.cost_price)}</p>
                )}
              </div>
              <div className="flex gap-1">
                <button onClick={() => openEdit(p)} className="p-1 text-gray-400 hover:text-gray-700"><Edit2 size={14} /></button>
                <button onClick={() => setDeleteTarget(p)} className="p-1 text-gray-400 hover:text-red-500"><Trash2 size={14} /></button>
              </div>
            </div>
          ))}
        </div>
      )}

      <Modal open={showModal} onClose={() => setShowModal(false)} title={editId ? "Edit Product" : "Add Product"} size="sm">
        <div className="space-y-4">
          <div>
            <label className="label">Name *</label>
            <input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Web Design (monthly)" />
          </div>
          <div>
            <label className="label">Description</label>
            <input className="input" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Optional details" />
          </div>
          <div>
            <label className="label">Selling Price (KSh) *</label>
            <input className="input" type="number" min="0" step="0.01" value={form.unit_price} onChange={(e) => setForm({ ...form, unit_price: e.target.value })} />
          </div>
          <div>
            <label className="label">Cost / Buying Price (KSh) <span className="text-gray-400 font-normal">(optional)</span></label>
            <input className="input" type="number" min="0" step="0.01" placeholder="0.00" value={form.cost_price} onChange={(e) => setForm({ ...form, cost_price: e.target.value })} />
            <p className="text-xs text-gray-400 mt-1">Used to calculate profit per invoice.</p>
          </div>
          <div className="flex gap-2 justify-end pt-1">
            <button className="btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
            <button className="btn-primary" onClick={handleSave} disabled={saving}>{saving ? "Saving…" : editId ? "Save" : "Add"}</button>
          </div>
        </div>
      </Modal>

      <ConfirmDialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={async () => { await deleteProduct(deleteTarget.id); setDeleteTarget(null); load(); }}
        title="Delete Product"
        message={`Delete "${deleteTarget?.name}"? This won't affect existing invoices or quotes.`}
        danger
      />
    </div>
    </UpgradeGate>
  );
}
