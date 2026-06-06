import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getPayrollRuns, createPayrollRun, deletePayrollRun } from "../../api/payroll";
import { ksh } from "../../utils/formatters";
import { Plus, Trash2, ArrowRight, CheckCircle, Clock, Wallet } from "lucide-react";
import Modal from "../../components/ui/Modal";
import ConfirmDialog from "../../components/ui/ConfirmDialog";
import Spinner from "../../components/ui/Spinner";

const MONTH_NAMES = [
  "", "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

const now = new Date();

function NewRunForm({ onSave, onClose, error }) {
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    await onSave({ period_year: Number(year), period_month: Number(month), notes: notes || null });
    setSaving(false);
  };

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-500">
        This will generate a payslip for every active employee, computing PAYE, NSSF, SHIF and the
        Affordable Housing Levy from their current basic salary and allowances.
      </p>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label">Month</label>
          <select className="input" value={month} onChange={(e) => setMonth(e.target.value)}>
            {MONTH_NAMES.slice(1).map((name, i) => (
              <option key={i + 1} value={i + 1}>{name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">Year</label>
          <input className="input" type="number" value={year} onChange={(e) => setYear(e.target.value)} />
        </div>
      </div>
      <div>
        <label className="label">Notes <span className="text-gray-400 font-normal">(optional)</span></label>
        <textarea className="input" rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="e.g. Mid-year bonus included" />
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className="flex gap-2 justify-end pt-1">
        <button className="btn-secondary" onClick={onClose}>Cancel</button>
        <button className="btn-primary" onClick={handleSave} disabled={saving}>
          {saving ? "Generating…" : "Generate Payroll Run"}
        </button>
      </div>
    </div>
  );
}

export default function PayrollRuns() {
  const navigate = useNavigate();
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [error, setError] = useState("");
  const [deleteTarget, setDeleteTarget] = useState(null);

  const load = async () => {
    setLoading(true);
    const { data } = await getPayrollRuns();
    setRuns(data);
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async (payload) => {
    setError("");
    try {
      const { data } = await createPayrollRun(payload);
      setShowModal(false);
      navigate(`/payroll/runs/${data.data.id}`);
    } catch (err) {
      setError(err?.response?.data?.detail ?? "Could not generate payroll run.");
    }
  };

  const handleDelete = async () => {
    await deletePayrollRun(deleteTarget.id);
    setDeleteTarget(null);
    load();
  };

  return (
    <div className="p-4 md:p-6 max-w-4xl mx-auto space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Payroll</h1>
          <p className="text-xs text-gray-400">Generate monthly payslips and your payroll register for staff payouts.</p>
        </div>
        <button className="btn-primary" onClick={() => { setError(""); setShowModal(true); }}>
          <Plus size={15} /> New Payroll Run
        </button>
      </div>

      {loading ? (
        <div className="flex h-48 items-center justify-center"><Spinner size="lg" /></div>
      ) : runs.length === 0 ? (
        <div className="card p-10 text-center text-sm text-gray-400">
          <Wallet size={28} className="mx-auto mb-2 text-gray-300" />
          No payroll runs yet. Add your employees, then generate your first monthly run.
        </div>
      ) : (
        <div className="card divide-y divide-gray-100">
          {runs.map((r) => (
            <div key={r.id} className="flex items-center gap-4 px-4 py-3.5 hover:bg-gray-50 cursor-pointer group"
              onClick={() => navigate(`/payroll/runs/${r.id}`)}>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <p className="font-medium text-gray-900">{MONTH_NAMES[r.period_month]} {r.period_year}</p>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    r.status === "finalized" ? "bg-green-100 text-green-700" : "bg-orange-100 text-orange-700"
                  }`}>
                    {r.status === "finalized"
                      ? <span className="inline-flex items-center gap-1"><CheckCircle size={11} /> Finalized</span>
                      : <span className="inline-flex items-center gap-1"><Clock size={11} /> Draft</span>}
                  </span>
                </div>
                <div className="flex gap-4 text-xs text-gray-400 mt-0.5">
                  <span>{r.employee_count} employee{r.employee_count !== 1 ? "s" : ""}</span>
                  <span>Net pay: {ksh(r.total_net_pay)}</span>
                </div>
              </div>
              <ArrowRight size={16} className="text-gray-300 group-hover:text-gray-500 shrink-0" />
              {r.status !== "finalized" && (
                <button
                  onClick={(e) => { e.stopPropagation(); setDeleteTarget(r); }}
                  className="p-1.5 text-gray-300 hover:text-red-500 shrink-0"
                >
                  <Trash2 size={14} />
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      <Modal open={showModal} onClose={() => setShowModal(false)} title="New Payroll Run">
        <NewRunForm onSave={handleCreate} onClose={() => setShowModal(false)} error={error} />
      </Modal>

      <ConfirmDialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
        title="Delete Payroll Run"
        message={`Delete the ${deleteTarget ? `${MONTH_NAMES[deleteTarget.period_month]} ${deleteTarget.period_year}` : ""} payroll run and all its payslips? This cannot be undone.`}
        danger
      />
    </div>
  );
}
