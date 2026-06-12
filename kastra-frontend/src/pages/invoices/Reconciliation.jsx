import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { CheckCircle, FileUp, Landmark, Loader, RefreshCw } from "lucide-react";
import { parseStatement, confirmMatches } from "../../api/reconciliation";
import { ksh, date } from "../../utils/formatters";

const CONFIDENCE_BADGE = {
  high: "bg-green-100 text-green-700",
  medium: "bg-amber-100 text-amber-700",
};

export default function Reconciliation() {
  const fileRef = useRef(null);
  const [parsing, setParsing] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  // selection: { [row]: { checked, invoiceId } }
  const [selection, setSelection] = useState({});
  const [confirming, setConfirming] = useState(false);
  const [summary, setSummary] = useState(null);

  const handleFile = async (file) => {
    if (!file) return;
    setParsing(true);
    setError("");
    setSummary(null);
    try {
      const { data } = await parseStatement(file);
      setResult(data);
      const initial = {};
      for (const t of data.transactions) {
        initial[t.row] = {
          checked: !!t.suggested_invoice_id,
          invoiceId: t.suggested_invoice_id || "",
        };
      }
      setSelection(initial);
    } catch (err) {
      setError(err.response?.data?.detail ?? "Could not parse the file");
      setResult(null);
    } finally {
      setParsing(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const setSel = (row, patch) =>
    setSelection((prev) => ({ ...prev, [row]: { ...prev[row], ...patch } }));

  const chosen = result
    ? result.transactions.filter((t) => selection[t.row]?.checked && selection[t.row]?.invoiceId)
    : [];

  const handleConfirm = async () => {
    setConfirming(true);
    setError("");
    try {
      const matches = chosen.map((t) => ({
        invoice_id: selection[t.row].invoiceId,
        amount: t.amount,
        reference: t.reference || null,
        paid_at: t.date || null,
        method: "mpesa",
      }));
      const { data } = await confirmMatches(matches);
      setSummary(data);
      setResult(null);
      setSelection({});
    } catch (err) {
      setError(err.response?.data?.detail ?? "Failed to record payments");
    } finally {
      setConfirming(false);
    }
  };

  return (
    <div className="p-4 md:p-6 max-w-5xl mx-auto space-y-5">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Payment Reconciliation</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Upload an M-Pesa or bank statement CSV. Kastra matches incoming payments to open
          invoices — you review and confirm before anything is recorded.
        </p>
      </div>

      {error && <div className="bg-red-50 text-red-700 text-sm px-3 py-2 rounded-lg">{error}</div>}

      {summary && (
        <div className="card p-4 bg-green-50 border-green-200">
          <div className="flex items-center gap-2 mb-1">
            <CheckCircle size={16} className="text-green-600" />
            <h2 className="text-sm font-semibold text-green-800">
              {summary.recorded} payment{summary.recorded === 1 ? "" : "s"} recorded
            </h2>
          </div>
          {summary.skipped.length > 0 && (
            <ul className="text-xs text-amber-700 mt-2 space-y-0.5">
              {summary.skipped.map((s, i) => (
                <li key={i}>• {s.invoice_id}: {s.reason}</li>
              ))}
            </ul>
          )}
          <Link to="/invoices" className="text-xs text-green-700 underline mt-2 inline-block">View invoices</Link>
        </div>
      )}

      {/* Upload */}
      <div
        className="card p-8 border-2 border-dashed border-gray-200 text-center cursor-pointer hover:border-green-300 transition-colors"
        onClick={() => fileRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => { e.preventDefault(); handleFile(e.dataTransfer.files?.[0]); }}
      >
        <input
          ref={fileRef}
          type="file"
          accept=".csv,text/csv"
          className="hidden"
          onChange={(e) => handleFile(e.target.files?.[0])}
        />
        {parsing ? (
          <div className="flex flex-col items-center gap-2 text-gray-500">
            <Loader size={28} className="animate-spin text-green-500" />
            <p className="text-sm">Parsing statement…</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2 text-gray-500">
            <Landmark size={28} className="text-green-500" />
            <p className="text-sm font-medium text-gray-700">Drop a statement CSV here, or click to browse</p>
            <p className="text-xs text-gray-400">
              Works with M-Pesa statement exports and bank CSVs (date, reference, details, amount)
            </p>
          </div>
        )}
      </div>

      {/* Parsed transactions */}
      {result && (
        <>
          <div className="card overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-gray-800">
                {result.transactions.length} incoming transaction{result.transactions.length === 1 ? "" : "s"}
              </h2>
              <span className="text-xs text-gray-400">
                {result.skipped_rows > 0 && `${result.skipped_rows} non-credit rows skipped · `}
                {result.open_invoices.length} open invoice{result.open_invoices.length === 1 ? "" : "s"}
              </span>
            </div>

            {result.transactions.length === 0 ? (
              <div className="px-4 py-6 text-center text-sm text-gray-400">
                No incoming payments found in this statement.
              </div>
            ) : (
              <div className="overflow-x-auto">
              <table className="w-full text-sm min-w-[640px]">
                <thead className="bg-gray-50 text-left text-xs text-gray-500 uppercase tracking-wide">
                  <tr>
                    <th className="px-4 py-2 w-8"></th>
                    <th className="px-4 py-2">Date</th>
                    <th className="px-4 py-2">Reference</th>
                    <th className="px-4 py-2">Details</th>
                    <th className="px-4 py-2 text-right">Amount</th>
                    <th className="px-4 py-2">Match to Invoice</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {result.transactions.map((t) => {
                    const sel = selection[t.row] ?? { checked: false, invoiceId: "" };
                    return (
                      <tr key={t.row} className={sel.checked ? "" : "opacity-60"}>
                        <td className="px-4 py-2.5">
                          <input
                            type="checkbox"
                            checked={sel.checked}
                            onChange={(e) => setSel(t.row, { checked: e.target.checked })}
                          />
                        </td>
                        <td className="px-4 py-2.5 text-gray-500 whitespace-nowrap">{t.date ? date(t.date) : "—"}</td>
                        <td className="px-4 py-2.5 font-mono text-xs text-gray-600">{t.reference || "—"}</td>
                        <td className="px-4 py-2.5 text-gray-600 max-w-[220px]">
                          <span className="truncate block" title={t.description}>{t.description || "—"}</span>
                          {t.match_reason && (
                            <span className={`inline-flex mt-1 px-1.5 py-0.5 rounded-full text-[10px] ${CONFIDENCE_BADGE[t.confidence] ?? "bg-gray-100 text-gray-500"}`}>
                              {t.match_reason}
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-2.5 text-right font-semibold text-green-700 whitespace-nowrap">{ksh(t.amount)}</td>
                        <td className="px-4 py-2.5">
                          <select
                            className="input text-xs w-full max-w-[220px]"
                            value={sel.invoiceId}
                            onChange={(e) => setSel(t.row, { invoiceId: e.target.value, checked: !!e.target.value })}
                          >
                            <option value="">— not matched —</option>
                            {result.open_invoices.map((inv) => (
                              <option key={inv.id} value={inv.id}>
                                {inv.id} · {inv.client_name} · bal {ksh(inv.balance_due)}
                              </option>
                            ))}
                          </select>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              </div>
            )}
          </div>

          <div className="flex items-center justify-between">
            <button className="btn-secondary" onClick={() => { setResult(null); setSelection({}); }}>
              <RefreshCw size={15} /> Start Over
            </button>
            <button className="btn-primary" onClick={handleConfirm} disabled={chosen.length === 0 || confirming}>
              {confirming ? <Loader size={15} className="animate-spin" /> : <FileUp size={15} />}
              {confirming ? "Recording…" : `Record ${chosen.length} Payment${chosen.length === 1 ? "" : "s"}`}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
