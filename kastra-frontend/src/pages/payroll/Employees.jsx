import { useEffect, useState } from "react";
import { getEmployees, createEmployee, updateEmployee, deleteEmployee } from "../../api/employees";
import { ksh } from "../../utils/formatters";
import { Plus, Edit2, Trash2, Users } from "lucide-react";
import Modal from "../../components/ui/Modal";
import ConfirmDialog from "../../components/ui/ConfirmDialog";
import Spinner from "../../components/ui/Spinner";

const EMPTY_EMPLOYEE = {
  employee_no: "", full_name: "", phone: "", email: "", job_title: "",
  employment_type: "permanent", basic_salary: "", allowances: "",
  national_id: "", kra_pin: "", nssf_no: "", shif_no: "",
  bank_name: "", bank_account_no: "", mpesa_number: "", date_joined: "",
};

const EMPLOYMENT_TYPES = [
  { value: "permanent", label: "Permanent" },
  { value: "contract", label: "Contract" },
  { value: "casual", label: "Casual" },
];

function EmployeeForm({ initial, onSave, onClose }) {
  const [form, setForm] = useState(initial ?? EMPTY_EMPLOYEE);
  const [saving, setSaving] = useState(false);
  const f = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const handleSave = async () => {
    if (!form.employee_no || !form.full_name) return;
    setSaving(true);
    const payload = {
      ...form,
      basic_salary: form.basic_salary === "" ? 0 : Number(form.basic_salary),
      allowances: form.allowances === "" ? 0 : Number(form.allowances),
      date_joined: form.date_joined || null,
    };
    for (const k of ["national_id", "kra_pin", "nssf_no", "shif_no", "phone", "email",
      "job_title", "bank_name", "bank_account_no", "mpesa_number"]) {
      if (payload[k] === "") payload[k] = null;
    }
    await onSave(payload);
    setSaving(false);
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="label">Employee No *</label>
          <input className="input" value={form.employee_no} onChange={f("employee_no")} placeholder="e.g. EMP-001" />
        </div>
        <div>
          <label className="label">Full Name *</label>
          <input className="input" value={form.full_name} onChange={f("full_name")} placeholder="e.g. Jane Wanjiru" />
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div>
          <label className="label">Job Title</label>
          <input className="input" value={form.job_title} onChange={f("job_title")} placeholder="e.g. Site Supervisor" />
        </div>
        <div>
          <label className="label">Employment Type</label>
          <select className="input" value={form.employment_type} onChange={f("employment_type")}>
            {EMPLOYMENT_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Date Joined</label>
          <input className="input" type="date" value={form.date_joined ?? ""} onChange={f("date_joined")} />
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="label">Basic Salary (KES) *</label>
          <input className="input" type="number" min="0" step="0.01" value={form.basic_salary} onChange={f("basic_salary")} placeholder="0.00" />
        </div>
        <div>
          <label className="label">Allowances (KES)</label>
          <input className="input" type="number" min="0" step="0.01" value={form.allowances} onChange={f("allowances")} placeholder="0.00" />
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="label">Phone</label>
          <input className="input" value={form.phone ?? ""} onChange={f("phone")} placeholder="254712345678" />
        </div>
        <div>
          <label className="label">Email</label>
          <input className="input" type="email" value={form.email ?? ""} onChange={f("email")} placeholder="employee@email.com" />
        </div>
      </div>

      <p className="label !mb-1 pt-1 text-gray-400">Statutory IDs (optional)</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="label">National ID</label>
          <input className="input" value={form.national_id ?? ""} onChange={f("national_id")} />
        </div>
        <div>
          <label className="label">KRA PIN</label>
          <input className="input" value={form.kra_pin ?? ""} onChange={f("kra_pin")} placeholder="A000000000X" />
        </div>
        <div>
          <label className="label">NSSF No.</label>
          <input className="input" value={form.nssf_no ?? ""} onChange={f("nssf_no")} />
        </div>
        <div>
          <label className="label">SHIF No.</label>
          <input className="input" value={form.shif_no ?? ""} onChange={f("shif_no")} />
        </div>
      </div>

      <p className="label !mb-1 pt-1 text-gray-400">Payout Details (optional — for your reference when paying staff)</p>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div>
          <label className="label">Bank Name</label>
          <input className="input" value={form.bank_name ?? ""} onChange={f("bank_name")} />
        </div>
        <div>
          <label className="label">Bank Account No.</label>
          <input className="input" value={form.bank_account_no ?? ""} onChange={f("bank_account_no")} />
        </div>
        <div>
          <label className="label">M-Pesa Number</label>
          <input className="input" value={form.mpesa_number ?? ""} onChange={f("mpesa_number")} placeholder="254712345678" />
        </div>
      </div>

      <div className="flex gap-2 justify-end pt-1">
        <button className="btn-secondary" onClick={onClose}>Cancel</button>
        <button className="btn-primary" onClick={handleSave} disabled={saving || !form.employee_no || !form.full_name}>
          {saving ? "Saving…" : initial ? "Save Changes" : "Add Employee"}
        </button>
      </div>
    </div>
  );
}

export default function Employees() {
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editTarget, setEditTarget] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);

  const load = async () => {
    setLoading(true);
    const { data } = await getEmployees();
    setEmployees(data);
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const openAdd = () => { setEditTarget(null); setShowModal(true); };
  const openEdit = (e) => { setEditTarget(e); setShowModal(true); };

  const handleSave = async (payload) => {
    if (editTarget) await updateEmployee(editTarget.id, payload);
    else await createEmployee(payload);
    setShowModal(false);
    load();
  };

  const handleDelete = async () => {
    await deleteEmployee(deleteTarget.id);
    setDeleteTarget(null);
    load();
  };

  return (
    <div className="p-4 md:p-6 max-w-4xl mx-auto space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Employees</h1>
          <p className="text-xs text-gray-400">Manage your staff records and salary details for payroll.</p>
        </div>
        <button className="btn-primary" onClick={openAdd}><Plus size={15} /> Add Employee</button>
      </div>

      {loading ? (
        <div className="flex h-48 items-center justify-center"><Spinner size="lg" /></div>
      ) : employees.length === 0 ? (
        <div className="card p-10 text-center text-sm text-gray-400">
          <Users size={28} className="mx-auto mb-2 text-gray-300" />
          No employees yet. Add your staff to start running payroll.
        </div>
      ) : (
        <div className="card divide-y divide-gray-100">
          {employees.map((e) => (
            <div key={e.id} className="flex items-center gap-4 px-4 py-3">
              <div className="h-9 w-9 rounded-full bg-green-100 flex items-center justify-center shrink-0">
                <span className="text-sm font-bold text-green-700">{e.full_name[0].toUpperCase()}</span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <p className="font-medium text-gray-900">{e.full_name}</p>
                  <span className="text-xs text-gray-400 font-mono">{e.employee_no}</span>
                  <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-gray-100 text-gray-500 capitalize">
                    {e.employment_type}
                  </span>
                </div>
                <div className="flex gap-3 text-xs text-gray-400 mt-0.5">
                  {e.job_title && <span>{e.job_title}</span>}
                  {e.phone && <span>{e.phone}</span>}
                </div>
              </div>
              <div className="text-right shrink-0">
                <p className="text-sm font-semibold text-gray-900">{ksh(Number(e.basic_salary) + Number(e.allowances))}</p>
                <p className="text-xs text-gray-400">gross / month</p>
              </div>
              <div className="flex gap-1 shrink-0">
                <button onClick={() => openEdit(e)} className="p-1.5 text-gray-400 hover:text-gray-700"><Edit2 size={14} /></button>
                <button onClick={() => setDeleteTarget(e)} className="p-1.5 text-gray-400 hover:text-red-500"><Trash2 size={14} /></button>
              </div>
            </div>
          ))}
        </div>
      )}

      <Modal open={showModal} onClose={() => setShowModal(false)} title={editTarget ? "Edit Employee" : "Add Employee"} size="lg">
        <EmployeeForm
          initial={editTarget ? {
            ...EMPTY_EMPLOYEE,
            ...editTarget,
            basic_salary: String(editTarget.basic_salary ?? ""),
            allowances: String(editTarget.allowances ?? ""),
            date_joined: editTarget.date_joined ?? "",
          } : null}
          onSave={handleSave}
          onClose={() => setShowModal(false)}
        />
      </Modal>

      <ConfirmDialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
        title="Remove Employee"
        message={`Remove "${deleteTarget?.full_name}"? Their past payslip records will be kept.`}
        danger
      />
    </div>
  );
}
