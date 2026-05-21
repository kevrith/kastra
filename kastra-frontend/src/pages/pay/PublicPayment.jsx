import { useEffect, useRef, useState } from "react";
import { useParams, useSearchParams, Link, useNavigate } from "react-router-dom";
import { getPublicInvoice, publicMpesaPay } from "../../api/pay";
import { initializePaystack } from "../../api/portal";
import { Smartphone, CheckCircle, Loader, AlertCircle, CreditCard, ArrowLeft } from "lucide-react";

function ksh(val) {
  return `KSh ${Number(val).toLocaleString("en-KE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
function fmtDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-KE", { day: "2-digit", month: "short", year: "numeric" });
}

export default function PublicPayment() {
  const { invoiceId } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const backUrl = searchParams.get("back");

  // Requested partial amount from the payment link (set by business owner)
  const requestedAmount = searchParams.get("amount") ? parseFloat(searchParams.get("amount")) : null;

  const [invoice, setInvoice] = useState(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  const [phone, setPhone] = useState("");
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  const [cardEmail, setCardEmail] = useState("");
  const [cardLoading, setCardLoading] = useState(false);
  const [cardError, setCardError] = useState("");

  const pollRef = useRef(null);

  useEffect(() => {
    if (invoice?.client_email) setCardEmail(invoice.client_email);
  }, [invoice?.client_email]);

  const load = () =>
    getPublicInvoice(invoiceId)
      .then(({ data }) => setInvoice(data))
      .catch(() => setNotFound(true))
      .finally(() => setLoading(false));

  useEffect(() => { load(); }, [invoiceId]);

  useEffect(() => {
    if (sent && invoice?.payment_status !== "paid") {
      pollRef.current = setInterval(() => {
        getPublicInvoice(invoiceId).then(({ data }) => {
          setInvoice(data);
          if (data.payment_status === "paid" || data.payment_status === "partial") {
            clearInterval(pollRef.current);
          }
        });
      }, 4000);
    } else {
      clearInterval(pollRef.current);
    }
    return () => clearInterval(pollRef.current);
  }, [sent, invoice?.payment_status]);

  const handlePay = async () => {
    if (!phone.match(/^254\d{9}$/)) {
      setError("Enter a valid phone number (format: 254XXXXXXXXX — 12 digits)");
      return;
    }
    setSending(true);
    setError("");
    try {
      await publicMpesaPay(invoiceId, phone, requestedAmount);
      setSent(true);
    } catch (err) {
      setError(err.response?.data?.detail ?? "STK Push failed. Check the phone number and try again.");
    } finally {
      setSending(false);
    }
  };

  const handleCardPay = async () => {
    if (!cardEmail.includes("@")) {
      setCardError("Enter a valid email address to receive your receipt.");
      return;
    }
    setCardLoading(true);
    setCardError("");
    try {
      const { data } = await initializePaystack(invoiceId, cardEmail, requestedAmount);
      if (backUrl) sessionStorage.setItem("paystack_back_url", backUrl);
      window.location.href = data.authorization_url;
    } catch (err) {
      setCardError(err.response?.data?.detail ?? "Card payment initialization failed. Please try again.");
      setCardLoading(false);
    }
  };

  if (loading)
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <Loader size={28} className="animate-spin text-green-600" />
      </div>
    );

  if (notFound)
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 px-4 text-center">
        <AlertCircle size={40} className="text-red-400 mb-3" />
        <h1 className="text-lg font-bold text-gray-800 mb-1">Invoice not found</h1>
        <p className="text-sm text-gray-500">The payment link may be invalid or expired.</p>
      </div>
    );

  const isPaid = invoice.payment_status === "paid";
  const isPartial = invoice.payment_status === "partial";
  const isOverdue = !isPaid && invoice.due_date && new Date(invoice.due_date) < new Date();

  // What the client is expected to pay on this link
  const chargeAmount = requestedAmount ?? Number(invoice.balance_due ?? invoice.grand_total);
  const isPartialRequest = requestedAmount && requestedAmount < Number(invoice.grand_total);

  return (
    <div className="min-h-screen bg-gray-50 flex items-start justify-center py-10 px-4">
      <div className="w-full max-w-md space-y-4">

        {backUrl && (
          <Link to={backUrl} className="inline-flex items-center gap-2 text-sm text-green-700 font-medium hover:text-green-900 transition-colors">
            <ArrowLeft size={16} /> Back to Portal
          </Link>
        )}

        {/* Header card */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 text-center">
          <p className="text-xs font-semibold uppercase tracking-widest text-green-600 mb-1">
            {invoice.business_name}
          </p>
          <h1 className="text-2xl font-bold text-gray-900 font-mono">{invoice.id}</h1>
          <p className="text-sm text-gray-400 mt-1">Tax Invoice</p>

          <div className="mt-4 py-4 border-t border-gray-100">
            {isPartialRequest ? (
              <>
                <p className="text-xs text-indigo-600 font-semibold uppercase tracking-wide mb-1">Partial Payment Requested</p>
                <p className="text-3xl font-bold text-gray-900">{ksh(chargeAmount)}</p>
                <p className="text-xs text-gray-400 mt-1">
                  of {ksh(invoice.grand_total)} total
                  {Number(invoice.amount_paid) > 0 && ` · ${ksh(invoice.amount_paid)} already paid`}
                </p>
                {/* Progress bar */}
                <div className="mt-3 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="h-1.5 bg-indigo-500 rounded-full"
                    style={{ width: `${Math.min(100, (chargeAmount / Number(invoice.grand_total)) * 100)}%` }}
                  />
                </div>
              </>
            ) : isPartial ? (
              <>
                <p className="text-xs text-blue-600 font-semibold uppercase tracking-wide mb-1">Remaining Balance</p>
                <p className="text-3xl font-bold text-gray-900">{ksh(invoice.balance_due)}</p>
                <p className="text-xs text-gray-400 mt-1">{ksh(invoice.amount_paid)} of {ksh(invoice.grand_total)} paid</p>
                <div className="mt-3 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="h-1.5 bg-blue-500 rounded-full"
                    style={{ width: `${Math.min(100, (Number(invoice.amount_paid) / Number(invoice.grand_total)) * 100)}%` }}
                  />
                </div>
              </>
            ) : (
              <>
                <p className="text-sm text-gray-500">Amount Due</p>
                <p className="text-3xl font-bold text-gray-900 mt-0.5">{ksh(invoice.grand_total)}</p>
              </>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3 mt-2 text-sm text-left">
            <div>
              <p className="text-xs text-gray-400 mb-0.5">Billed To</p>
              <p className="font-medium text-gray-800">{invoice.client_name}</p>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-0.5">Due Date</p>
              <p className={`font-medium ${isOverdue ? "text-red-500" : "text-gray-800"}`}>
                {fmtDate(invoice.due_date)}
                {isOverdue && <span className="ml-1 text-xs">(Overdue)</span>}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-0.5">Invoice Date</p>
              <p className="font-medium text-gray-800">{fmtDate(invoice.created_at)}</p>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-0.5">Status</p>
              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${
                isPaid ? "bg-green-100 text-green-700"
                : isPartial ? "bg-blue-100 text-blue-700"
                : "bg-amber-100 text-amber-700"
              }`}>
                {isPaid ? "Paid" : isPartial ? "Partial" : "Unpaid"}
              </span>
            </div>
          </div>
        </div>

        {/* Paid state */}
        {isPaid ? (
          <div className="bg-green-50 border border-green-200 rounded-2xl p-6 text-center space-y-3">
            <CheckCircle size={36} className="text-green-500 mx-auto" />
            <p className="font-semibold text-green-800 text-lg">Payment Received</p>
            <p className="text-sm text-green-600">Thank you! This invoice has been fully paid.</p>
            {backUrl && (
              <button onClick={() => navigate(backUrl)}
                className="inline-flex items-center gap-2 mt-1 px-4 py-2 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-xl text-sm transition-colors">
                <ArrowLeft size={15} /> Back to Portal
              </button>
            )}
          </div>

        ) : sent ? (
          /* Waiting for M-Pesa confirmation */
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 text-center space-y-3">
            <Loader size={28} className="animate-spin text-green-600 mx-auto" />
            <p className="font-semibold text-gray-800">Waiting for M-Pesa confirmation…</p>
            <p className="text-sm text-gray-500">
              Check your phone and enter your M-Pesa PIN to complete <strong>{ksh(chargeAmount)}</strong>.
            </p>
            <p className="text-xs text-gray-400">This page updates automatically once confirmed.</p>
          </div>

        ) : (
          <>
            {/* M-Pesa */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 space-y-4">
              <div className="flex items-center gap-2">
                <Smartphone size={18} className="text-green-600" />
                <h2 className="font-semibold text-gray-800">Pay via M-Pesa</h2>
              </div>
              {isPartialRequest && (
                <div className="flex items-center gap-2 bg-indigo-50 text-indigo-800 text-xs px-3 py-2 rounded-lg">
                  <span>Sending prompt for <strong>{ksh(chargeAmount)}</strong> (partial payment)</span>
                </div>
              )}
              {error && (
                <div className="bg-red-50 text-red-700 text-sm px-3 py-2 rounded-lg flex items-start gap-2">
                  <AlertCircle size={15} className="mt-0.5 shrink-0" /> {error}
                </div>
              )}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1.5">Phone Number</label>
                <input
                  className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-green-400 focus:border-transparent"
                  placeholder="254712345678"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value.replace(/\D/g, ""))}
                  maxLength={12}
                  inputMode="numeric"
                />
                <p className="text-xs text-gray-400 mt-1">Format: 254XXXXXXXXX (12 digits)</p>
              </div>
              <button onClick={handlePay} disabled={sending || !phone}
                className="w-full bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white font-semibold rounded-xl py-3 flex items-center justify-center gap-2 transition-colors">
                {sending ? <Loader size={17} className="animate-spin" /> : <Smartphone size={17} />}
                {sending ? "Sending…" : `Pay ${ksh(chargeAmount)} via M-Pesa`}
              </button>
            </div>

            {/* Card */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 space-y-4">
              <div className="flex items-center gap-2">
                <CreditCard size={18} className="text-indigo-600" />
                <h2 className="font-semibold text-gray-800">Pay by Card (Visa / Mastercard)</h2>
              </div>
              {isPartialRequest && (
                <div className="flex items-center gap-2 bg-indigo-50 text-indigo-800 text-xs px-3 py-2 rounded-lg">
                  <span>Charging <strong>{ksh(chargeAmount)}</strong> — partial payment</span>
                </div>
              )}
              <p className="text-sm text-gray-500">
                You'll be redirected to Paystack's secure page to enter your card details.
              </p>
              {cardError && (
                <div className="bg-red-50 text-red-700 text-sm px-3 py-2 rounded-lg flex items-start gap-2">
                  <AlertCircle size={15} className="mt-0.5 shrink-0" /> {cardError}
                </div>
              )}
              {!invoice.client_email && (
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1.5">
                    Email Address <span className="text-gray-400">(for your receipt)</span>
                  </label>
                  <input
                    className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent"
                    type="email" placeholder="your@email.com"
                    value={cardEmail}
                    onChange={(e) => setCardEmail(e.target.value)}
                  />
                </div>
              )}
              <button onClick={handleCardPay} disabled={cardLoading || !cardEmail}
                className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-semibold rounded-xl py-3 flex items-center justify-center gap-2 transition-colors">
                {cardLoading ? <Loader size={17} className="animate-spin" /> : <CreditCard size={17} />}
                {cardLoading ? "Redirecting to Paystack…" : `Pay ${ksh(chargeAmount)} by Card`}
              </button>
            </div>
          </>
        )}

        <p className="text-center text-xs text-gray-400 pb-4">
          Powered by <span className="font-semibold text-green-600">Kastra</span>
        </p>
      </div>
    </div>
  );
}
