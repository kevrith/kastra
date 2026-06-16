import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Plus, Trash2, ArrowLeft } from "lucide-react";
import { getSuppliers } from "../../api/suppliers";
import { getProducts } from "../../api/products";
import {
  createPurchaseOrder, updatePurchaseOrder, getPurchaseOrder,
} from "../../api/purchaseOrders";
import { ksh } from "../../utils/formatters";
import Spinner from "../../components/ui/Spinner";

const EMPTY_ITEM = { product_id: null, description: "", unit: "", ordered_qty: 1, ordered_unit_price: 0 };

export default function PurchaseOrderForm() {
  const { id } = useParams();
  const navigate = useNavigate();
  const editing = !!id;

  const [suppliers, setSuppliers] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(editing);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const [form, setForm] = useState({
    supplier_id: "", currency: "KES", expected_delivery: "", notes: "", tax_amount: 0,
    items: [{ ...EMPTY_ITEM }],
  });

  useEffect(() => {
    (async () => {
      const [{ data: sup }, { data: prod }] = await Promise.all([getSuppliers(), getProducts()]);
      setSuppliers(sup);
      setProducts(prod.data ?? prod ?? []);
      if (editing) {
        const { data } = await getPurchaseOrder(id);
        const po = data.data;
        if (po.status !== "draft") { navigate(`/purchase-orders/${id}`); return; }
        setForm({
          supplier_id: po.supplier_id, currency: po.currency,
          expected_delivery: po.expected_delivery ?? "", notes: po.notes ?? "",
          tax_amount: Number(po.tax_amount) || 0,
          items: po.items.map((i) => ({
            product_id: i.product_id, description: i.description, unit: i.unit ?? "",
            ordered_qty: Number(i.ordered_qty), ordered_unit_price: Number(i.ordered_unit_price),
          })),
        });
        setLoading(false);
      }
    })();
  }, [id]);

  const setItem = (idx, key, val) => {
    const items = [...form.items];
    items[idx] = { ...items[idx], [key]: val };
    setForm({ ...form, items });
  };

  const pickProduct = (idx, productId) => {
    const p = products.find((x) => x.id === productId);
    const items = [...form.items];
    items[idx] = {
      ...items[idx],
      product_id: productId || null,
      description: p ? p.name : items[idx].description,
      ordered_unit_price: p && p.cost_price ? Number(p.cost_price) : items[idx].ordered_unit_price,
    };
    setForm({ ...form, items });
  };

  const addItem = () => setForm({ ...form, items: [...form.items, { ...EMPTY_ITEM }] });
  const removeItem = (idx) => setForm({ ...form, items: form.items.filter((_, i) => i !== idx) });

  const subtotal = form.items.reduce((s, i) => s + (Number(i.ordered_qty) || 0) * (Number(i.ordered_unit_price) || 0), 0);
  const total = subtotal + (Number(form.tax_amount) || 0);

  const save = async () => {
    setError("");
    if (!form.supplier_id) { setError("Choose a supplier."); return; }
    const items = form.items.filter((i) => i.description.trim());
    if (!items.length) { setError("Add at least one item."); return; }
    setSaving(true);
    const payload = {
      supplier_id: form.supplier_id, currency: form.currency,
      expected_delivery: form.expected_delivery || null, notes: form.notes || null,
      tax_amount: Number(form.tax_amount) || 0,
      items: items.map((i, idx) => ({
        product_id: i.product_id || null, description: i.description.trim(), unit: i.unit || null,
        ordered_qty: Number(i.ordered_qty) || 0, ordered_unit_price: Number(i.ordered_unit_price) || 0,
        sort_order: idx,
      })),
    };
    try {
      const { data } = editing ? await updatePurchaseOrder(id, payload) : await createPurchaseOrder(payload);
      navigate(`/purchase-orders/${data.data.id}`);
    } catch (e) {
      setError(e?.response?.data?.detail ?? "Could not save order.");
      setSaving(false);
    }
  };

  if (loading) return <div className="flex h-64 items-center justify-center"><Spinner size="lg" /></div>;

  return (
    <div className="p-4 md:p-6 max-w-3xl mx-auto space-y-5">
      <button onClick={() => navigate(-1)} className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800">
        <ArrowLeft size={15} /> Back
      </button>
      <h1 className="text-xl font-bold text-gray-900">{editing ? "Edit Purchase Order" : "New Purchase Order"}</h1>

      {error && <div className="bg-red-50 text-red-700 text-sm px-4 py-2.5 rounded-lg">{error}</div>}

      <div className="card p-4 space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="label">Supplier *</label>
            <select className="input" value={form.supplier_id} onChange={(e) => setForm({ ...form, supplier_id: e.target.value })}>
              <option value="">Select supplier…</option>
              {suppliers.map((s) => <option key={s.id} value={s.id}>{s.company_name || s.name}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Expected delivery</label>
            <input type="date" className="input" value={form.expected_delivery} onChange={(e) => setForm({ ...form, expected_delivery: e.target.value })} />
          </div>
        </div>
        <div>
          <label className="label">Notes to supplier <span className="text-gray-400 font-normal">(optional)</span></label>
          <textarea className="input" rows={2} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} placeholder="Delivery address, terms, instructions…" />
        </div>
      </div>

      <div className="card p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-gray-900">Items</h2>
          <button className="btn-secondary text-sm" onClick={addItem}><Plus size={14} /> Add item</button>
        </div>
        {form.items.map((it, idx) => (
          <div key={idx} className="grid grid-cols-12 gap-2 items-end border-b border-gray-100 pb-3">
            <div className="col-span-12 sm:col-span-5">
              <label className="label">Item</label>
              {products.length > 0 && (
                <select className="input mb-1 text-xs" value={it.product_id ?? ""} onChange={(e) => pickProduct(idx, e.target.value)}>
                  <option value="">— Free text / pick product —</option>
                  {products.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
              )}
              <input className="input" value={it.description} onChange={(e) => setItem(idx, "description", e.target.value)} placeholder="Description" />
            </div>
            <div className="col-span-3 sm:col-span-2">
              <label className="label">Qty</label>
              <input type="number" min="0" step="0.01" className="input" value={it.ordered_qty} onChange={(e) => setItem(idx, "ordered_qty", e.target.value)} />
            </div>
            <div className="col-span-3 sm:col-span-2">
              <label className="label">Unit</label>
              <input className="input" value={it.unit} onChange={(e) => setItem(idx, "unit", e.target.value)} placeholder="pcs" />
            </div>
            <div className="col-span-4 sm:col-span-2">
              <label className="label">Unit price</label>
              <input type="number" min="0" step="0.01" className="input" value={it.ordered_unit_price} onChange={(e) => setItem(idx, "ordered_unit_price", e.target.value)} />
            </div>
            <div className="col-span-2 sm:col-span-1 flex justify-end">
              {form.items.length > 1 && (
                <button onClick={() => removeItem(idx)} className="p-2 text-gray-300 hover:text-red-500"><Trash2 size={15} /></button>
              )}
            </div>
          </div>
        ))}
        <div className="flex justify-end gap-8 pt-1 text-sm">
          <div className="text-right space-y-1">
            <div className="flex justify-between gap-8 text-gray-500"><span>Subtotal</span><span>{ksh(subtotal)}</span></div>
            <div className="flex items-center justify-between gap-8 text-gray-500">
              <span>Tax</span>
              <input type="number" min="0" step="0.01" className="input w-28 text-right py-1" value={form.tax_amount} onChange={(e) => setForm({ ...form, tax_amount: e.target.value })} />
            </div>
            <div className="flex justify-between gap-8 font-bold text-gray-900 border-t border-gray-200 pt-1"><span>Total</span><span>{ksh(total)}</span></div>
          </div>
        </div>
      </div>

      <div className="flex justify-end gap-2">
        <button className="btn-secondary" onClick={() => navigate(-1)}>Cancel</button>
        <button className="btn-primary" onClick={save} disabled={saving}>{saving ? "Saving…" : editing ? "Save Changes" : "Create Draft"}</button>
      </div>
    </div>
  );
}
