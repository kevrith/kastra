import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { createSupplierRequest } from "../../api/suppliers";
import { getProducts } from "../../api/products";
import { Plus, Trash2, ArrowLeft } from "lucide-react";

const emptyItem = () => ({ description: "", quantity: "", unit: "" });

export default function NewSupplierRequest() {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [notes, setNotes] = useState("");
  const [items, setItems] = useState([emptyItem()]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const setItem = (i, k, v) => setItems((prev) => prev.map((it, idx) => (idx === i ? { ...it, [k]: v } : it)));
  const addItem = () => setItems((prev) => [...prev, emptyItem()]);
  const removeItem = (i) => setItems((prev) => prev.filter((_, idx) => idx !== i));

  const handleSubmit = async (e) => {
    e.preventDefault();
    const validItems = items.filter((it) => it.description.trim());
    if (!title || validItems.length === 0) { setError("Add a title and at least one item."); return; }
    setSaving(true);
    setError("");
    try {
      const { data } = await createSupplierRequest({
        title,
        notes: notes || null,
        items: validItems.map((it, i) => ({
          description: it.description,
          quantity: parseFloat(it.quantity) || null,
          unit: it.unit || null,
          sort_order: i,
        })),
      });
      navigate(`/suppliers/requests/${data.data.id}`);
    } catch (err) {
      setError(err.response?.data?.detail ?? "Failed to create request");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-4 md:p-6 max-w-2xl mx-auto space-y-5">
      <div className="flex items-center gap-3">
        <button onClick={() => navigate("/suppliers")} className="text-gray-400 hover:text-gray-600"><ArrowLeft size={20} /></button>
        <h1 className="text-xl font-bold text-gray-900">New Price Request</h1>
      </div>

      {error && <div className="bg-red-50 text-red-700 text-sm px-3 py-2 rounded-lg">{error}</div>}

      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="card p-4 space-y-4">
          <div>
            <label className="label">Request Title *</label>
            <input className="input" placeholder="e.g. Cement & Steel — June 2026" value={title} onChange={(e) => setTitle(e.target.value)} required />
            <p className="text-xs text-gray-400 mt-1">Suppliers will see this title when they open your link.</p>
          </div>
          <div>
            <label className="label">Notes <span className="text-gray-400 font-normal">(optional)</span></label>
            <textarea className="input" rows={2} placeholder="Delivery location, urgency, special requirements…" value={notes} onChange={(e) => setNotes(e.target.value)} />
          </div>
        </div>

        <div className="card p-4 space-y-3">
          <h2 className="text-sm font-semibold text-gray-700">Items to Price</h2>
          <div className="hidden sm:grid grid-cols-12 gap-2 text-[10px] text-gray-400 uppercase tracking-wide px-1">
            <div className="col-span-6">Description *</div>
            <div className="col-span-3">Quantity</div>
            <div className="col-span-2">Unit</div>
            <div className="col-span-1" />
          </div>
          {items.map((item, i) => (
            <div key={i} className="grid grid-cols-12 gap-2 items-center">
              <div className="col-span-12 sm:col-span-6">
                <input className="input" placeholder="e.g. Cement (50kg bag)" value={item.description}
                  onChange={(e) => setItem(i, "description", e.target.value)} />
              </div>
              <div className="col-span-5 sm:col-span-3">
                <input className="input" type="number" placeholder="Qty" min="0" step="any" value={item.quantity}
                  onChange={(e) => setItem(i, "quantity", e.target.value)} />
              </div>
              <div className="col-span-5 sm:col-span-2">
                <input className="input" placeholder="bags" value={item.unit}
                  onChange={(e) => setItem(i, "unit", e.target.value)} />
              </div>
              <div className="col-span-2 sm:col-span-1 flex justify-center">
                {items.length > 1 && (
                  <button type="button" onClick={() => removeItem(i)} className="text-gray-400 hover:text-red-500"><Trash2 size={14} /></button>
                )}
              </div>
            </div>
          ))}
          <button type="button" className="btn-secondary text-sm" onClick={addItem}>
            <Plus size={14} /> Add Item
          </button>
        </div>

        <div className="flex justify-end gap-3">
          <button type="button" className="btn-secondary" onClick={() => navigate("/suppliers")}>Cancel</button>
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? "Creating…" : "Create Request"}
          </button>
        </div>
      </form>
    </div>
  );
}
