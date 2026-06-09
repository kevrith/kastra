import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { createQuotation, getQuotation, updateQuotation } from "../../api/quotations";
import { getClients, createClient } from "../../api/clients";
import { getOrganization } from "../../api/organization";
import { scanReceipt } from "../../api/ocr";
import { generateDescription } from "../../api/ai";
import { Plus, Trash2, ArrowLeft, ScanLine, X, Camera, Sparkles } from "lucide-react";
import ProductAutocomplete from "../../components/ui/ProductAutocomplete";
import FinancialsForm from "../../components/ui/FinancialsForm";
import PriceConverter from "../../components/ui/PriceConverter";

const CONVERTED_NOTE_RE = /\s*\(≈ [^()]*\)\s*$/;

const emptyItem = () => ({ description: "", quantity: "1", unit_price: "", discount_pct: "0", vat_exempt: false });

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
      canvas.width = width;
      canvas.height = height;
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

export default function QuotationForm() {
  const { id } = useParams();
  const isEdit = !!id;
  const navigate = useNavigate();

  const [clients, setClients] = useState([]);
  const [clientId, setClientId] = useState("");
  const [notes, setNotes] = useState("");
  const [projectDescription, setProjectDescription] = useState("");
  const [expiresAt, setExpiresAt] = useState("");
  const [items, setItems] = useState([emptyItem()]);
  const [charges, setCharges] = useState([]);
  const [discountPct, setDiscountPct] = useState("0");
  const [whtPct, setWhtPct] = useState("0");
  const [currency, setCurrency] = useState("KES");
  const [exchangeRate, setExchangeRate] = useState("1");
  const [labourPct, setLabourPct] = useState("0");
  const [labourVatExempt, setLabourVatExempt] = useState(false);
  const [saving, setSaving] = useState(false);
  const [savingDraft, setSavingDraft] = useState(false);
  const [error, setError] = useState("");
  const [showScan, setShowScan] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [scanPreview, setScanPreview] = useState(null);
  const [scanError, setScanError] = useState("");
  const [scanClientHint, setScanClientHint] = useState(null);
  const [creatingClient, setCreatingClient] = useState(false);
  const [showDescGen, setShowDescGen] = useState(false);
  const [descBullets, setDescBullets] = useState("");
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState("");
  const fileInputRef = useRef(null);

  useEffect(() => {
    getClients({ limit: 100 }).then(({ data }) => setClients(data.data));
    if (isEdit) {
      getQuotation(id).then(({ data }) => {
        const q = data.data;
        setClientId(q.client_id);
        setProjectDescription(q.project_description ?? "");
        setNotes(q.notes ?? "");
        setExpiresAt(q.expires_at ? q.expires_at.slice(0, 10) : "");
        setItems(q.items.map((i) => ({
          description: i.description,
          quantity: String(i.quantity),
          unit_price: String(i.unit_price),
          discount_pct: String(i.discount_pct ?? 0),
          vat_exempt: i.vat_exempt ?? false,
          sort_order: i.sort_order,
        })));
        const labourCharge = (q.charges || []).find((c) => c.description === "Labour");
        const otherCharges = (q.charges || []).filter((c) => c.description !== "Labour");
        if (labourCharge) {
          const subtotal = q.items.reduce((s, i) => s + parseFloat(i.quantity) * parseFloat(i.unit_price), 0);
          setLabourPct(subtotal > 0 ? String(Math.round((parseFloat(labourCharge.amount) / subtotal) * 10000) / 100) : "0");
          setLabourVatExempt(labourCharge.vat_exempt ?? false);
        }
        setCharges(otherCharges.map((c) => ({ description: c.description, amount: String(c.amount), vat_exempt: c.vat_exempt })));
        setDiscountPct(String(q.discount_pct ?? 0));
        setWhtPct(String(q.wht_pct ?? 0));
        setCurrency(q.currency ?? "KES");
        setExchangeRate(String(q.exchange_rate ?? 1));
      });
    } else {
      getOrganization().then(({ data }) => {
        const days = data.data.quotation_validity_days ?? 30;
        const expiry = new Date();
        expiry.setDate(expiry.getDate() + days);
        setExpiresAt(expiry.toISOString().slice(0, 10));
      }).catch(() => {});
    }
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

  const buildPayload = (isDraft = false) => {
    const validItems = items.filter((it) => it.description.trim() && parseFloat(it.quantity) > 0 && it.unit_price.toString().trim() !== "");
    const itemsGross = validItems.reduce((s, it) => s + parseFloat(it.quantity) * parseFloat(it.unit_price), 0);
    return {
      client_id: clientId || null,
      project_description: projectDescription || null,
      notes: notes || null,
      expires_at: expiresAt ? new Date(expiresAt).toISOString() : null,
      discount_pct: parseFloat(discountPct) || 0,
      wht_pct: parseFloat(whtPct) || 0,
      currency,
      exchange_rate: parseFloat(exchangeRate) || 1,
      status: isDraft ? "draft" : "pending",
      items: validItems.map((item, i) => ({
        description: item.description,
        quantity: parseFloat(item.quantity),
        unit_price: parseFloat(item.unit_price),
        discount_pct: parseFloat(item.discount_pct) || 0,
        vat_exempt: item.vat_exempt,
        sort_order: i,
      })),
      charges: [
        ...(parseFloat(labourPct) > 0 ? [{
          description: "Labour",
          amount: parseFloat(labourPct) / 100 * itemsGross,
          vat_exempt: labourVatExempt,
          sort_order: 0,
        }] : []),
        ...charges.filter((c) => c.description && parseFloat(c.amount) > 0).map((c, i) => ({
          description: c.description,
          amount: parseFloat(c.amount),
          vat_exempt: c.vat_exempt,
          sort_order: i + 1,
        })),
      ],
    };
  };

  const save = async (setLoader, isDraft = false) => {
    if (!isDraft && !clientId) { setError("Please select a client"); return; }
    setLoader(true);
    setError("");
    try {
      const payload = buildPayload(isDraft);
      if (isEdit) {
        await updateQuotation(id, payload);
        navigate(`/quotations/${id}`);
      } else {
        const { data } = await createQuotation(payload);
        navigate(`/quotations/${data.data.id}`);
      }
    } catch (err) {
      setError(err.response?.data?.detail ?? "Failed to save quotation");
    } finally {
      setLoader(false);
    }
  };

  const handleSubmit = (e) => { e.preventDefault(); save(setSaving, false); };
  const handleSaveDraft = () => save(setSavingDraft, true);

  const handleFileSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setScanError("");
    const compressed = await compressImage(file);
    setScanPreview(compressed);
  };

  const handleScan = async () => {
    if (!scanPreview) return;
    setScanning(true);
    setScanError("");
    try {
      const { base64, mediaType } = scanPreview;
      const { data } = await scanReceipt(base64, mediaType);
      const result = data;
      if (result.items?.length) {
        setItems(result.items.map((it) => ({
          description: it.description,
          quantity: String(it.quantity),
          unit_price: String(it.unit_price),
          vat_exempt: false,
        })));
      }
      if (result.notes) setNotes(result.notes);
      if (result.client_name) {
        const match = clients.find((c) =>
          c.name.toLowerCase().includes(result.client_name.toLowerCase()) ||
          result.client_name.toLowerCase().includes(c.name.toLowerCase())
        );
        if (match) {
          setClientId(match.id);
          setScanClientHint(null);
        } else {
          setScanClientHint({ name: result.client_name, phone: result.client_phone || "", email: result.client_email || "" });
        }
      }
      setShowScan(false);
      setScanPreview(null);
    } catch (err) {
      setScanError(err.response?.data?.detail ?? "Scan failed. Try a clearer image.");
    } finally {
      setScanning(false);
    }
  };

  const handleGenerateDescription = async () => {
    if (!descBullets.trim()) return;
    setGenerating(true);
    setGenError("");
    try {
      const context = projectDescription ? `Project: ${projectDescription}` : "";
      const { data } = await generateDescription(descBullets, context);
      setNotes((prev) => (prev ? prev + "\n\n" : "") + data.description);
      setShowDescGen(false);
      setDescBullets("");
    } catch (err) {
      setGenError(err.response?.data?.detail ?? "Generation failed. Try again.");
    } finally {
      setGenerating(false);
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
    } catch {
      // ignore — user can still pick manually
    } finally {
      setCreatingClient(false);
    }
  };

  return (
    <div className="p-4 md:p-6 max-w-3xl mx-auto space-y-5">
      <div className="flex items-center gap-3">
        <button onClick={() => navigate(-1)} className="text-gray-400 hover:text-gray-600"><ArrowLeft size={20} /></button>
        <h1 className="text-xl font-bold text-gray-900 flex-1">{isEdit ? "Edit Quotation" : "New Quotation"}</h1>
        {!isEdit && (
          <button type="button" className="btn-secondary" onClick={() => { setShowScan(true); setScanPreview(null); setScanError(""); setScanClientHint(null); }}>
            <ScanLine size={15} /> Scan Receipt
          </button>
        )}
      </div>

      {/* OCR Scan Modal */}
      {showScan && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md space-y-4 p-6">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-gray-900 flex items-center gap-2">
                <ScanLine size={18} className="text-green-600" /> Scan Receipt or Quotation
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
            <label className="label">Project Description <span className="text-gray-400 font-normal">(optional)</span></label>
            <textarea className="input" rows={2}
              placeholder="e.g. Kevin's 5-bedroom house — Kiambu Road, Phase 1 supply"
              value={projectDescription}
              onChange={(e) => setProjectDescription(e.target.value)}
            />
            <p className="text-xs text-gray-400 mt-1">Appears in WhatsApp messages and helps you track the project</p>
          </div>
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
                <div className="flex gap-1.5 shrink-0">
                  <button type="button" className="btn-primary text-xs py-1 px-2.5"
                    onClick={handleCreateClientFromScan} disabled={creatingClient}>
                    {creatingClient ? "Adding…" : "Create & Select"}
                  </button>
                  <button type="button" onClick={() => setScanClientHint(null)} className="text-amber-400 hover:text-amber-600">
                    <X size={14} />
                  </button>
                </div>
              </div>
            )}
          </div>
          <div>
            <label className="label">Expiry Date</label>
            <input className="input" type="date" value={expiresAt}
              onChange={(e) => setExpiresAt(e.target.value)}
              min={new Date().toISOString().slice(0, 10)} />
            <p className="text-xs text-gray-400 mt-1">Quotation will auto-expire after this date</p>
          </div>
        </div>

        <div className="card p-4 space-y-3">
          <h2 className="text-sm font-semibold text-gray-700">Line Items</h2>
          {items.map((item, i) => (
            <div key={i} className="grid grid-cols-12 gap-2 items-center">
              <div className="col-span-12 sm:col-span-4">
                <ProductAutocomplete
                  value={item.description}
                  onChange={(v) => setItem(i, "description", v)}
                  onSelect={({ description, unit_price }) => setItems((prev) =>
                    prev.map((it, idx) => idx === i ? { ...it, description, unit_price: String(unit_price) } : it)
                  )}
                  placeholder="Description (type to search products)"
                  clientId={clientId || undefined}
                />
              </div>
              <div className="col-span-3 sm:col-span-2">
                <input className="input" type="number" placeholder="Qty" min="0.01" step="any"
                  value={item.quantity} onChange={(e) => setItem(i, "quantity", e.target.value)} required />
              </div>
              <div className="col-span-4 sm:col-span-2">
                <div className="relative">
                  <input className="input pr-7" type="number" placeholder="Unit Price" min="0" step="any"
                    value={item.unit_price} onChange={(e) => setItem(i, "unit_price", e.target.value)} required />
                  <div className="absolute right-1 top-1/2 -translate-y-1/2">
                    <PriceConverter onApply={(conversion) => applyConvertedPrice(i, conversion)} />
                  </div>
                </div>
              </div>
              <div className="col-span-3 sm:col-span-2">
                <div className="relative">
                  <input className="input pr-5" type="number" placeholder="Disc" min="0" max="100" step="0.01"
                    value={item.discount_pct} onChange={(e) => setItem(i, "discount_pct", e.target.value)} />
                  <span className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 text-xs">%</span>
                </div>
              </div>
              <div className="col-span-1 sm:col-span-1 flex items-center justify-center" title={item.vat_exempt ? "VAT exempt" : "VAT applies (16%)"}>
                <label className="flex flex-col items-center gap-0.5 cursor-pointer select-none">
                  <input type="checkbox" checked={!item.vat_exempt}
                    onChange={(e) => setItem(i, "vat_exempt", !e.target.checked)}
                    className="accent-green-600" />
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
          labourPct={labourPct}
          setLabourPct={setLabourPct}
          labourVatExempt={labourVatExempt}
          setLabourVatExempt={setLabourVatExempt}
        />

        <div className="card p-4 space-y-3">
          <div className="flex items-center justify-between">
            <label className="label mb-0">Notes / Scope</label>
            <button
              type="button"
              onClick={() => { setShowDescGen((v) => !v); setGenError(""); }}
              className="flex items-center gap-1.5 text-xs text-purple-700 bg-purple-50 hover:bg-purple-100 border border-purple-200 rounded-lg px-3 py-1.5 font-medium transition-colors"
            >
              <Sparkles size={13} /> AI Write
            </button>
          </div>
          {showDescGen && (
            <div className="bg-purple-50 border border-purple-200 rounded-lg p-3 space-y-2">
              <p className="text-xs text-purple-700 font-medium">Enter bullet points — AI will write a professional scope for you:</p>
              <textarea
                className="input text-sm"
                rows={3}
                placeholder={"- Supply and install 10 CCTV cameras\n- 6 months warranty\n- Commissioning included"}
                value={descBullets}
                onChange={(e) => setDescBullets(e.target.value)}
              />
              {genError && <p className="text-xs text-red-600">{genError}</p>}
              <div className="flex gap-2 justify-end">
                <button type="button" className="btn-secondary text-xs" onClick={() => { setShowDescGen(false); setDescBullets(""); }}>Cancel</button>
                <button type="button" className="btn-primary text-xs flex items-center gap-1.5" onClick={handleGenerateDescription} disabled={generating || !descBullets.trim()}>
                  <Sparkles size={12} /> {generating ? "Writing…" : "Generate"}
                </button>
              </div>
            </div>
          )}
          <textarea className="input" rows={3} placeholder="Payment terms, special instructions, scope of work…"
            value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>

        <div className="flex justify-end gap-3">
          <button type="button" className="btn-secondary" onClick={() => navigate(-1)}>Cancel</button>
          {!isEdit && (
            <button type="button" className="btn-secondary" onClick={handleSaveDraft} disabled={savingDraft || saving}>
              {savingDraft ? "Saving…" : "Save Draft"}
            </button>
          )}
          <button type="submit" className="btn-primary" disabled={saving || savingDraft}>
            {saving ? "Saving…" : isEdit ? "Update Quotation" : "Create Quotation"}
          </button>
        </div>
      </form>
    </div>
  );
}
