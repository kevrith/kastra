import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getSupplierPortal, submitSupplierPrices } from "../../api/suppliers";
import { CheckCircle, Plus, Trash2, PackageSearch } from "lucide-react";
import Spinner from "../../components/ui/Spinner";

function ksh(val) {
  return `KSh ${Number(val).toLocaleString("en-KE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export default function SupplierPortal() {
  const { token } = useParams();
  const [portal, setPortal] = useState(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [items, setItems] = useState([]);
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getSupplierPortal(token)
      .then(({ data }) => {
        setPortal(data);
        // Pre-fill items from the request, or use existing response if already responded
        if (data.existing_response) {
          setItems(data.existing_response.map((r) => ({ ...r, unit_price: String(r.unit_price), quantity: String(r.quantity ?? "") })));
        } else {
          setItems(data.items.map((item) => ({
            description: item.description,
            quantity: item.quantity != null ? String(item.quantity) : "",
            unit: item.unit ?? "",
            unit_price: "",
            notes: "",
            sort_order: item.sort_order,
          })));
        }
        setLoading(false);
      })
      .catch(() => {
        setNotFound(true);
        setLoading(false);
      });
  }, [token]);

  const setItem = (i, k, v) => setItems((prev) => prev.map((it, idx) => idx === i ? { ...it, [k]: v } : it));
  const addItem = () => setItems((prev) => [...prev, { description: "", quantity: "", unit: "", unit_price: "", notes: "", sort_order: prev.length }]);
  const removeItem = (i) => setItems((prev) => prev.filter((_, idx) => idx !== i));

  const handleSubmit = async (e) => {
    e.preventDefault();
    const valid = items.filter((it) => it.description.trim() && it.unit_price);
    if (valid.length === 0) { setError("Please fill in a price for at least one item."); return; }
    setSubmitting(true);
    setError("");
    try {
      await submitSupplierPrices(token, {
        items: valid.map((it, i) => ({
          description: it.description,
          quantity: parseFloat(it.quantity) || null,
          unit: it.unit || null,
          unit_price: parseFloat(it.unit_price),
          notes: it.notes || null,
          sort_order: i,
        })),
        supplier_notes: notes || null,
      });
      setSubmitted(true);
    } catch (err) {
      setError(err.response?.data?.detail ?? "Submission failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div className="flex h-screen items-center justify-center"><Spinner size="lg" /></div>;

  if (notFound) return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
      <div className="card p-10 max-w-sm text-center space-y-3">
        <PackageSearch size={40} className="mx-auto text-gray-300" />
        <h1 className="text-lg font-bold text-gray-800">Link Not Found</h1>
        <p className="text-sm text-gray-500">This link is invalid or has expired. Please contact the business that sent you this link.</p>
      </div>
    </div>
  );

  if (submitted) return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
      <div className="card p-10 max-w-sm text-center space-y-4">
        <div className="h-16 w-16 rounded-full bg-green-100 flex items-center justify-center mx-auto">
          <CheckCircle size={32} className="text-green-600" />
        </div>
        <h1 className="text-xl font-bold text-gray-900">Prices Submitted!</h1>
        <p className="text-sm text-gray-500">
          Thank you, <strong>{portal.supplier.name}</strong>. Your prices for <strong>{portal.title}</strong> have been submitted successfully to <strong>{portal.organization_name}</strong>.
        </p>
        <p className="text-xs text-gray-400">You can close this page now.</p>
      </div>
    </div>
  );

  const total = items.reduce((sum, it) => {
    const p = parseFloat(it.unit_price) || 0;
    const q = parseFloat(it.quantity) || 1;
    return sum + (p * q);
  }, 0);

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Header */}
        <div className="text-center">
          <div className="inline-flex items-center justify-center h-12 w-12 rounded-xl bg-green-600 mb-3">
            <PackageSearch size={22} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">{portal.organization_name}</h1>
          <p className="text-gray-500 mt-1">Price Request</p>
        </div>

        {/* Request info */}
        <div className="card p-5 space-y-2">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div>
              <h2 className="font-bold text-gray-900 text-lg">{portal.title}</h2>
              <p className="text-sm text-gray-500 mt-0.5">
                Hello <strong>{portal.supplier.name}</strong>
                {portal.supplier.company_name && ` (${portal.supplier.company_name})`}
                , please provide your best prices for the items below.
              </p>
            </div>
            {portal.status === "responded" && (
              <span className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-green-100 text-green-700 font-semibold">
                <CheckCircle size={11} /> Previously Submitted
              </span>
            )}
          </div>
          {portal.notes && <p className="text-sm text-gray-600 bg-gray-50 rounded-lg p-3">{portal.notes}</p>}
        </div>

        {/* Price form */}
        <form onSubmit={handleSubmit} className="card overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100 bg-gray-50">
            <p className="text-sm font-semibold text-gray-700">
              Enter your unit price for each item. You can also add items not listed below.
            </p>
          </div>

          <div className="p-4 space-y-3">
            {error && <div className="bg-red-50 text-red-700 text-sm px-3 py-2 rounded-lg">{error}</div>}

            {/* Column headers */}
            <div className="hidden sm:grid grid-cols-12 gap-2 text-[10px] text-gray-400 uppercase tracking-wide px-1">
              <div className="col-span-4">Item Description</div>
              <div className="col-span-1">Qty</div>
              <div className="col-span-1">Unit</div>
              <div className="col-span-3">Unit Price (KSh) *</div>
              <div className="col-span-2 text-right">Line Total</div>
              <div className="col-span-1" />
            </div>

            {items.map((item, i) => {
              const lineTotal = (parseFloat(item.unit_price) || 0) * (parseFloat(item.quantity) || 0);
              return (
                <div key={i} className="grid grid-cols-12 gap-2 items-center">
                  <div className="col-span-12 sm:col-span-4">
                    <input
                      className="input"
                      placeholder="Item description"
                      value={item.description}
                      onChange={(e) => setItem(i, "description", e.target.value)}
                    />
                  </div>
                  <div className="col-span-3 sm:col-span-1">
                    <input
                      className="input bg-gray-50"
                      type="number"
                      placeholder="Qty"
                      value={item.quantity}
                      onChange={(e) => setItem(i, "quantity", e.target.value)}
                    />
                  </div>
                  <div className="col-span-3 sm:col-span-1">
                    <input
                      className="input bg-gray-50"
                      placeholder="unit"
                      value={item.unit}
                      onChange={(e) => setItem(i, "unit", e.target.value)}
                    />
                  </div>
                  <div className="col-span-5 sm:col-span-3">
                    <input
                      className="input font-medium"
                      type="number"
                      placeholder="0.00"
                      min="0"
                      step="0.01"
                      value={item.unit_price}
                      onChange={(e) => setItem(i, "unit_price", e.target.value)}
                      required={item.description.trim().length > 0}
                    />
                  </div>
                  <div className="col-span-1 hidden sm:block" />
                  <div className="col-span-12 sm:col-span-2 flex items-center justify-end sm:justify-end gap-2">
                    {lineTotal > 0 ? (
                      <span className="text-sm font-semibold text-green-700 whitespace-nowrap">{ksh(lineTotal)}</span>
                    ) : (
                      <span className="text-sm text-gray-300 hidden sm:block">—</span>
                    )}
                    <button type="button" onClick={() => removeItem(i)} className="text-gray-300 hover:text-red-500 p-1 shrink-0">
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              );
            })}

            <button type="button" className="btn-secondary text-sm" onClick={addItem}>
              <Plus size={14} /> Add Item
            </button>

            {/* Running total */}
            {total > 0 && (
              <div className="flex justify-between items-center bg-green-50 rounded-lg px-4 py-3 mt-2">
                <span className="text-sm font-semibold text-green-800">Estimated Total</span>
                <span className="text-base font-bold text-green-800">{ksh(total)}</span>
              </div>
            )}
          </div>

          {/* Notes + Submit */}
          <div className="px-4 pb-4 space-y-3 border-t border-gray-100 pt-4">
            <div>
              <label className="label">Additional Notes <span className="text-gray-400 font-normal">(optional)</span></label>
              <textarea
                className="input"
                rows={2}
                placeholder="Availability, lead time, delivery terms, payment terms…"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </div>
            <button type="submit" className="btn-primary w-full text-base py-3" disabled={submitting}>
              {submitting ? "Submitting…" : portal.status === "responded" ? "Update My Prices" : "Submit My Prices"}
            </button>
            <p className="text-xs text-gray-400 text-center">
              Your prices will be sent directly to {portal.organization_name}. You can re-open this link to update them.
            </p>
          </div>
        </form>
      </div>
    </div>
  );
}
