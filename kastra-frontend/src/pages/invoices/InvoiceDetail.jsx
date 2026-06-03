import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getInvoice, markPaid, mpesaPay, sendReminder, submitEtims, sendInvoiceEmail } from "../../api/invoices";
import { getOrganization } from "../../api/organization";
import { getInvoicePayments, recordPayment, deletePayment } from "../../api/invoice_payments";
import { createInvoiceExpense, updateInvoiceExpense, deleteInvoiceExpense } from "../../api/expenses";
import { ksh, date, phone, statusBadgeClass, normalizePhone } from "../../utils/formatters";
import { publicOrigin } from "../../utils/publicUrl";
import {
  ArrowLeft, MessageCircle, Smartphone, CheckCircle, FileDown, ShieldCheck,
  Loader, Copy, Plus, Trash2, Mail, CreditCard, Link2, Bell, TrendingUp, TrendingDown, Receipt,
} from "lucide-react";
import Spinner from "../../components/ui/Spinner";
import Modal from "../../components/ui/Modal";
import ConfirmDialog from "../../components/ui/ConfirmDialog";
import PDFPreviewModal from "../../components/ui/PDFPreviewModal";
import InvoiceDocument from "../../components/documents/InvoiceDocument";

const JOB_EXPENSE_CATEGORIES = [
  { value: "materials", label: "Materials / Buying Price" },
  { value: "labour", label: "Labour" },
  { value: "lunch", label: "Lunch / Meals" },
  { value: "transport", label: "Transport" },
  { value: "fuel", label: "Fuel" },
  { value: "rent", label: "Rent" },
  { value: "utilities", label: "Utilities" },
  { value: "supplies", label: "Supplies" },
  { value: "other", label: "Other" },
];

const EMPTY_EXPENSE = { category: "materials", description: "", vendor: "", amount: "", date: new Date().toISOString().slice(0, 10) };

function JobExpensesSection({ invoiceId, expenses, onRefresh }) {
  const [showForm, setShowForm] = useState(false);
  const [editTarget, setEditTarget] = useState(null);
  const [form, setForm] = useState(EMPTY_EXPENSE);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const openAdd = () => { setForm(EMPTY_EXPENSE); setEditTarget(null); setShowForm(true); setError(""); };
  const openEdit = (e) => {
    setForm({ category: e.category, description: e.description, vendor: e.vendor || "", amount: String(e.amount), date: e.date });
    setEditTarget(e);
    setShowForm(true);
    setError("");
  };

  const handleSave = async () => {
    if (!form.description || !form.amount) { setError("Description and amount are required"); return; }
    setSaving(true);
    setError("");
    try {
      const payload = { ...form, amount: parseFloat(form.amount), vendor: form.vendor || null };
      if (editTarget) await updateInvoiceExpense(invoiceId, editTarget.id, payload);
      else await createInvoiceExpense(invoiceId, payload);
      setShowForm(false);
      onRefresh();
    } catch (err) {
      setError(err.response?.data?.detail ?? "Failed to save expense");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (e) => {
    await deleteInvoiceExpense(invoiceId, e.id);
    onRefresh();
  };

  const total = expenses.reduce((s, e) => s + Number(e.amount), 0);

  return (
    <div className="card overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Receipt size={15} className="text-gray-500" />
          <h2 className="text-sm font-semibold text-gray-800">Job Expenses</h2>
          {total > 0 && <span className="text-xs text-gray-400">({ksh(total)})</span>}
        </div>
        <button className="btn-secondary text-xs py-1.5 px-3" onClick={openAdd}>
          <Plus size={13} /> Add Expense
        </button>
      </div>

      {expenses.length === 0 && !showForm && (
        <div className="px-4 py-6 text-center text-sm text-gray-400">
          No job expenses yet. Add materials, labour, lunch, transport and more.
        </div>
      )}

      {expenses.length > 0 && (
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left text-xs text-gray-500 uppercase tracking-wide">
            <tr>
              <th className="px-4 py-2">Category</th>
              <th className="px-4 py-2">Description</th>
              <th className="px-4 py-2 hidden sm:table-cell">Vendor</th>
              <th className="px-4 py-2 text-right">Amount</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {expenses.map((e) => (
              <tr key={e.id}>
                <td className="px-4 py-2.5">
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-gray-100 text-gray-600 capitalize">
                    {JOB_EXPENSE_CATEGORIES.find((c) => c.value === e.category)?.label ?? e.category}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-gray-700">{e.description}</td>
                <td className="px-4 py-2.5 text-gray-400 hidden sm:table-cell">{e.vendor || "—"}</td>
                <td className="px-4 py-2.5 text-right font-medium text-red-600">{ksh(e.amount)}</td>
                <td className="px-4 py-2.5">
                  <div className="flex gap-1 justify-end">
                    <button onClick={() => openEdit(e)} className="p-1 text-gray-300 hover:text-gray-600"><Receipt size={12} /></button>
                    <button onClick={() => handleDelete(e)} className="p-1 text-gray-300 hover:text-red-500"><Trash2 size={12} /></button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t border-gray-200 bg-gray-50">
              <td colSpan={3} className="px-4 py-2 text-xs font-semibold text-gray-600 uppercase tracking-wide">Total Job Expenses</td>
              <td className="px-4 py-2 text-right font-bold text-red-600">{ksh(total)}</td>
              <td />
            </tr>
          </tfoot>
        </table>
      )}

      {showForm && (
        <div className="px-4 py-4 border-t border-gray-100 bg-gray-50 space-y-3">
          {error && <div className="bg-red-50 text-red-700 text-xs px-3 py-2 rounded-lg">{error}</div>}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Category</label>
              <select className="input" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
                {JOB_EXPENSE_CATEGORIES.map((c) => (
                  <option key={c.value} value={c.value}>{c.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Date</label>
              <input className="input" type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} />
            </div>
          </div>
          <div>
            <label className="label">Description *</label>
            <input className="input" placeholder="e.g. 50 bags of cement, 3 workers × 2 days" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Amount (KSh) *</label>
              <input className="input" type="number" min="0.01" step="0.01" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} />
            </div>
            <div>
              <label className="label">Vendor <span className="text-gray-400 font-normal">(optional)</span></label>
              <input className="input" placeholder="Who was paid?" value={form.vendor} onChange={(e) => setForm({ ...form, vendor: e.target.value })} />
            </div>
          </div>
          <div className="flex gap-2 justify-end">
            <button className="btn-secondary text-sm" onClick={() => setShowForm(false)}>Cancel</button>
            <button className="btn-primary text-sm" onClick={handleSave} disabled={saving}>
              {saving ? "Saving…" : editTarget ? "Update" : "Add Expense"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function ProfitabilityCard({ invoice }) {
  const revenue = Number(invoice.grand_total);
  const cogs = Number(invoice.total_cogs ?? 0);
  const jobExpenses = Number(invoice.total_job_expenses ?? 0);
  const profit = Number(invoice.gross_profit ?? revenue - cogs - jobExpenses);
  const isProfitable = profit >= 0;
  const hasData = cogs > 0 || jobExpenses > 0;

  if (!hasData) return null;

  const margin = revenue > 0 ? ((profit / revenue) * 100).toFixed(1) : "0.0";

  return (
    <div className={`card p-4 border-2 ${isProfitable ? "border-emerald-200 bg-emerald-50" : "border-red-200 bg-red-50"}`}>
      <div className="flex items-center gap-2 mb-3">
        {isProfitable
          ? <TrendingUp size={16} className="text-emerald-600" />
          : <TrendingDown size={16} className="text-red-600" />}
        <h2 className="text-sm font-semibold text-gray-800">Job Profitability</h2>
        <span className={`ml-auto text-xs font-semibold px-2 py-0.5 rounded-full ${isProfitable ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-700"}`}>
          {isProfitable ? "Profit" : "Loss"} · {Math.abs(Number(margin))}% margin
        </span>
      </div>
      <div className="space-y-1.5 text-sm">
        <div className="flex justify-between text-gray-600">
          <span>Revenue (invoice total)</span>
          <span className="font-medium">{ksh(revenue)}</span>
        </div>
        {cogs > 0 && (
          <div className="flex justify-between text-gray-500">
            <span>Cost of goods (COGS)</span>
            <span className="text-red-500">− {ksh(cogs)}</span>
          </div>
        )}
        {jobExpenses > 0 && (
          <div className="flex justify-between text-gray-500">
            <span>Job expenses</span>
            <span className="text-red-500">− {ksh(jobExpenses)}</span>
          </div>
        )}
        <div className={`flex justify-between font-bold text-base border-t pt-2 mt-1 ${isProfitable ? "border-emerald-200 text-emerald-700" : "border-red-200 text-red-600"}`}>
          <span>{isProfitable ? "Gross Profit" : "Net Loss"}</span>
          <span>{isProfitable ? "" : "− "}{ksh(Math.abs(profit))}</span>
        </div>
      </div>
    </div>
  );
}

const PAYMENT_STATUS_COLORS = {
  paid: "bg-green-100 text-green-700",
  partial: "bg-blue-100 text-blue-700",
  unpaid: "bg-amber-100 text-amber-700",
};

function RecordPaymentForm({ invoice, paymentsData, onSave, onClose }) {
  const balance = paymentsData ? paymentsData.balance_due : Number(invoice.grand_total);
  const [form, setForm] = useState({
    method: "cash",
    amount: String(balance.toFixed(2)),
    reference: "",
    notes: "",
    paid_at: new Date().toISOString().slice(0, 10),
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await recordPayment(invoice.id, { ...form, amount: parseFloat(form.amount), paid_at: new Date(form.paid_at).toISOString() });
      onSave();
    } catch (err) {
      setError(err.response?.data?.detail ?? "Failed to record payment");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && <div className="bg-red-50 text-red-700 text-sm px-3 py-2 rounded-lg">{error}</div>}
      <div className="flex items-center gap-3 p-3 bg-blue-50 rounded-lg text-sm text-blue-800">
        <CreditCard size={16} className="shrink-0" />
        Balance due: <strong>{ksh(balance)}</strong>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label">Amount (KSh) *</label>
          <input className="input" type="number" min="0.01" step="0.01" value={form.amount}
            onChange={(e) => setForm({ ...form, amount: e.target.value })} required />
        </div>
        <div>
          <label className="label">Date *</label>
          <input className="input" type="date" value={form.paid_at}
            onChange={(e) => setForm({ ...form, paid_at: e.target.value })} required />
        </div>
      </div>
      <div>
        <label className="label">Method</label>
        <select className="input" value={form.method} onChange={(e) => setForm({ ...form, method: e.target.value })}>
          <option value="cash">Cash</option>
          <option value="bank">Bank Transfer</option>
          <option value="mpesa">M-Pesa</option>
          <option value="cheque">Cheque</option>
          <option value="paystack">Card (Paystack)</option>
        </select>
      </div>
      <div>
        <label className="label">Reference</label>
        <input className="input" placeholder="Receipt no., transaction ref…" value={form.reference}
          onChange={(e) => setForm({ ...form, reference: e.target.value })} />
      </div>
      <div>
        <label className="label">Notes</label>
        <input className="input" placeholder="Optional" value={form.notes}
          onChange={(e) => setForm({ ...form, notes: e.target.value })} />
      </div>
      <div className="flex justify-end gap-2 pt-1">
        <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
        <button type="submit" className="btn-primary" disabled={saving}>
          {saving ? "Saving…" : "Record Payment"}
        </button>
      </div>
    </form>
  );
}

function MpesaForm({ invoice, onClose }) {
  const [ph, setPh] = useState(invoice.client?.phone ?? "");
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  const handleSend = async () => {
    setSending(true);
    setError("");
    try {
      await mpesaPay(invoice.id, ph);
      setSent(true);
    } catch (err) {
      setError(err.response?.data?.detail ?? "STK Push failed. Check the phone number and try again.");
    } finally {
      setSending(false);
    }
  };

  if (sent)
    return (
      <div className="flex flex-col items-center py-6 text-center gap-3">
        <div className="h-14 w-14 rounded-full bg-green-100 flex items-center justify-center">
          <CheckCircle size={28} className="text-green-600" />
        </div>
        <p className="font-semibold text-gray-900">STK Push Sent</p>
        <p className="text-sm text-gray-500 max-w-xs">
          Ask <strong>{invoice.client.name}</strong> to check their phone and enter their M-Pesa PIN to complete payment of <strong>{ksh(invoice.grand_total)}</strong>.
        </p>
        <button className="btn-secondary mt-2" onClick={onClose}>Close</button>
      </div>
    );

  return (
    <div className="space-y-4">
      <div className="flex items-start gap-3 p-3 bg-green-50 rounded-lg">
        <Smartphone size={18} className="text-green-600 mt-0.5 shrink-0" />
        <p className="text-sm text-green-800">
          An M-Pesa payment prompt for <strong>{ksh(invoice.grand_total)}</strong> will be sent to the number below.
        </p>
      </div>
      {error && <div className="bg-red-50 text-red-700 text-sm px-3 py-2 rounded-lg">{error}</div>}
      <div>
        <label className="label">Customer Phone Number</label>
        <input className="input" value={ph} onChange={(e) => setPh(e.target.value)} placeholder="254712345678" />
        <p className="text-xs text-gray-400 mt-1">Format: 254XXXXXXXXX (12 digits)</p>
      </div>
      <div className="flex justify-end gap-2">
        <button className="btn-secondary" onClick={onClose}>Cancel</button>
        <button className="btn-primary" onClick={handleSend} disabled={sending || !ph}>
          <Smartphone size={15} />
          {sending ? "Sending…" : "Send Payment Request"}
        </button>
      </div>
    </div>
  );
}

function RequestPaymentForm({ invoice, paymentsData, onClose }) {
  const balance = paymentsData ? paymentsData.balance_due : Number(invoice.grand_total);
  const [amount, setAmount] = useState(String(balance.toFixed(2)));
  const [copied, setCopied] = useState(false);

  const amountNum = parseFloat(amount) || 0;
  const isPartial = amountNum < Number(invoice.grand_total) - 0.01;
  const isValid = amountNum > 0 && amountNum <= balance + 0.01;

  const link = isValid
    ? `${publicOrigin()}/pay/${invoice.id}${isPartial ? `?amount=${amountNum.toFixed(2)}` : ""}`
    : null;

  const handleCopy = () => {
    if (!link) return;
    navigator.clipboard.writeText(link).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const handleWhatsApp = () => {
    if (!link) return;
    const clientPhone = normalizePhone(invoice.client?.phone);
    const amtLabel = isPartial ? `*KSh ${amountNum.toLocaleString()}* (partial)` : `*${ksh(invoice.grand_total)}*`;
    const msg = [
      `Hello ${invoice.client?.name ?? ""},`,
      ``,
      `This is a payment request for invoice *${invoice.id}* — ${amtLabel}.`,
      ``,
      `Pay securely here: ${link}`,
      ``,
      `Thank you.`,
    ].join("\n");
    window.open(`https://wa.me/${clientPhone}?text=${encodeURIComponent(msg)}`, "_blank");
  };

  return (
    <div className="space-y-4">
      <div className="flex items-start gap-3 p-3 bg-blue-50 rounded-lg text-sm text-blue-800">
        <Link2 size={16} className="mt-0.5 shrink-0 text-blue-600" />
        <p>Set the agreed amount, then share the payment link with your client. They can pay via M-Pesa or card.</p>
      </div>

      <div>
        <label className="label">Amount to Request (KSh)</label>
        <input
          className="input"
          type="number"
          min="1"
          step="0.01"
          max={balance}
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
        />
        <p className="text-xs text-gray-400 mt-1">
          Balance due: <strong>{ksh(balance)}</strong>
          {isPartial && isValid && (
            <span className="ml-2 text-indigo-600 font-medium">· Partial payment</span>
          )}
        </p>
      </div>

      {!isValid && amount && (
        <div className="bg-red-50 text-red-700 text-sm px-3 py-2 rounded-lg">
          Amount must be between KSh 1 and {ksh(balance)}.
        </div>
      )}

      {link && (
        <div>
          <label className="label">Payment Link</label>
          <div className="flex gap-2">
            <input
              className="input flex-1 text-xs font-mono bg-gray-50 text-gray-600"
              readOnly
              value={link}
              onFocus={(e) => e.target.select()}
            />
            <button
              onClick={handleCopy}
              className="px-3 py-2 border border-gray-200 rounded-lg text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors whitespace-nowrap"
            >
              {copied ? <CheckCircle size={15} className="text-green-500" /> : <Copy size={15} />}
            </button>
          </div>
        </div>
      )}

      <div className="flex gap-2 pt-1">
        <button
          onClick={handleWhatsApp}
          disabled={!isValid}
          className="flex-1 flex items-center justify-center gap-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white font-semibold rounded-xl py-2.5 text-sm transition-colors"
        >
          <MessageCircle size={15} /> Send via WhatsApp
        </button>
        <button
          onClick={handleCopy}
          disabled={!isValid}
          className="flex-1 flex items-center justify-center gap-2 border border-gray-200 text-gray-700 hover:bg-gray-50 disabled:opacity-50 rounded-xl py-2.5 text-sm font-medium transition-colors"
        >
          <Copy size={15} /> {copied ? "Copied!" : "Copy Link"}
        </button>
      </div>
      <button className="w-full btn-secondary" onClick={onClose}>Close</button>
    </div>
  );
}

export default function InvoiceDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [invoice, setInvoice] = useState(null);
  const [org, setOrg] = useState({});
  const [paymentsData, setPaymentsData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showPayment, setShowPayment] = useState(false);
  const [showMpesa, setShowMpesa] = useState(false);
  const [showPDF, setShowPDF] = useState(false);
  const [showRequestPayment, setShowRequestPayment] = useState(false);
  const [reminderSent, setReminderSent] = useState(false);
  const [etimsLoading, setEtimsLoading] = useState(false);
  const [etimsError, setEtimsError] = useState("");
  const [linkCopied, setLinkCopied] = useState(false);
  const [deletePaymentTarget, setDeletePaymentTarget] = useState(null);
  const [emailSent, setEmailSent] = useState(false);
  const pollRef = useRef(null);

  const load = async () => {
    setLoading(true);
    const [invRes, payRes] = await Promise.all([
      getInvoice(id),
      getInvoicePayments(id).catch(() => null),
    ]);
    setInvoice(invRes.data.data);
    if (payRes) setPaymentsData(payRes.data);
    setLoading(false);
  };

  useEffect(() => { load(); }, [id]);
  useEffect(() => { getOrganization().then(({ data }) => setOrg(data.data)).catch(() => {}); }, []);

  useEffect(() => {
    if (showMpesa) {
      pollRef.current = setInterval(() => {
        getInvoice(id).then(({ data }) => {
          if (data.data.payment_status === "paid") {
            clearInterval(pollRef.current);
            setInvoice(data.data);
            setShowMpesa(false);
            load();
          }
        });
      }, 3000);
    } else {
      clearInterval(pollRef.current);
    }
    return () => clearInterval(pollRef.current);
  }, [showMpesa]);

  const handleCopyLink = () => {
    navigator.clipboard.writeText(`${publicOrigin()}/pay/${id}`).then(() => {
      setLinkCopied(true);
      setTimeout(() => setLinkCopied(false), 2000);
    });
  };

  const handleShareWhatsApp = () => {
    if (!invoice) return;
    const payLink = `${publicOrigin()}/pay/${id}`;
    const msg = [`Hello ${invoice.client?.name ?? ""},`, ``, `Please find your invoice *${id}* for *${ksh(invoice.grand_total)}*.`, ``, `Pay online here: ${payLink}`, ``, `Thank you.`].join("\n");
    window.open(`https://wa.me/${normalizePhone(invoice.client?.phone)}?text=${encodeURIComponent(msg)}`, "_blank");
  };

  const handleEtimsSubmit = async () => {
    setEtimsLoading(true);
    setEtimsError("");
    try {
      const { data } = await submitEtims(id);
      setInvoice(data.data);
    } catch (err) {
      setEtimsError(err.response?.data?.detail ?? "eTIMS submission failed");
    } finally {
      setEtimsLoading(false);
    }
  };

  const handleSendEmail = async () => {
    try {
      await sendInvoiceEmail(id);
      setEmailSent(true);
      setTimeout(() => setEmailSent(false), 3000);
    } catch { /* ignore */ }
  };

  const handleDeletePayment = async () => {
    await deletePayment(id, deletePaymentTarget.id);
    setDeletePaymentTarget(null);
    load();
  };

  const handleSendReminder = async () => {
    try {
      const { data } = await sendReminder(id);
      // Backend returns a WhatsApp URL — open it
      window.open(data.message, "_blank");
      setReminderSent(true);
      setTimeout(() => setReminderSent(false), 3000);
    } catch { /* ignore */ }
  };

  if (loading) return <div className="flex h-96 items-center justify-center"><Spinner size="lg" /></div>;
  if (!invoice) return null;

  const statusCls = PAYMENT_STATUS_COLORS[invoice.payment_status] ?? "bg-gray-100 text-gray-600";
  const isFullyPaid = invoice.payment_status === "paid";
  const isPartial = invoice.payment_status === "partial";
  const canPay = !isFullyPaid;

  return (
    <div className="p-4 md:p-6 max-w-3xl mx-auto space-y-5">
      <div className="flex items-start gap-3 flex-wrap">
        <button onClick={() => navigate(-1)} className="mt-1 text-gray-400 hover:text-gray-600">
          <ArrowLeft size={20} />
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-xl font-bold text-gray-900 font-mono">{invoice.id}</h1>
            <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold capitalize ${statusCls}`}>
              {invoice.payment_status}
            </span>
          </div>
          <p className="text-sm text-gray-400 mt-0.5">
            Created {date(invoice.created_at)}
            {invoice.due_date && (
              <span className={`ml-2 ${!isFullyPaid ? "text-red-400" : "text-gray-400"}`}>
                · Due {date(invoice.due_date)}
              </span>
            )}
          </p>
        </div>
        <div className="flex gap-2 flex-wrap justify-end">
          <button className="btn-secondary" onClick={() => setShowPDF(true)}>
            <FileDown size={15} /> PDF
          </button>
          {invoice.client?.email && (
            <button className="btn-secondary" onClick={handleSendEmail} disabled={emailSent}>
              <Mail size={15} /> {emailSent ? "Sent!" : "Email"}
            </button>
          )}
          {canPay && (
            <>
              <button className="btn-secondary" onClick={handleSendReminder} disabled={reminderSent}>
                <Bell size={15} /> {reminderSent ? "Sent!" : "Remind"}
              </button>
              <button className="btn-secondary" onClick={() => setShowRequestPayment(true)}>
                <Link2 size={15} /> Request Payment
              </button>
              <button className="btn-secondary" onClick={() => setShowMpesa(true)}>
                <Smartphone size={15} /> M-Pesa
              </button>
              <button className="btn-primary" onClick={() => setShowPayment(true)}>
                <Plus size={15} /> Record Payment
              </button>
            </>
          )}
          {org.etims_enabled && !invoice.etims_cu_invoice_no && (
            <button className="btn-secondary" onClick={handleEtimsSubmit} disabled={etimsLoading}>
              {etimsLoading ? <Loader size={15} className="animate-spin" /> : <ShieldCheck size={15} />}
              {etimsLoading ? "Submitting…" : "Submit to KRA"}
            </button>
          )}
        </div>
      </div>

      {/* Partial payment progress */}
      {isPartial && paymentsData && (
        <div className="card p-4 bg-blue-50 border-blue-200 space-y-2">
          <div className="flex justify-between text-sm font-medium text-blue-800">
            <span>Partial Payment</span>
            <span>{ksh(paymentsData.amount_paid)} of {ksh(paymentsData.grand_total)}</span>
          </div>
          <div className="h-2 bg-blue-100 rounded-full overflow-hidden">
            <div
              className="h-2 bg-blue-500 rounded-full transition-all"
              style={{ width: `${Math.min(100, (paymentsData.amount_paid / paymentsData.grand_total) * 100)}%` }}
            />
          </div>
          <p className="text-xs text-blue-600">Balance due: <strong>{ksh(paymentsData.balance_due)}</strong></p>
        </div>
      )}

      {/* Smart reminder status */}
      {!isFullyPaid && invoice.due_date && (() => {
        const MILESTONES = [-7, 0, 7, 30, 60];
        const sent = invoice.reminders_sent ?? 0;
        const nextMilestone = MILESTONES[sent];
        const daysFromDue = Math.round((Date.now() - new Date(invoice.due_date).getTime()) / 86400000);
        const daysUntilNext = nextMilestone !== undefined ? nextMilestone - daysFromDue : null;
        const isOverdue = daysFromDue > 0;
        const lastSent = invoice.last_reminded_at
          ? new Date(invoice.last_reminded_at).toLocaleDateString("en-KE", { day: "2-digit", month: "short", year: "numeric" })
          : null;

        const nextLabel = nextMilestone === undefined ? "All reminders sent" :
          nextMilestone < 0
            ? (daysUntilNext <= 0 ? "Due-soon reminder pending (runs tonight)" : `Due-soon reminder in ${daysUntilNext}d`)
            : daysUntilNext <= 0
              ? `${isOverdue ? "Overdue" : "Due"} reminder pending (runs tonight)`
              : `Next overdue reminder in ${daysUntilNext}d`;

        return (
          <div className="card p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Bell size={15} className="text-amber-500" />
                <h2 className="text-xs font-semibold text-gray-700 uppercase tracking-wide">Payment Reminders</h2>
              </div>
              <span className="text-xs text-gray-400">{sent} of {MILESTONES.length} sent</span>
            </div>

            {/* Milestone progress */}
            <div className="flex items-center gap-1">
              {MILESTONES.map((m, i) => (
                <div key={i} className="flex-1 flex flex-col items-center gap-1">
                  <div className={`h-2 w-full rounded-full ${i < sent ? "bg-green-500" : i === sent ? "bg-amber-400" : "bg-gray-100"}`} />
                  <span className="text-[9px] text-gray-400 leading-none">
                    {m < 0 ? `${Math.abs(m)}d before` : m === 0 ? "due date" : `+${m}d`}
                  </span>
                </div>
              ))}
            </div>

            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1 text-xs text-gray-500">
              <span>{nextLabel}</span>
              {lastSent && <span className="text-gray-400">Last sent: {lastSent}</span>}
            </div>
          </div>
        );
      })()}

      {/* eTIMS */}
      {etimsError && <div className="bg-red-50 text-red-700 text-sm px-3 py-2 rounded-lg">{etimsError}</div>}
      {invoice.etims_cu_invoice_no && (
        <div className="card p-4 bg-green-50 border-green-200">
          <div className="flex items-center gap-2 mb-1">
            <ShieldCheck size={16} className="text-green-600" />
            <h2 className="text-xs font-semibold text-green-700 uppercase tracking-wide">KRA eTIMS Verified</h2>
          </div>
          <p className="text-sm text-green-900">CU Invoice No: <span className="font-mono font-semibold">{invoice.etims_cu_invoice_no}</span></p>
          <p className="text-xs text-green-600 mt-1">Submitted {invoice.etims_submitted_at ? new Date(invoice.etims_submitted_at).toLocaleString() : ""}</p>
        </div>
      )}

      {/* Client */}
      <div className="card p-4">
        <h2 className="text-xs text-gray-500 uppercase tracking-wide mb-2">Client</h2>
        <p className="font-semibold text-gray-900">{invoice.client.name}</p>
        <p className="text-sm text-gray-500">{invoice.client.email}</p>
        <p className="text-sm text-gray-500">{phone(invoice.client.phone)}</p>
        {invoice.quotation_id && <p className="text-xs text-gray-400 mt-1">From quotation <span className="font-mono">{invoice.quotation_id}</span></p>}
      </div>

      {/* Items */}
      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left text-xs text-gray-500 uppercase tracking-wide">
            <tr>
              <th className="px-4 py-3">Description</th>
              <th className="px-4 py-3 text-right">Qty</th>
              <th className="px-4 py-3 text-right hidden sm:table-cell">Unit Price</th>
              <th className="px-4 py-3 text-right">Total</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {invoice.items.map((item) => (
              <tr key={item.id}>
                <td className="px-4 py-3">{item.description}</td>
                <td className="px-4 py-3 text-right text-gray-600">{item.quantity}</td>
                <td className="px-4 py-3 text-right text-gray-600 hidden sm:table-cell">{ksh(item.unit_price)}</td>
                <td className="px-4 py-3 text-right font-medium">{ksh(item.line_total)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {invoice.charges?.length > 0 && (
          <div className="px-4 py-2 border-t border-gray-100">
            <p className="text-xs text-gray-400 uppercase tracking-wide mb-1.5">Other Charges</p>
            {invoice.charges.map((c) => (
              <div key={c.id} className="flex justify-between text-sm text-gray-600 py-0.5">
                <span>{c.description}</span><span>{ksh(c.amount)}</span>
              </div>
            ))}
          </div>
        )}
        <div className="px-4 py-3 border-t border-gray-100 space-y-1.5 text-sm">
          <div className="flex justify-between text-gray-600"><span>Items subtotal</span><span>{ksh(invoice.subtotal)}</span></div>
          {Number(invoice.total_discount) > 0 && (
            <div className="flex justify-between text-red-500"><span>Total discount</span><span>− {ksh(invoice.total_discount)}</span></div>
          )}
          {(() => {
            const labour = invoice.charges?.find((c) => c.description === "Labour");
            const otherTotal = Number(invoice.charges_total) - (labour ? Number(labour.amount) : 0);
            return (
              <>
                {labour && (
                  <div className="flex justify-between text-gray-600">
                    <span>Labour ({Number(invoice.subtotal) > 0 ? Math.round(Number(labour.amount) / Number(invoice.subtotal) * 10000) / 100 : 0}%)</span>
                    <span>{ksh(labour.amount)}</span>
                  </div>
                )}
                {otherTotal > 0 && (
                  <div className="flex justify-between text-gray-600"><span>Other charges</span><span>{ksh(otherTotal)}</span></div>
                )}
              </>
            );
          })()}
          {Number(invoice.vat_amount) > 0 && (
            <div className="flex justify-between text-gray-600"><span>VAT (16%)</span><span>{ksh(invoice.vat_amount)}</span></div>
          )}
          <div className="flex justify-between font-bold text-gray-900 text-base border-t pt-2">
            <span>Grand Total</span><span>{ksh(invoice.grand_total)}</span>
          </div>
          {Number(invoice.wht_amount) > 0 && (
            <div className="flex justify-between text-amber-600 text-xs">
              <span>WHT ({invoice.wht_pct}%) — deducted by client</span>
              <span>− {ksh(invoice.wht_amount)}</span>
            </div>
          )}
          {Number(invoice.deposit_amount) > 0 && (
            <div className="flex justify-between text-green-600 text-xs">
              <span>Deposit received</span>
              <span>− {ksh(invoice.deposit_amount)}</span>
            </div>
          )}
          {(Number(invoice.wht_amount) > 0 || Number(invoice.deposit_amount) > 0) && (
            <div className="flex justify-between font-bold text-gray-900 border-t pt-2">
              <span>Amount Payable</span>
              <span>{ksh(Number(invoice.grand_total) - Number(invoice.wht_amount) - Number(invoice.deposit_amount))}</span>
            </div>
          )}
        </div>
      </div>

      {/* Payment history */}
      {paymentsData && paymentsData.payments.length > 0 && (
        <div className="card overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100">
            <h2 className="text-sm font-semibold text-gray-800">Payment History</h2>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs text-gray-500 uppercase tracking-wide">
              <tr>
                <th className="px-4 py-2">Date</th>
                <th className="px-4 py-2">Method</th>
                <th className="px-4 py-2 hidden sm:table-cell">Reference</th>
                <th className="px-4 py-2 text-right">Amount</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {paymentsData.payments.map((p) => (
                <tr key={p.id}>
                  <td className="px-4 py-2.5 text-gray-600">{date(p.paid_at)}</td>
                  <td className="px-4 py-2.5 capitalize">{p.method}</td>
                  <td className="px-4 py-2.5 text-gray-400 hidden sm:table-cell font-mono text-xs">{p.reference || "—"}</td>
                  <td className="px-4 py-2.5 text-right font-semibold text-green-700">{ksh(p.amount)}</td>
                  <td className="px-4 py-2.5">
                    {!isFullyPaid && (
                      <button onClick={() => setDeletePaymentTarget(p)} className="p-1 text-gray-300 hover:text-red-500">
                        <Trash2 size={13} />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Job Expenses */}
      <JobExpensesSection
        invoiceId={invoice.id}
        expenses={invoice.expenses ?? []}
        onRefresh={load}
      />

      {/* Profitability */}
      <ProfitabilityCard invoice={invoice} />

      {/* PDF Preview */}
      <PDFPreviewModal open={showPDF} onClose={() => setShowPDF(false)} title={`${invoice.id} — Tax Invoice`} >
        <InvoiceDocument invoice={invoice} org={org} />
      </PDFPreviewModal>

      {/* Record Payment Modal */}
      <Modal open={showPayment} onClose={() => setShowPayment(false)} title="Record Payment">
        <RecordPaymentForm
          invoice={invoice}
          paymentsData={paymentsData}
          onSave={() => { setShowPayment(false); load(); }}
          onClose={() => setShowPayment(false)}
        />
      </Modal>

      {/* M-Pesa Modal */}
      <Modal open={showMpesa} onClose={() => setShowMpesa(false)} title="Request M-Pesa Payment">
        <MpesaForm invoice={invoice} onClose={() => setShowMpesa(false)} />
      </Modal>

      {/* Request Payment Link Modal */}
      <Modal open={showRequestPayment} onClose={() => setShowRequestPayment(false)} title="Request Payment">
        <RequestPaymentForm
          invoice={invoice}
          paymentsData={paymentsData}
          onClose={() => setShowRequestPayment(false)}
        />
      </Modal>

      <ConfirmDialog
        open={!!deletePaymentTarget}
        onClose={() => setDeletePaymentTarget(null)}
        onConfirm={handleDeletePayment}
        title="Delete Payment"
        message={`Remove payment of ${ksh(deletePaymentTarget?.amount ?? 0)}? The invoice balance will be updated.`}
        danger
      />
    </div>
  );
}
