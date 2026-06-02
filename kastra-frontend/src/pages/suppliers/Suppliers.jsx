import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  getSuppliers, createSupplier, updateSupplier, deleteSupplier,
  getSupplierRequests, deleteSupplierRequest,
} from "../../api/suppliers";
import { Plus, Edit2, Trash2, FileText, ArrowRight, CheckCircle, Clock, Users } from "lucide-react";
import Modal from "../../components/ui/Modal";
import ConfirmDialog from "../../components/ui/ConfirmDialog";
import Spinner from "../../components/ui/Spinner";

const EMPTY_SUPPLIER = { name: "", company_name: "", email: "", phone: "", notes: "" };

function SupplierForm({ initial, onSave, onClose }) {
  const [form, setForm] = useState(initial ?? EMPTY_SUPPLIER);
  const [saving, setSaving] = useState(false);
  const f = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const handleSave = async () => {
    if (!form.name) return;
    setSaving(true);
    await onSave({ ...form, company_name: form.company_name || null, email: form.email || null, phone: form.phone || null, notes: form.notes || null });
    setSaving(false);
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label">Contact Name *</label>
          <input className="input" value={form.name} onChange={f("name")} placeholder="e.g. James Mwangi" />
        </div>
        <div>
          <label className="label">Company Name</label>
          <input className="input" value={form.company_name} onChange={f("company_name")} placeholder="e.g. Nairobi Hardware Ltd" />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label">Phone</label>
          <input className="input" value={form.phone} onChange={f("phone")} placeholder="254712345678" />
        </div>
        <div>
          <label className="label">Email</label>
          <input className="input" type="email" value={form.email} onChange={f("email")} placeholder="supplier@email.com" />
        </div>
      </div>
      <div>
        <label className="label">Notes <span className="text-gray-400 font-normal">(optional)</span></label>
        <textarea className="input" rows={2} value={form.notes} onChange={f("notes")} placeholder="What they supply, payment terms, etc." />
      </div>
      <div className="flex gap-2 justify-end pt-1">
        <button className="btn-secondary" onClick={onClose}>Cancel</button>
        <button className="btn-primary" onClick={handleSave} disabled={saving || !form.name}>
          {saving ? "Saving…" : initial ? "Save Changes" : "Add Supplier"}
        </button>
      </div>
    </div>
  );
}

export default function Suppliers() {
  const navigate = useNavigate();
  const [tab, setTab] = useState("suppliers"); // suppliers | requests
  const [suppliers, setSuppliers] = useState([]);
  const [requests, setRequests] = useState([]);
  const [loadingS, setLoadingS] = useState(true);
  const [loadingR, setLoadingR] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editTarget, setEditTarget] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleteReqTarget, setDeleteReqTarget] = useState(null);

  const loadSuppliers = async () => {
    setLoadingS(true);
    const { data } = await getSuppliers();
    setSuppliers(data);
    setLoadingS(false);
  };

  const loadRequests = async () => {
    setLoadingR(true);
    const { data } = await getSupplierRequests();
    setRequests(data.data ?? []);
    setLoadingR(false);
  };

  useEffect(() => { loadSuppliers(); loadRequests(); }, []);

  const openAdd = () => { setEditTarget(null); setShowModal(true); };
  const openEdit = (s) => { setEditTarget(s); setShowModal(true); };

  const handleSaveSupplier = async (payload) => {
    if (editTarget) await updateSupplier(editTarget.id, payload);
    else await createSupplier(payload);
    setShowModal(false);
    loadSuppliers();
  };

  const handleDeleteSupplier = async () => {
    await deleteSupplier(deleteTarget.id);
    setDeleteTarget(null);
    loadSuppliers();
  };

  const handleDeleteRequest = async () => {
    await deleteSupplierRequest(deleteReqTarget.id);
    setDeleteReqTarget(null);
    loadRequests();
  };

  return (
    <div className="p-4 md:p-6 max-w-4xl mx-auto space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Suppliers</h1>
          <p className="text-xs text-gray-400">Manage your suppliers and send them price requests.</p>
        </div>
        <div className="flex gap-2">
          {tab === "suppliers" && (
            <button className="btn-primary" onClick={openAdd}><Plus size={15} /> Add Supplier</button>
          )}
          {tab === "requests" && (
            <button className="btn-primary" onClick={() => navigate("/suppliers/requests/new")}>
              <Plus size={15} /> New Price Request
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200">
        {[
          { key: "suppliers", label: `Suppliers (${suppliers.length})`, icon: Users },
          { key: "requests", label: `Price Requests (${requests.length})`, icon: FileText },
        ].map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              tab === key ? "border-green-600 text-green-700" : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            <Icon size={14} /> {label}
          </button>
        ))}
      </div>

      {/* Suppliers tab */}
      {tab === "suppliers" && (
        loadingS ? (
          <div className="flex h-48 items-center justify-center"><Spinner size="lg" /></div>
        ) : suppliers.length === 0 ? (
          <div className="card p-10 text-center text-sm text-gray-400">
            No suppliers yet. Add your first supplier to start requesting prices.
          </div>
        ) : (
          <div className="card divide-y divide-gray-100">
            {suppliers.map((s) => (
              <div key={s.id} className="flex items-center gap-4 px-4 py-3">
                <div className="h-9 w-9 rounded-full bg-purple-100 flex items-center justify-center shrink-0">
                  <span className="text-sm font-bold text-purple-700">{s.name[0].toUpperCase()}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-900">{s.name}</p>
                  {s.company_name && <p className="text-xs text-gray-500">{s.company_name}</p>}
                  <div className="flex gap-3 text-xs text-gray-400 mt-0.5">
                    {s.phone && <span>{s.phone}</span>}
                    {s.email && <span>{s.email}</span>}
                  </div>
                </div>
                <div className="flex gap-1 shrink-0">
                  <button onClick={() => openEdit(s)} className="p-1.5 text-gray-400 hover:text-gray-700"><Edit2 size={14} /></button>
                  <button onClick={() => setDeleteTarget(s)} className="p-1.5 text-gray-400 hover:text-red-500"><Trash2 size={14} /></button>
                </div>
              </div>
            ))}
          </div>
        )
      )}

      {/* Requests tab */}
      {tab === "requests" && (
        loadingR ? (
          <div className="flex h-48 items-center justify-center"><Spinner size="lg" /></div>
        ) : requests.length === 0 ? (
          <div className="card p-10 text-center text-sm text-gray-400">
            No price requests yet. Create one to start comparing supplier prices.
          </div>
        ) : (
          <div className="card divide-y divide-gray-100">
            {requests.map((r) => (
              <div key={r.id} className="flex items-center gap-4 px-4 py-3.5 hover:bg-gray-50 cursor-pointer group"
                onClick={() => navigate(`/suppliers/requests/${r.id}`)}>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="font-medium text-gray-900">{r.title}</p>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                      r.status === "open" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"
                    }`}>{r.status}</span>
                  </div>
                  <div className="flex gap-4 text-xs text-gray-400 mt-0.5">
                    <span>{r.items_count} item{r.items_count !== 1 ? "s" : ""}</span>
                    <span className="flex items-center gap-1">
                      {r.responses_count > 0
                        ? <><CheckCircle size={11} className="text-green-500" /> {r.responses_count} response{r.responses_count !== 1 ? "s" : ""}</>
                        : <><Clock size={11} /> No responses yet</>}
                    </span>
                    <span>{new Date(r.created_at).toLocaleDateString("en-KE", { day: "2-digit", month: "short", year: "numeric" })}</span>
                  </div>
                </div>
                <ArrowRight size={16} className="text-gray-300 group-hover:text-gray-500 shrink-0" />
                <button
                  onClick={(e) => { e.stopPropagation(); setDeleteReqTarget(r); }}
                  className="p-1.5 text-gray-300 hover:text-red-500 shrink-0"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        )
      )}

      {/* Supplier modal */}
      <Modal open={showModal} onClose={() => setShowModal(false)} title={editTarget ? "Edit Supplier" : "Add Supplier"}>
        <SupplierForm
          initial={editTarget ? { name: editTarget.name, company_name: editTarget.company_name ?? "", email: editTarget.email ?? "", phone: editTarget.phone ?? "", notes: editTarget.notes ?? "" } : null}
          onSave={handleSaveSupplier}
          onClose={() => setShowModal(false)}
        />
      </Modal>

      <ConfirmDialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDeleteSupplier}
        title="Remove Supplier"
        message={`Remove "${deleteTarget?.name}"? Their price history will be kept.`}
        danger
      />
      <ConfirmDialog
        open={!!deleteReqTarget}
        onClose={() => setDeleteReqTarget(null)}
        onConfirm={handleDeleteRequest}
        title="Delete Price Request"
        message={`Delete "${deleteReqTarget?.title}"? All supplier responses will also be deleted.`}
        danger
      />
    </div>
  );
}
