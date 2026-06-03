import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getClients, createClient, deleteClient } from "../../api/clients";
import { phone, statusBadgeClass } from "../../utils/formatters";
import { Plus, Search, Trash2, ChevronRight } from "lucide-react";
import Spinner from "../../components/ui/Spinner";
import Modal from "../../components/ui/Modal";
import ConfirmDialog from "../../components/ui/ConfirmDialog";
import Pagination from "../../components/ui/Pagination";
import EmptyState from "../../components/ui/EmptyState";
import { Users } from "lucide-react";

function ClientForm({ onSave, onClose }) {
  const [form, setForm] = useState({ name: "", email: "", phone: "", address: "", sms_consent: false });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = {
        ...form,
        email: form.email || null,
        phone: form.phone || null,
        address: form.address || null,
      };
      await createClient(payload);
      onSave();
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) {
        setError(detail.map((d) => d.msg).join("; "));
      } else {
        setError(detail ?? "Failed to save client");
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && <div className="bg-red-50 text-red-700 text-sm px-3 py-2 rounded-lg">{error}</div>}
      <div>
        <label className="label">Name *</label>
        <input className="input" placeholder="Acme Ltd" value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })} required />
      </div>
      <div>
        <label className="label">Email</label>
        <input className="input" type="email" placeholder="billing@acme.co.ke" value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })} />
      </div>
      <div>
        <label className="label">Phone (M-Pesa)</label>
        <input className="input" placeholder="0712345678 or 254712345678" value={form.phone}
          onChange={(e) => setForm({ ...form, phone: e.target.value })} />
      </div>
      <div>
        <label className="label">Address</label>
        <textarea className="input" rows={2} placeholder="Nairobi, Kenya" value={form.address}
          onChange={(e) => setForm({ ...form, address: e.target.value })} />
      </div>
      {form.phone && (
        <label className="flex items-start gap-2.5 cursor-pointer select-none">
          <input
            type="checkbox"
            className="mt-0.5 accent-green-600"
            checked={form.sms_consent}
            onChange={(e) => setForm({ ...form, sms_consent: e.target.checked })}
          />
          <span className="text-xs text-gray-600">
            Client consents to receive SMS notifications (invoice alerts, payment confirmations, reminders) at the phone number above. Required by the Kenya Data Protection Act 2019 to send SMS.
          </span>
        </label>
      )}
      <div className="flex justify-end gap-2 pt-2">
        <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
        <button type="submit" className="btn-primary" disabled={saving}>
          {saving ? "Saving…" : "Save Client"}
        </button>
      </div>
    </form>
  );
}

export default function ClientList() {
  const navigate = useNavigate();
  const [clients, setClients] = useState([]);
  const [meta, setMeta] = useState(null);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);

  const load = () => {
    setLoading(true);
    getClients({ page, limit: 20, search: search || undefined })
      .then(({ data }) => { setClients(data.data); setMeta(data.meta); })
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [page, search]);

  const handleDelete = async (id) => {
    await deleteClient(id);
    load();
  };

  return (
    <div className="p-4 md:p-6 max-w-5xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Clients</h1>
        <button className="btn-primary" onClick={() => setShowForm(true)}>
          <Plus size={16} /> New Client
        </button>
      </div>

      <div className="relative">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          className="input pl-9"
          placeholder="Search clients…"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
        />
      </div>

      <div className="card overflow-hidden">
        {loading ? (
          <div className="flex h-48 items-center justify-center"><Spinner /></div>
        ) : clients.length === 0 ? (
          <EmptyState icon={Users} title="No clients yet" description="Add your first client to get started"
            action={<button className="btn-primary" onClick={() => setShowForm(true)}><Plus size={16} />New Client</button>} />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-left text-xs text-gray-500 uppercase tracking-wide">
                  <tr>
                    <th className="px-4 py-3">Name</th>
                    <th className="px-4 py-3 hidden sm:table-cell">Phone</th>
                    <th className="px-4 py-3 hidden md:table-cell">Email</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3 w-20" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {clients.map((c) => (
                    <tr key={c.id} className="hover:bg-gray-50 cursor-pointer"
                      onClick={() => navigate(`/clients/${c.id}`)}>
                      <td className="px-4 py-3 font-medium text-gray-900">{c.name}</td>
                      <td className="px-4 py-3 text-gray-500 hidden sm:table-cell">{phone(c.phone)}</td>
                      <td className="px-4 py-3 text-gray-500 hidden md:table-cell">{c.email}</td>
                      <td className="px-4 py-3"><span className={statusBadgeClass(c.status)}>{c.status}</span></td>
                      <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center gap-1">
                          <button className="p-1 text-gray-400 hover:text-red-600"
                            onClick={() => setDeleteTarget(c)}>
                            <Trash2 size={15} />
                          </button>
                          <ChevronRight size={15} className="text-gray-300" />
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination meta={meta} onPageChange={setPage} />
          </>
        )}
      </div>

      <Modal open={showForm} onClose={() => setShowForm(false)} title="New Client">
        <ClientForm onSave={() => { setShowForm(false); load(); }} onClose={() => setShowForm(false)} />
      </Modal>

      <ConfirmDialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => handleDelete(deleteTarget.id)}
        title="Delete Client"
        message={`Delete ${deleteTarget?.name}? This cannot be undone.`}
        danger
      />
    </div>
  );
}
