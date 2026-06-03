import { useEffect, useState } from "react";
import { useParams, useSearchParams, Link } from "react-router-dom";
import { getPublicQuotation, respondToQuotation } from "../../api/portal";
import { CheckCircle, XCircle, Loader, AlertCircle, Phone, Mail, ArrowLeft } from "lucide-react";

function ksh(val) {
  return `KSh ${Number(val).toLocaleString("en-KE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
function fmtDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-KE", { day: "2-digit", month: "short", year: "numeric" });
}

const STATUS_LABELS = {
  draft: { label: "Draft", cls: "bg-gray-100 text-gray-700" },
  pending: { label: "Pending Review", cls: "bg-amber-100 text-amber-700" },
  accepted: { label: "Accepted", cls: "bg-green-100 text-green-700" },
  declined: { label: "Declined", cls: "bg-red-100 text-red-700" },
};

export default function PublicQuotation() {
  const { quotationId } = useParams();
  const [searchParams] = useSearchParams();
  const backUrl = searchParams.get("back");
  const [quotation, setQuotation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [responding, setResponding] = useState(null);
  const [done, setDone] = useState(null);
  const [error, setError] = useState("");
  const [showDeclineForm, setShowDeclineForm] = useState(false);
  const [declineReason, setDeclineReason] = useState("");

  useEffect(() => {
    getPublicQuotation(quotationId)
      .then(({ data }) => setQuotation(data))
      .catch(() => setNotFound(true))
      .finally(() => setLoading(false));
  }, [quotationId]);

  const handleRespond = async (action, reason = "") => {
    setResponding(action);
    setError("");
    try {
      const { data } = await respondToQuotation(quotationId, action, reason);
      setDone(data.status);
      setQuotation((q) => ({ ...q, status: data.status }));
    } catch (err) {
      setError(err.response?.data?.detail ?? "Something went wrong. Please try again.");
    } finally {
      setResponding(null);
      setShowDeclineForm(false);
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
        <h1 className="text-lg font-bold text-gray-800 mb-1">Quotation not found</h1>
        <p className="text-sm text-gray-500">This link may be invalid or the quotation has been removed.</p>
      </div>
    );

  const st = STATUS_LABELS[quotation.status] ?? STATUS_LABELS.draft;
  const canRespond = ["draft", "pending"].includes(quotation.status) && !quotation.is_expired && !done;

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="max-w-2xl mx-auto space-y-4">

        {/* Back to portal */}
        {backUrl && (
          <Link to={backUrl} className="inline-flex items-center gap-2 text-sm text-green-700 font-medium hover:text-green-900 transition-colors">
            <ArrowLeft size={16} /> Back to Portal
          </Link>
        )}

        {/* Header */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <p className="text-xs font-semibold uppercase tracking-widest text-green-600 mb-1">
            {quotation.business_name}
          </p>
          <div className="flex items-start justify-between gap-3">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 font-mono">{quotation.id}</h1>
              <p className="text-sm text-gray-400 mt-0.5">Quotation · {fmtDate(quotation.created_at)}</p>
            </div>
            <div className="flex flex-col items-end gap-1.5">
              <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ${st.cls}`}>
                {st.label}
              </span>
              {quotation.is_expired && (
                <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-orange-100 text-orange-700">
                  Expired
                </span>
              )}
            </div>
          </div>

          {quotation.expires_at && (
            <p className={`text-sm mt-3 ${quotation.is_expired ? "text-orange-600 font-medium" : "text-gray-400"}`}>
              {quotation.is_expired ? "Expired on " : "Valid until "}{fmtDate(quotation.expires_at)}
            </p>
          )}

          <div className="mt-4 pt-4 border-t border-gray-100 grid grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-xs text-gray-400 mb-0.5">Prepared for</p>
              <p className="font-semibold text-gray-800">{quotation.client_name}</p>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-0.5">Total Amount</p>
              <p className="font-bold text-gray-900 text-lg">{ksh(quotation.grand_total)}</p>
            </div>
          </div>
        </div>

        {/* Items */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
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
              {quotation.items.map((item, i) => (
                <tr key={i}>
                  <td className="px-4 py-3 text-gray-900">{item.description}</td>
                  <td className="px-4 py-3 text-right text-gray-600">{Number(item.quantity)}</td>
                  <td className="px-4 py-3 text-right text-gray-600 hidden sm:table-cell">{ksh(item.unit_price)}</td>
                  <td className="px-4 py-3 text-right font-medium">{ksh(item.line_total)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="px-4 py-3 border-t border-gray-100 space-y-1.5 text-sm">
            <div className="flex justify-between text-gray-500"><span>Subtotal</span><span>{ksh(quotation.subtotal)}</span></div>

            {/* Discount */}
            {Number(quotation.total_discount) > 0 && (
              <div className="flex justify-between text-red-500">
                <span>Discount {Number(quotation.discount_pct) > 0 ? `(${quotation.discount_pct}%)` : ""}</span>
                <span>− {ksh(quotation.total_discount)}</span>
              </div>
            )}

            {/* Charges (Labour with %, other charges) */}
            {(quotation.charges ?? []).map((charge, i) => {
              const isLabour = charge.description?.toLowerCase() === "labour";
              const pct = Number(quotation.subtotal) > 0
                ? Math.round((Number(charge.amount) / Number(quotation.subtotal)) * 10000) / 100
                : 0;
              return (
                <div key={i} className="flex justify-between text-gray-500">
                  <span>{charge.description}{isLabour && pct > 0 ? ` (${pct}%)` : ""}</span>
                  <span>{ksh(charge.amount)}</span>
                </div>
              );
            })}

            {/* VAT */}
            {Number(quotation.vat_amount) > 0 && (
              <div className="flex justify-between text-gray-500"><span>VAT (16%)</span><span>{ksh(quotation.vat_amount)}</span></div>
            )}

            <div className="flex justify-between font-bold text-gray-900 text-base border-t pt-2">
              <span>Total</span><span>{ksh(quotation.grand_total)}</span>
            </div>

            {/* WHT */}
            {Number(quotation.wht_amount) > 0 && (
              <div className="flex justify-between text-amber-600 text-xs">
                <span>WHT ({quotation.wht_pct}%) — deducted by client</span>
                <span>− {ksh(quotation.wht_amount)}</span>
              </div>
            )}

            {/* Deposit */}
            {Number(quotation.deposit_amount) > 0 && (
              <div className="flex justify-between text-green-600 text-xs">
                <span>Deposit</span>
                <span>− {ksh(quotation.deposit_amount)}</span>
              </div>
            )}

            {(Number(quotation.wht_amount) > 0 || Number(quotation.deposit_amount) > 0) && (
              <div className="flex justify-between font-bold text-gray-900 border-t pt-2">
                <span>Amount Payable</span>
                <span>{ksh(Number(quotation.grand_total) - Number(quotation.wht_amount) - Number(quotation.deposit_amount))}</span>
              </div>
            )}
          </div>
        </div>

        {/* Notes */}
        {quotation.notes && (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5">
            <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Notes</p>
            <p className="text-sm text-gray-700 whitespace-pre-line">{quotation.notes}</p>
          </div>
        )}

        {/* Accept / Decline */}
        {canRespond && (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 space-y-4">
            <p className="text-sm font-medium text-gray-700">
              Please review this quotation and let us know your decision:
            </p>
            {error && (
              <div className="bg-red-50 text-red-700 text-sm px-3 py-2 rounded-lg flex items-center gap-2">
                <AlertCircle size={15} /> {error}
              </div>
            )}

            {showDeclineForm ? (
              <div className="space-y-3">
                <label className="block text-sm font-medium text-gray-700">
                  Reason for declining <span className="text-gray-400 font-normal">(optional)</span>
                </label>
                <textarea
                  className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-red-300 focus:border-transparent resize-none"
                  rows={3}
                  placeholder="e.g. Price is too high, need to discuss further…"
                  value={declineReason}
                  onChange={(e) => setDeclineReason(e.target.value)}
                />
                <div className="flex gap-3">
                  <button
                    onClick={() => handleRespond("decline", declineReason)}
                    disabled={!!responding}
                    className="flex-1 flex items-center justify-center gap-2 py-3 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white font-semibold rounded-xl transition-colors"
                  >
                    {responding === "decline" ? <Loader size={17} className="animate-spin" /> : <XCircle size={17} />}
                    {responding === "decline" ? "Declining…" : "Confirm Decline"}
                  </button>
                  <button
                    onClick={() => { setShowDeclineForm(false); setDeclineReason(""); }}
                    className="px-4 py-3 text-gray-600 hover:text-gray-800 font-medium text-sm rounded-xl border border-gray-200 hover:bg-gray-50 transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex gap-3">
                <button
                  onClick={() => handleRespond("accept")}
                  disabled={!!responding}
                  className="flex-1 flex items-center justify-center gap-2 py-3 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white font-semibold rounded-xl transition-colors"
                >
                  {responding === "accept" ? <Loader size={17} className="animate-spin" /> : <CheckCircle size={17} />}
                  {responding === "accept" ? "Accepting…" : "Accept Quotation"}
                </button>
                <button
                  onClick={() => setShowDeclineForm(true)}
                  disabled={!!responding}
                  className="flex-1 flex items-center justify-center gap-2 py-3 bg-red-50 hover:bg-red-100 disabled:opacity-50 text-red-700 font-semibold rounded-xl border border-red-200 transition-colors"
                >
                  <XCircle size={17} /> Decline
                </button>
              </div>
            )}
          </div>
        )}

        {/* Post-response confirmation */}
        {done === "accepted" && (
          <div className="bg-green-50 border border-green-200 rounded-2xl p-6 text-center">
            <CheckCircle size={36} className="text-green-500 mx-auto mb-2" />
            <p className="font-semibold text-green-800 text-lg">Quotation Accepted</p>
            <p className="text-sm text-green-600 mt-1">
              Thank you! We'll be in touch shortly with next steps.
            </p>
          </div>
        )}
        {done === "declined" && (
          <div className="bg-gray-50 border border-gray-200 rounded-2xl p-6 text-center">
            <XCircle size={36} className="text-gray-400 mx-auto mb-2" />
            <p className="font-semibold text-gray-700 text-lg">Quotation Declined</p>
            <p className="text-sm text-gray-500 mt-1">
              Noted. Please contact us if you'd like to discuss alternatives.
            </p>
          </div>
        )}

        {/* Contact */}
        {(quotation.business_email || quotation.business_phone) && (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5">
            <p className="text-xs text-gray-400 uppercase tracking-wide mb-3">Contact {quotation.business_name}</p>
            <div className="flex flex-col gap-2">
              {quotation.business_email && (
                <a href={`mailto:${quotation.business_email}`}
                  className="flex items-center gap-2 text-sm text-green-600 hover:underline">
                  <Mail size={14} /> {quotation.business_email}
                </a>
              )}
              {quotation.business_phone && (
                <a href={`tel:${quotation.business_phone}`}
                  className="flex items-center gap-2 text-sm text-green-600 hover:underline">
                  <Phone size={14} /> {quotation.business_phone}
                </a>
              )}
            </div>
          </div>
        )}

        <p className="text-center text-xs text-gray-400 pb-4">
          Powered by <span className="font-semibold text-green-600">Kastra</span>
        </p>
      </div>
    </div>
  );
}
