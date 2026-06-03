import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { createInvoice } from "../../api/invoices";
import { getClients } from "../../api/clients";
import { getOrganization } from "../../api/organization";
import { Plus, Trash2, ArrowLeft } from "lucide-react";
import ProductAutocomplete from "../../components/ui/ProductAutocomplete";
import FinancialsForm from "../../components/ui/FinancialsForm";

const emptyItem = () => ({ description: "", quantity: "1", unit_price: "", cost_price: "", discount_pct: "0", vat_exempt: false });

export default function InvoiceCreate() {
  const navigate = useNavigate();
  const [clients, setClients] = useState([]);
  const [clientId, setClientId] = useState("");
  const [lpoNumber, setLpoNumber] = useState("");
  const [invoiceDate, setInvoiceDate] = useState(new Date().toISOString().slice(0, 10));
  const [dueDate, setDueDate] = useState("");
  const [notes, setNotes] = useState("");
  const [items, setItems] = useState([emptyItem()]);
  const [charges, setCharges] = useState([]);
  const [discountPct, setDiscountPct] = useState("0");
  const [whtPct, setWhtPct] = useState("0");
  const [depositAmount, setDepositAmount] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getClients({ limit: 100 }).then(({ data }) => setClients(data.data));
    getOrganization().then(({ data }) => {
      const days = data.data.payment_terms_days ?? 30;
      const d = new Date();
      d.setDate(d.getDate() + days);
      setDueDate(d.toISOString().slice(0, 10));
    }).catch(() => {});
  }, []);

  const setItem = (i, field, value) =>
    setItems((prev) => prev.map((item, idx) => (idx === i ? { ...item, [field]: value } : item)));

  const removeItem = (i) => setItems((prev) => prev.filter((_, idx) => idx !== i));
  const addItem = () => setItems((prev) => [...prev, emptyItem()]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!clientId) { setError("Please select a client"); return; }
    setSaving(true);
    setError("");
    try {
      const { data } = await createInvoice({
        client_id: clientId,
        invoice_date: invoiceDate ? new Date(invoiceDate).toISOString() : null,
        lpo_number: lpoNumber || null,
        due_date: dueDate ? new Date(dueDate).toISOString() : null,
        notes: notes || null,
        discount_pct: parseFloat(discountPct) || 0,
        wht_pct: parseFloat(whtPct) || 0,
        deposit_amount: parseFloat(depositAmount) || 0,
        items: items.map((item, i) => ({
          description: item.description,
          quantity: parseFloat(item.quantity),
          unit_price: parseFloat(item.unit_price),
          cost_price: parseFloat(item.cost_price) || 0,
          discount_pct: parseFloat(item.discount_pct) || 0,
          vat_exempt: item.vat_exempt,
          sort_order: i,
        })),
        charges: charges.filter((c) => c.description && c.amount).map((c, i) => ({
          description: c.description,
          amount: parseFloat(c.amount),
          vat_exempt: c.vat_exempt,
          sort_order: i,
        })),
      });
      navigate(`/invoices/${data.data.id}`);
    } catch (err) {
      setError(err.response?.data?.detail ?? "Failed to create invoice");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-4 md:p-6 max-w-3xl mx-auto space-y-5">
      <div className="flex items-center gap-3">
        <button onClick={() => navigate(-1)} className="text-gray-400 hover:text-gray-600"><ArrowLeft size={20} /></button>
        <h1 className="text-xl font-bold text-gray-900 flex-1">New Invoice</h1>
      </div>

      {error && <div className="bg-red-50 text-red-700 text-sm px-3 py-2 rounded-lg">{error}</div>}

      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="card p-4 space-y-4">
          <div>
            <label className="label">Client *</label>
            <select className="input" value={clientId} onChange={(e) => setClientId(e.target.value)} required>
              <option value="">Select a client…</option>
              {clients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="label">Invoice Date</label>
              <input className="input" type="date" value={invoiceDate}
                onChange={(e) => setInvoiceDate(e.target.value)} />
            </div>
            <div>
              <label className="label">Due Date</label>
              <input className="input" type="date" value={dueDate}
                onChange={(e) => setDueDate(e.target.value)} />
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="label">LPO Number <span className="text-gray-400 font-normal">(optional)</span></label>
              <input className="input" type="text" placeholder="e.g. LPO-2026-001"
                value={lpoNumber} onChange={(e) => setLpoNumber(e.target.value)} />
            </div>
          </div>
        </div>

        <div className="card p-4 space-y-3">
          <h2 className="text-sm font-semibold text-gray-700">Line Items</h2>
          <div className="hidden sm:grid grid-cols-12 gap-2 text-[10px] text-gray-400 uppercase tracking-wide px-1">
            <div className="col-span-4">Description</div>
            <div className="col-span-1">Qty</div>
            <div className="col-span-2">Sell Price</div>
            <div className="col-span-2">Cost Price</div>
            <div className="col-span-1">Disc%</div>
            <div className="col-span-1 text-center">VAT</div>
            <div className="col-span-1" />
          </div>
          {items.map((item, i) => (
            <div key={i} className="grid grid-cols-12 gap-2 items-center">
              <div className="col-span-12 sm:col-span-4">
                <ProductAutocomplete
                  value={item.description}
                  onChange={(v) => setItem(i, "description", v)}
                  onSelect={({ description, unit_price, cost_price }) => setItems((prev) =>
                    prev.map((it, idx) => idx === i ? { ...it, description, unit_price: String(unit_price), cost_price: String(cost_price ?? "") } : it)
                  )}
                  placeholder="Description (type to search products)"
                  clientId={clientId || undefined}
                />
              </div>
              <div className="col-span-3 sm:col-span-1">
                <input className="input" type="number" placeholder="Qty" min="0.01" step="any"
                  value={item.quantity} onChange={(e) => setItem(i, "quantity", e.target.value)} required />
              </div>
              <div className="col-span-4 sm:col-span-2">
                <input className="input" type="number" placeholder="Sell Price" min="0" step="any"
                  value={item.unit_price} onChange={(e) => setItem(i, "unit_price", e.target.value)} required />
              </div>
              <div className="col-span-4 sm:col-span-2">
                <input className="input" type="number" placeholder="Cost Price" min="0" step="any"
                  title="What you paid to buy/make this item"
                  value={item.cost_price} onChange={(e) => setItem(i, "cost_price", e.target.value)} />
              </div>
              <div className="col-span-3 sm:col-span-1">
                <div className="relative">
                  <input className="input pr-5" type="number" placeholder="Disc" min="0" max="100" step="0.01"
                    value={item.discount_pct} onChange={(e) => setItem(i, "discount_pct", e.target.value)} />
                  <span className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 text-xs">%</span>
                </div>
              </div>
              <div className="col-span-1 flex items-center justify-center" title={item.vat_exempt ? "VAT exempt" : "VAT applies (16%)"}>
                <label className="flex flex-col items-center gap-0.5 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={!item.vat_exempt}
                    onChange={(e) => setItem(i, "vat_exempt", !e.target.checked)}
                    className="accent-green-600"
                  />
                  <span className="text-[10px] text-gray-400 leading-none">VAT</span>
                </label>
              </div>
              <div className="col-span-1 flex justify-center">
                {items.length > 1 && (
                  <button type="button" onClick={() => removeItem(i)} className="text-gray-400 hover:text-red-600">
                    <Trash2 size={15} />
                  </button>
                )}
              </div>
            </div>
          ))}
          <button type="button" className="btn-secondary text-sm" onClick={addItem}>
            <Plus size={15} /> Add Item
          </button>
        </div>

        <FinancialsForm
          items={items}
          setItems={setItems}
          charges={charges}
          setCharges={setCharges}
          discountPct={discountPct}
          setDiscountPct={setDiscountPct}
          whtPct={whtPct}
          setWhtPct={setWhtPct}
          depositAmount={depositAmount}
          setDepositAmount={setDepositAmount}
          showDeposit={true}
        />

        <div className="card p-4">
          <label className="label">Notes <span className="text-gray-400 font-normal">(optional)</span></label>
          <textarea className="input" rows={3} placeholder="Payment terms, special instructions…"
            value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>

        <div className="flex justify-end gap-3">
          <button type="button" className="btn-secondary" onClick={() => navigate(-1)}>Cancel</button>
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? "Creating…" : "Create Invoice"}
          </button>
        </div>
      </form>
    </div>
  );
}
