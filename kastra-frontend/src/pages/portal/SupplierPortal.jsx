import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getSupplierPortal, submitSupplierPrices } from "../../api/suppliers";
import { CheckCircle, Plus, Trash2, PackageSearch, Building2, FileText } from "lucide-react";
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
        if (data.existing_response) {
          setItems(data.existing_response.map((r) => ({
            ...r,
            unit_price: String(r.unit_price),
            quantity: String(r.quantity ?? ""),
          })));
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
      .catch(() => { setNotFound(true); setLoading(false); });
  }, [token]);

  const setItem = (i, k, v) =>
    setItems((prev) => prev.map((it, idx) => (idx === i ? { ...it, [k]: v } : it)));
  const addItem = () =>
    setItems((prev) => [...prev, { description: "", quantity: "", unit: "", unit_price: "", notes: "", sort_order: prev.length }]);
  const removeItem = (i) =>
    setItems((prev) => prev.filter((_, idx) => idx !== i));

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
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-12 max-w-sm w-full text-center space-y-4">
        <PackageSearch size={48} className="mx-auto text-gray-300" />
        <h1 className="text-xl font-bold text-gray-800">Link Not Found</h1>
        <p className="text-sm text-gray-500">This link is invalid or has expired. Contact the business that sent you this link.</p>
      </div>
    </div>
  );

  if (submitted) return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-12 max-w-sm w-full text-center space-y-4">
        <div className="h-20 w-20 rounded-full bg-green-100 flex items-center justify-center mx-auto">
          <CheckCircle size={40} className="text-green-600" />
        </div>
        <h1 className="text-2xl font-bold text-gray-900">Prices Submitted!</h1>
        <p className="text-sm text-gray-500">
          Thank you, <strong>{portal.supplier.name}</strong>. Your prices for{" "}
          <strong>{portal.title}</strong> have been sent to{" "}
          <strong>{portal.organization_name}</strong>.
        </p>
        <p className="text-xs text-gray-400">You can close this page now.</p>
      </div>
    </div>
  );

  const grandTotal = items.reduce((sum, it) => {
    const p = parseFloat(it.unit_price) || 0;
    const q = parseFloat(it.quantity) || 0;
    return sum + p * q;
  }, 0);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top bar */}
      <div className="bg-white border-b border-gray-200 px-4 py-4">
        <div className="max-w-6xl mx-auto flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-green-600 flex items-center justify-center shrink-0">
            <PackageSearch size={20} className="text-white" />
          </div>
          <div>
            <p className="font-bold text-gray-900 text-lg leading-tight">{portal.organization_name}</p>
            <p className="text-xs text-gray-400">Price Request Portal</p>
          </div>
          {portal.status === "responded" && (
            <span className="ml-auto inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full bg-green-100 text-green-700 font-semibold">
              <CheckCircle size={12} /> Previously Submitted
            </span>
          )}
        </div>
      </div>

      {/* Body */}
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="lg:grid lg:grid-cols-3 lg:gap-8 space-y-6 lg:space-y-0">

          {/* ── Left panel: request info (desktop sidebar) ── */}
          <div className="lg:col-span-1 space-y-5">
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 space-y-4">
              <div className="flex items-center gap-2 text-xs font-semibold text-gray-400 uppercase tracking-wide">
                <FileText size={13} /> Request Details
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-900">{portal.title}</h2>
                {portal.notes && (
                  <p className="text-sm text-gray-500 mt-2 leading-relaxed">{portal.notes}</p>
                )}
              </div>
              <div className="border-t border-gray-100 pt-4 space-y-2">
                <div className="flex items-start gap-2">
                  <Building2 size={15} className="text-gray-400 mt-0.5 shrink-0" />
                  <div>
                    <p className="text-sm font-semibold text-gray-800">{portal.supplier.name}</p>
                    {portal.supplier.company_name && (
                      <p className="text-xs text-gray-400">{portal.supplier.company_name}</p>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Summary of requested items (read-only, desktop only) */}
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 hidden lg:block">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Items Requested</p>
              <ul className="space-y-2">
                {portal.items.map((item) => (
                  <li key={item.id} className="flex items-start justify-between gap-3 text-sm">
                    <span className="text-gray-700">{item.description}</span>
                    {item.quantity != null && (
                      <span className="text-gray-400 shrink-0">
                        {Number(item.quantity).toLocaleString()} {item.unit || ""}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>

            {/* Grand total summary (desktop) */}
            {grandTotal > 0 && (
              <div className="bg-green-600 rounded-2xl p-6 text-white hidden lg:block">
                <p className="text-sm font-medium text-green-100">Your Estimated Total</p>
                <p className="text-3xl font-bold mt-1">{ksh(grandTotal)}</p>
                <p className="text-xs text-green-200 mt-1">Based on qty × unit price</p>
              </div>
            )}
          </div>

          {/* ── Right panel: price form ── */}
          <div className="lg:col-span-2">
            <form onSubmit={handleSubmit} className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-100 bg-gray-50">
                <h3 className="text-sm font-semibold text-gray-700">
                  Enter your unit price for each item below. You can also add extra items.
                </h3>
              </div>

              {/* Items table */}
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="bg-gray-50 text-left">
                      <th className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide min-w-[200px]">Item Description</th>
                      <th className="px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide w-24">Qty</th>
                      <th className="px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide w-24">Unit</th>
                      <th className="px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide w-40">Unit Price (KSh) *</th>
                      <th className="px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide w-36 text-right">Line Total</th>
                      <th className="px-3 py-3 w-10" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {items.map((item, i) => {
                      const lineTotal = (parseFloat(item.unit_price) || 0) * (parseFloat(item.quantity) || 0);
                      return (
                        <tr key={i} className="hover:bg-gray-50/50 transition-colors">
                          <td className="px-4 py-3">
                            <input
                              className="input text-sm"
                              placeholder="e.g. Dahua CCTV Camera 4MP"
                              value={item.description}
                              onChange={(e) => setItem(i, "description", e.target.value)}
                            />
                          </td>
                          <td className="px-3 py-3">
                            <input
                              className="input text-sm text-center bg-gray-50"
                              type="number"
                              placeholder="0"
                              min="0"
                              step="any"
                              value={item.quantity}
                              onChange={(e) => setItem(i, "quantity", e.target.value)}
                            />
                          </td>
                          <td className="px-3 py-3">
                            <input
                              className="input text-sm bg-gray-50"
                              placeholder="pcs"
                              value={item.unit}
                              onChange={(e) => setItem(i, "unit", e.target.value)}
                            />
                          </td>
                          <td className="px-3 py-3">
                            <input
                              className="input text-sm font-semibold text-gray-900"
                              type="number"
                              placeholder="0.00"
                              min="0"
                              step="0.01"
                              value={item.unit_price}
                              onChange={(e) => setItem(i, "unit_price", e.target.value)}
                              required={item.description.trim().length > 0}
                            />
                          </td>
                          <td className="px-3 py-3 text-right">
                            {lineTotal > 0 ? (
                              <span className="text-sm font-bold text-green-700 whitespace-nowrap">
                                {ksh(lineTotal)}
                              </span>
                            ) : (
                              <span className="text-sm text-gray-300">—</span>
                            )}
                          </td>
                          <td className="px-3 py-3 text-center">
                            <button
                              type="button"
                              onClick={() => removeItem(i)}
                              className="text-gray-300 hover:text-red-500 transition-colors p-1 rounded"
                              title="Remove item"
                            >
                              <Trash2 size={15} />
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                  {/* Grand total row */}
                  {grandTotal > 0 && (
                    <tfoot>
                      <tr className="border-t-2 border-gray-200 bg-gray-50">
                        <td colSpan={4} className="px-4 py-3 text-sm font-bold text-gray-700 text-right">
                          Estimated Grand Total
                        </td>
                        <td className="px-3 py-3 text-right">
                          <span className="text-base font-extrabold text-green-700">{ksh(grandTotal)}</span>
                        </td>
                        <td />
                      </tr>
                    </tfoot>
                  )}
                </table>
              </div>

              {/* Add item button */}
              <div className="px-6 py-3 border-t border-gray-100">
                <button type="button" className="btn-secondary text-sm" onClick={addItem}>
                  <Plus size={14} /> Add Item
                </button>
              </div>

              {/* Notes + error + submit */}
              <div className="px-6 pb-6 pt-2 space-y-4 border-t border-gray-100">
                {error && (
                  <div className="bg-red-50 text-red-700 text-sm px-4 py-3 rounded-xl">{error}</div>
                )}
                <div>
                  <label className="label">
                    Additional Notes{" "}
                    <span className="text-gray-400 font-normal">(optional)</span>
                  </label>
                  <textarea
                    className="input"
                    rows={3}
                    placeholder="Availability, lead time, delivery terms, payment terms, minimum order…"
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                  />
                </div>
                <button
                  type="submit"
                  className="btn-primary w-full py-3 text-base"
                  disabled={submitting}
                >
                  {submitting
                    ? "Submitting…"
                    : portal.status === "responded"
                    ? "Update My Prices"
                    : "Submit My Prices"}
                </button>
                <p className="text-xs text-gray-400 text-center">
                  Your prices will be sent directly to{" "}
                  <strong>{portal.organization_name}</strong>. You can re-open this link to update them anytime.
                </p>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
