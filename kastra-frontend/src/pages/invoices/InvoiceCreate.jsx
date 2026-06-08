import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { createInvoice } from "../../api/invoices";
import { getClients, createClient } from "../../api/clients";
import { getOrganization } from "../../api/organization";
import { suggestItems } from "../../api/ai";
import { scanReceipt } from "../../api/ocr";
import { Plus, Trash2, ArrowLeft, Sparkles, ScanLine, X, Camera } from "lucide-react";
import ProductAutocomplete from "../../components/ui/ProductAutocomplete";
import FinancialsForm from "../../components/ui/FinancialsForm";
import PriceConverter from "../../components/ui/PriceConverter";

const CONVERTED_NOTE_RE = /\s*\(≈ [^()]*\)\s*$/;

const emptyItem = () => ({ description: "", quantity: "1", unit_price: "", cost_price: "", discount_pct: "0", vat_exempt: false });

function compressImage(file, maxDimension = 1920) {
  return new Promise((resolve) => {
    const img = new Image();
    const objectUrl = URL.createObjectURL(file);
    img.onload = () => {
      URL.revokeObjectURL(objectUrl);
      let { width, height } = img;
      if (width > maxDimension || height > maxDimension) {
        if (width >= height) { height = Math.round(height * maxDimension / width); width = maxDimension; }
        else { width = Math.round(width * maxDimension / height); height = maxDimension; }
      }
      const canvas = document.createElement("canvas");
      canvas.width = width; canvas.height = height;
      canvas.getContext("2d").drawImage(img, 0, 0, width, height);
      const encode = (q) => {
        const dataUrl = canvas.toDataURL("image/jpeg", q);
        const b64 = dataUrl.split(",")[1];
        if (b64.length > 4 * 1024 * 1024 && q > 0.3) return encode(Math.max(0.3, q - 0.15));
        return { dataUrl, base64: b64, mediaType: "image/jpeg" };
      };
      resolve(encode(0.85));
    };
    img.src = objectUrl;
  });
}

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
  const [currency, setCurrency] = useState("KES");
  const [exchangeRate, setExchangeRate] = useState("1");
  const [depositAmount, setDepositAmount] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [suggesting, setSuggesting] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [showScan, setShowScan] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [scanPreview, setScanPreview] = useState(null);
  const [scanError, setScanError] = useState("");
  const [scanClientHint, setScanClientHint] = useState(null);
  const [creatingClient, setCreatingClient] = useState(false);
  const fileInputRef = useRef(null);

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

  const applyConvertedPrice = (i, { kesAmount, originalAmount, currency, rate }) => {
    setItems((prev) => prev.map((item, idx) => {
      if (idx !== i) return item;
      const note = `(≈ ${currency} ${originalAmount.toLocaleString()} @ ${rate.toLocaleString()})`;
      const baseDesc = item.description.replace(CONVERTED_NOTE_RE, "").trim();
      return {
        ...item,
        unit_price: String(kesAmount),
        description: baseDesc ? `${baseDesc} ${note}` : item.description,
      };
    }));
  };

  const handleSuggestItems = async () => {
    if (!clientId) return;
    setSuggesting(true);
    setSuggestions([]);
    try {
      const { data } = await suggestItems(clientId);
      setSuggestions(data.items || []);
    } catch (err) {
      setError(err.response?.data?.detail ?? "AI suggestion failed");
    } finally {
      setSuggesting(false);
    }
  };

  const applySuggestion = (s) => {
    setItems((prev) => {
      const hasEmpty = prev.some((it) => !it.description && !it.unit_price);
      const newItem = { description: s.description, quantity: String(s.quantity), unit_price: String(s.unit_price), cost_price: "", discount_pct: "0", vat_exempt: false };
      if (hasEmpty) return prev.map((it, idx) => (!it.description && !it.unit_price && idx === prev.findIndex((x) => !x.description && !x.unit_price)) ? newItem : it);
      return [...prev, newItem];
    });
    setSuggestions((prev) => prev.filter((x) => x.description !== s.description));
  };

  const handleFileSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setScanError("");
    setScanPreview(await compressImage(file));
  };

  const handleScan = async () => {
    if (!scanPreview) return;
    setScanning(true);
    setScanError("");
    try {
      const { data } = await scanReceipt(scanPreview.base64, scanPreview.mediaType);
      if (data.items?.length) {
        setItems(data.items.map((it) => ({
          description: it.description,
          quantity: String(it.quantity),
          unit_price: String(it.unit_price),
          cost_price: "",
          discount_pct: "0",
          vat_exempt: false,
        })));
      }
      if (data.notes) setNotes(data.notes);
      if (data.receipt_date) setInvoiceDate(data.receipt_date);
      if (data.client_name) {
        const match = clients.find((c) =>
          c.name.toLowerCase().includes(data.client_name.toLowerCase()) ||
          data.client_name.toLowerCase().includes(c.name.toLowerCase())
        );
        if (match) { setClientId(match.id); setScanClientHint(null); }
        else { setScanClientHint({ name: data.client_name, phone: data.client_phone || "", email: data.client_email || "" }); }
      }
      setShowScan(false);
      setScanPreview(null);
    } catch (err) {
      setScanError(err.response?.data?.detail ?? "Scan failed. Try a clearer image.");
    } finally {
      setScanning(false);
    }
  };

  const handleCreateClientFromScan = async () => {
    if (!scanClientHint) return;
    setCreatingClient(true);
    try {
      const { data } = await createClient({ name: scanClientHint.name, phone: scanClientHint.phone || null, email: scanClientHint.email || null });
      const newClient = data.data;
      setClients((prev) => [...prev, newClient]);
      setClientId(newClient.id);
      setScanClientHint(null);
    } catch { /* user can pick manually */ } finally {
      setCreatingClient(false);
    }
  };

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
        currency,
        exchange_rate: parseFloat(exchangeRate) || 1,
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
        <button type="button" className="btn-secondary" onClick={() => { setShowScan(true); setScanPreview(null); setScanError(""); setScanClientHint(null); }}>
          <ScanLine size={15} /> Scan Receipt
        </button>
      </div>

      {/* OCR Scan Modal */}
      {showScan && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md space-y-4 p-6">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-gray-900 flex items-center gap-2">
                <ScanLine size={18} className="text-green-600" /> Scan Receipt or Invoice
              </h2>
              <button onClick={() => setShowScan(false)} className="text-gray-400 hover:text-gray-600"><X size={18} /></button>
            </div>
            <p className="text-xs text-gray-500">
              Take a photo or upload an image of a receipt, handwritten quote, or printed invoice.
              Claude AI will extract the items and pre-fill the form for you.
            </p>
            <input ref={fileInputRef} type="file" accept="image/jpeg,image/png,image/webp" capture="environment"
              className="hidden" onChange={handleFileSelect} />
            {!scanPreview ? (
              <button type="button" className="btn-primary w-full" onClick={() => fileInputRef.current?.click()}>
                <Camera size={16} /> Take Photo / Choose Image
              </button>
            ) : (
              <div className="space-y-3">
                <img src={scanPreview.dataUrl} alt="Receipt preview"
                  className="w-full max-h-56 object-contain rounded-lg border border-gray-200" />
                {scanError && <p className="text-xs text-red-600">{scanError}</p>}
                <div className="flex gap-2">
                  <button type="button" className="btn-secondary flex-1"
                    onClick={() => { setScanPreview(null); fileInputRef.current?.click(); }}>Retake</button>
                  <button type="button" className="btn-primary flex-1" onClick={handleScan} disabled={scanning}>
                    {scanning ? "Scanning…" : "Extract Items"}
                  </button>
                </div>
              </div>
            )}
            <p className="text-[10px] text-gray-400 text-center">Powered by Claude AI · Review extracted data before saving</p>
          </div>
        </div>
      )}

      {error && <div className="bg-red-50 text-red-700 text-sm px-3 py-2 rounded-lg">{error}</div>}

      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="card p-4 space-y-4">
          <div>
            <label className="label">Client *</label>
            <select className="input" value={clientId} onChange={(e) => { setClientId(e.target.value); setScanClientHint(null); }} required>
              <option value="">Select a client…</option>
              {clients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            {scanClientHint && (
              <div className="mt-2 flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2.5">
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-semibold text-amber-800">New client detected from scan</p>
                  <p className="text-xs text-amber-700 mt-0.5 truncate">
                    {scanClientHint.name}
                    {scanClientHint.phone && <span className="ml-2 text-amber-600">{scanClientHint.phone}</span>}
                    {scanClientHint.email && <span className="ml-2 text-amber-600">{scanClientHint.email}</span>}
                  </p>
                </div>
                <button type="button" disabled={creatingClient}
                  onClick={handleCreateClientFromScan}
                  className="shrink-0 text-xs bg-amber-600 hover:bg-amber-700 text-white rounded-md px-2.5 py-1 font-medium transition-colors disabled:opacity-50">
                  {creatingClient ? "Adding…" : "Add client"}
                </button>
                <button type="button" onClick={() => setScanClientHint(null)} className="shrink-0 text-amber-500 hover:text-amber-700"><X size={14} /></button>
              </div>
            )}
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
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-700">Line Items</h2>
            {clientId && (
              <button
                type="button"
                onClick={handleSuggestItems}
                disabled={suggesting}
                className="flex items-center gap-1.5 text-xs text-purple-700 bg-purple-50 hover:bg-purple-100 border border-purple-200 rounded-lg px-3 py-1.5 font-medium transition-colors disabled:opacity-50"
              >
                <Sparkles size={13} />
                {suggesting ? "Thinking…" : "AI Suggest"}
              </button>
            )}
          </div>
          {suggestions.length > 0 && (
            <div className="bg-purple-50 border border-purple-200 rounded-lg p-3 space-y-2">
              <p className="text-xs text-purple-700 font-medium">Suggested from past invoices — click to add:</p>
              <div className="flex flex-wrap gap-2">
                {suggestions.map((s, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => applySuggestion(s)}
                    className="text-xs bg-white border border-purple-200 rounded-lg px-3 py-1.5 hover:bg-purple-100 text-gray-700 transition-colors"
                  >
                    {s.description} — KES {Number(s.unit_price).toLocaleString()}
                  </button>
                ))}
              </div>
            </div>
          )}
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
                <div className="relative">
                  <input className="input pr-7" type="number" placeholder="Sell Price" min="0" step="any"
                    value={item.unit_price} onChange={(e) => setItem(i, "unit_price", e.target.value)} required />
                  <div className="absolute right-1 top-1/2 -translate-y-1/2">
                    <PriceConverter onApply={(conversion) => applyConvertedPrice(i, conversion)} />
                  </div>
                </div>
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
          currency={currency}
          setCurrency={setCurrency}
          exchangeRate={exchangeRate}
          setExchangeRate={setExchangeRate}
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
