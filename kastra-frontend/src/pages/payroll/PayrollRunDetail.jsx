import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  getPayrollRun, finalizePayrollRun, exportPayrollRunCsv, downloadPayslipPdf,
} from "../../api/payroll";
import { ksh } from "../../utils/formatters";
import { ArrowLeft, CheckCircle, Clock, Download, FileText, Lock } from "lucide-react";
import ConfirmDialog from "../../components/ui/ConfirmDialog";
import Spinner from "../../components/ui/Spinner";

const MONTH_NAMES = [
  "", "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function PayrollRunDetail() {
  const { id } = useParams();
  const [run, setRun] = useState(null);
  const [loading, setLoading] = useState(true);
  const [confirmFinalize, setConfirmFinalize] = useState(false);
  const [finalizing, setFinalizing] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [pdfTarget, setPdfTarget] = useState(null);

  const load = async () => {
    setLoading(true);
    const { data } = await getPayrollRun(id);
    setRun(data.data);
    setLoading(false);
  };

  useEffect(() => { load(); }, [id]);

  const handleFinalize = async () => {
    setFinalizing(true);
    try {
      const { data } = await finalizePayrollRun(id);
      setRun(data.data);
    } finally {
      setFinalizing(false);
      setConfirmFinalize(false);
    }
  };

  const handleExportCsv = async () => {
    setExporting(true);
    try {
      const { data } = await exportPayrollRunCsv(id);
      downloadBlob(data, `kastra-payroll-register-${run.period_year}-${String(run.period_month).padStart(2, "0")}.csv`);
    } finally {
      setExporting(false);
    }
  };

  const handleDownloadPdf = async (payslip) => {
    setPdfTarget(payslip.id);
    try {
      const { data } = await downloadPayslipPdf(id, payslip.id);
      downloadBlob(data, `payslip-${payslip.employee_no}-${MONTH_NAMES[run.period_month]}-${run.period_year}.pdf`);
    } finally {
      setPdfTarget(null);
    }
  };

  if (loading || !run) {
    return <div className="flex h-64 items-center justify-center"><Spinner size="lg" /></div>;
  }

  const totals = run.payslips.reduce((acc, p) => ({
    gross: acc.gross + Number(p.gross_pay),
    deductions: acc.deductions + Number(p.total_deductions),
    net: acc.net + Number(p.net_pay),
  }), { gross: 0, deductions: 0, net: 0 });

  return (
    <div className="p-4 md:p-6 max-w-5xl mx-auto space-y-5">
      <div className="flex items-center gap-3">
        <Link to="/payroll" className="p-1.5 -ml-1.5 text-gray-400 hover:text-gray-700"><ArrowLeft size={18} /></Link>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-xl font-bold text-gray-900">{MONTH_NAMES[run.period_month]} {run.period_year} Payroll</h1>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
              run.status === "finalized" ? "bg-green-100 text-green-700" : "bg-orange-100 text-orange-700"
            }`}>
              {run.status === "finalized"
                ? <span className="inline-flex items-center gap-1"><CheckCircle size={11} /> Finalized</span>
                : <span className="inline-flex items-center gap-1"><Clock size={11} /> Draft</span>}
            </span>
          </div>
          {run.notes && <p className="text-xs text-gray-400 mt-0.5">{run.notes}</p>}
        </div>
        <div className="flex gap-2 shrink-0">
          <button className="btn-secondary" onClick={handleExportCsv} disabled={exporting}>
            <Download size={14} /> {exporting ? "Exporting…" : "Export Register (CSV)"}
          </button>
          {run.status !== "finalized" && (
            <button className="btn-primary" onClick={() => setConfirmFinalize(true)}>
              <Lock size={14} /> Finalize Run
            </button>
          )}
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="card p-4">
          <p className="text-xs text-gray-400 uppercase tracking-wide">Gross Pay</p>
          <p className="text-lg font-bold text-gray-900 mt-1">{ksh(totals.gross)}</p>
        </div>
        <div className="card p-4">
          <p className="text-xs text-gray-400 uppercase tracking-wide">Total Deductions</p>
          <p className="text-lg font-bold text-gray-900 mt-1">{ksh(totals.deductions)}</p>
        </div>
        <div className="card p-4">
          <p className="text-xs text-gray-400 uppercase tracking-wide">Net Pay (to disburse)</p>
          <p className="text-lg font-bold text-green-700 mt-1">{ksh(totals.net)}</p>
        </div>
      </div>

      <div className="card p-4 bg-blue-50 border-blue-200 text-sm text-blue-800">
        Kastra generates payslips and a payroll register — it does not move money. Export the CSV register
        below and pay your staff via your own bank or M-Pesa.
      </div>

      {run.status !== "finalized" && (
        <div className="card p-4 bg-orange-50 border-orange-200 text-sm text-orange-800">
          This run is in <strong>draft</strong>. Review the payslips below, then finalize once you're ready —
          finalized runs are locked and form your permanent payroll record.
        </div>
      )}

      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-2.5 font-medium text-gray-600">Employee</th>
                <th className="text-right px-4 py-2.5 font-medium text-gray-600">Gross Pay</th>
                <th className="text-right px-4 py-2.5 font-medium text-gray-600">PAYE</th>
                <th className="text-right px-4 py-2.5 font-medium text-gray-600">NSSF</th>
                <th className="text-right px-4 py-2.5 font-medium text-gray-600">SHIF</th>
                <th className="text-right px-4 py-2.5 font-medium text-gray-600">Housing Levy</th>
                <th className="text-right px-4 py-2.5 font-medium text-gray-600">Net Pay</th>
                <th className="px-4 py-2.5"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {run.payslips.map((p) => (
                <tr key={p.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2.5">
                    <p className="font-medium text-gray-900">{p.employee_name}</p>
                    <p className="text-xs text-gray-400 font-mono">{p.employee_no}</p>
                  </td>
                  <td className="px-4 py-2.5 text-right text-gray-700">{ksh(p.gross_pay)}</td>
                  <td className="px-4 py-2.5 text-right text-gray-500">{ksh(p.paye)}</td>
                  <td className="px-4 py-2.5 text-right text-gray-500">{ksh(p.nssf)}</td>
                  <td className="px-4 py-2.5 text-right text-gray-500">{ksh(p.shif)}</td>
                  <td className="px-4 py-2.5 text-right text-gray-500">{ksh(p.housing_levy)}</td>
                  <td className="px-4 py-2.5 text-right font-semibold text-gray-900">{ksh(p.net_pay)}</td>
                  <td className="px-4 py-2.5 text-right">
                    <button
                      className="inline-flex items-center gap-1.5 text-xs text-green-700 hover:text-green-800 font-medium disabled:opacity-50"
                      onClick={() => handleDownloadPdf(p)}
                      disabled={pdfTarget === p.id}
                    >
                      <FileText size={13} /> {pdfTarget === p.id ? "Preparing…" : "Payslip PDF"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <ConfirmDialog
        open={confirmFinalize}
        onClose={() => setConfirmFinalize(false)}
        onConfirm={handleFinalize}
        title="Finalize Payroll Run"
        message="Finalizing locks this run permanently — payslips can no longer be regenerated for this period. Make sure all employee details and salaries are correct first."
      />
      {finalizing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20">
          <div className="bg-white rounded-lg shadow-xl px-6 py-4 flex items-center gap-3">
            <Spinner size="sm" /> <span className="text-sm text-gray-600">Finalizing payroll run…</span>
          </div>
        </div>
      )}
    </div>
  );
}
