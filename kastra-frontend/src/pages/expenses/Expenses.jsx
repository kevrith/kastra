import { useEffect, useRef, useState } from "react";
import { getExpenses, createExpense, updateExpense, deleteExpense } from "../../api/expenses";
import { categorizeExpense } from "../../api/ai";
import { Plus, Edit2, Trash2, X, Check, ScanLine } from "lucide-react";
import Modal from "../../components/ui/Modal";
import ConfirmDialog from "../../components/ui/ConfirmDialog";
import Spinner from "../../components/ui/Spinner";

const CATEGORIES = ["rent", "salaries", "utilities", "supplies", "materials", "labour", "lunch", "transport", "fuel", "other"];

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
        return { base64: b64, mediaType: "image/jpeg" };
      };
      resolve(encode(0.85));
    };
    img.src = objectUrl;
  });
}

function ksh(val) {
  return `KSh ${Number(val).toLocaleString("en-KE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

const EMPTY_FORM = { category: "other", description: "", vendor: "", amount: "", date: new Date().toISOString().slice(0, 10) };

export default function Expenses() {
  const [expenses, setExpenses] = useState([]);
  const [meta, setMeta] = useState(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [filterCat, setFilterCat] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [editId, setEditId] = useState(null);
  const [saving, setSaving] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [scanError, setScanError] = useState("");
  const [deleteTarget, setDeleteTarget] = useState(null);
  const receiptInputRef = useRef(null);

  const load = async () => {
    setLoading(true);
    const { data } = await getExpenses({ page, limit: 20, category: filterCat || undefined });
    setExpenses(data.data);
    setMeta(data.meta);
    setLoading(false);
  };

  useEffect(() => { load(); }, [page, filterCat]);

  const openAdd = () => { setForm(EMPTY_FORM); setEditId(null); setScanError(""); setShowModal(true); };
  const openEdit = (exp) => {
    setForm({ category: exp.category, description: exp.description, vendor: exp.vendor ?? "", amount: String(exp.amount), date: exp.date });
    setEditId(exp.id);
    setShowModal(true);
  };

  const handleScanReceipt = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";
    setScanning(true);
    setScanError("");
    try {
      const { base64, mediaType } = await compressImage(file);
      const { data } = await categorizeExpense(base64, mediaType);
      const r = data;
      setForm((prev) => ({
        ...prev,
        category: r.category || prev.category,
        description: r.description || prev.description,
        vendor: r.vendor || prev.vendor,
        amount: r.amount != null ? String(r.amount) : prev.amount,
        date: r.date || prev.date,
      }));
    } catch (err) {
      setScanError(err.response?.data?.detail ?? "Receipt scan failed. Try again.");
    } finally {
      setScanning(false);
    }
  };

  const handleSave = async () => {
    if (!form.description || !form.amount || !form.date) return;
    setSaving(true);
    const payload = { ...form, amount: parseFloat(form.amount), vendor: form.vendor || null };
    try {
      if (editId) await updateExpense(editId, payload);
      else await createExpense(payload);
      setShowModal(false);
      load();
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    await deleteExpense(deleteTarget.id);
    setDeleteTarget(null);
    load();
  };

  const totalThisPage = expenses.reduce((s, e) => s + Number(e.amount), 0);

  return (
    <div className="p-4 md:p-6 max-w-4xl mx-auto space-y-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Expenses</h1>
          {meta && <p className="text-xs text-gray-400">{meta.total} total expense{meta.total !== 1 ? "s" : ""}</p>}
        </div>
        <button className="btn-primary" onClick={openAdd}><Plus size={16} /> Add Expense</button>
      </div>

      {/* Category filter */}
      <div className="flex gap-2 flex-wrap">
        {["", ...CATEGORIES].map((cat) => (
          <button
            key={cat}
            onClick={() => { setFilterCat(cat); setPage(1); }}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-colors ${filterCat === cat ? "bg-green-600 text-white" : "bg-white text-gray-600 border border-gray-200 hover:border-green-300"}`}
          >
            {cat || "All"}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex h-48 items-center justify-center"><Spinner size="lg" /></div>
      ) : expenses.length === 0 ? (
        <div className="card p-10 text-center text-sm text-gray-400">No expenses yet. Add your first one.</div>
      ) : (
        <>
          <div className="card overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-left text-xs text-gray-500 uppercase tracking-wide">
                <tr>
                  <th className="px-4 py-3">Date</th>
                  <th className="px-4 py-3">Description</th>
                  <th className="px-4 py-3 hidden sm:table-cell">Category</th>
                  <th className="px-4 py-3 hidden sm:table-cell">Vendor</th>
                  <th className="px-4 py-3 text-right">Amount</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {expenses.map((exp) => (
                  <tr key={exp.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-500 whitespace-nowrap">{new Date(exp.date + "T00:00:00").toLocaleDateString("en-KE", { day: "2-digit", month: "short", year: "numeric" })}</td>
                    <td className="px-4 py-3 font-medium text-gray-900">{exp.description}</td>
                    <td className="px-4 py-3 hidden sm:table-cell"><span className="capitalize bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full text-xs">{exp.category}</span></td>
                    <td className="px-4 py-3 hidden sm:table-cell text-gray-400">{exp.vendor || "—"}</td>
                    <td className="px-4 py-3 text-right font-semibold text-red-600">{ksh(exp.amount)}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1 justify-end">
                        <button onClick={() => openEdit(exp)} className="p-1 text-gray-400 hover:text-gray-700"><Edit2 size={14} /></button>
                        <button onClick={() => setDeleteTarget(exp)} className="p-1 text-gray-400 hover:text-red-500"><Trash2 size={14} /></button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t-2 border-gray-200 bg-gray-50">
                  <td colSpan={4} className="px-4 py-3 text-xs text-gray-500 font-medium">Page total</td>
                  <td className="px-4 py-3 text-right font-bold text-red-700">{ksh(totalThisPage)}</td>
                  <td />
                </tr>
              </tfoot>
            </table>
          </div>

          {meta && meta.pages > 1 && (
            <div className="flex justify-center gap-2">
              <button disabled={page <= 1} onClick={() => setPage(p => p - 1)} className="btn-secondary text-xs disabled:opacity-40">Previous</button>
              <span className="text-sm text-gray-500 self-center">Page {page} of {meta.pages}</span>
              <button disabled={page >= meta.pages} onClick={() => setPage(p => p + 1)} className="btn-secondary text-xs disabled:opacity-40">Next</button>
            </div>
          )}
        </>
      )}

      {/* Add/Edit Modal */}
      <Modal open={showModal} onClose={() => setShowModal(false)} title={editId ? "Edit Expense" : "Add Expense"} size="sm">
        <div className="space-y-4">
          {!editId && (
            <div>
              <input
                ref={receiptInputRef}
                type="file"
                accept="image/*"
                capture="environment"
                className="hidden"
                onChange={handleScanReceipt}
              />
              <button
                type="button"
                onClick={() => receiptInputRef.current?.click()}
                disabled={scanning}
                className="w-full flex items-center justify-center gap-2 text-sm text-purple-700 bg-purple-50 hover:bg-purple-100 border border-purple-200 rounded-lg px-4 py-2.5 font-medium transition-colors disabled:opacity-50"
              >
                <ScanLine size={16} />
                {scanning ? "Scanning receipt…" : "Scan Receipt with AI"}
              </button>
              {scanError && <p className="text-xs text-red-600 mt-1">{scanError}</p>}
            </div>
          )}
          <div>
            <label className="label">Category</label>
            <select className="input capitalize" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
              {CATEGORIES.map((c) => <option key={c} value={c} className="capitalize">{c}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Description *</label>
            <input className="input" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="e.g. Monthly office rent" />
          </div>
          <div>
            <label className="label">Vendor</label>
            <input className="input" value={form.vendor} onChange={(e) => setForm({ ...form, vendor: e.target.value })} placeholder="Optional" />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="label">Amount (KSh) *</label>
              <input className="input" type="number" min="0" step="0.01" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} />
            </div>
            <div>
              <label className="label">Date *</label>
              <input className="input" type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} />
            </div>
          </div>
          <div className="flex gap-2 justify-end pt-1">
            <button className="btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
            <button className="btn-primary" onClick={handleSave} disabled={saving}>
              {saving ? "Saving…" : editId ? "Save Changes" : "Add Expense"}
            </button>
          </div>
        </div>
      </Modal>

      <ConfirmDialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
        title="Delete Expense"
        message={`Delete "${deleteTarget?.description}"? This cannot be undone.`}
        danger
      />
    </div>
  );
}
