import { useEffect, useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getClientPortal, verifyPortalPin } from "../../api/portal";
import { Loader, AlertCircle, FileText, Receipt, CreditCard, Lock } from "lucide-react";

function ksh(val) {
  return `KSh ${Number(val).toLocaleString("en-KE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
function fmtDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-KE", { day: "2-digit", month: "short", year: "numeric" });
}

const SESSION_KEY = (token) => `portal_session_${token}`;

const INVOICE_STATUS = {
  paid: "bg-green-100 text-green-700",
  unpaid: "bg-amber-100 text-amber-700",
  partial: "bg-blue-100 text-blue-700",
};
const QUOTE_STATUS = {
  draft: "bg-gray-100 text-gray-600",
  pending: "bg-amber-100 text-amber-700",
  accepted: "bg-green-100 text-green-700",
  declined: "bg-red-100 text-red-700",
};

function PinEntry({ token, onSuccess }) {
  const [digits, setDigits] = useState(["", "", "", ""]);
  const [error, setError] = useState("");
  const [verifying, setVerifying] = useState(false);
  const inputs = useRef([]);

  const handleChange = (i, val) => {
    if (!/^\d?$/.test(val)) return;
    const next = [...digits];
    next[i] = val;
    setDigits(next);
    if (val && i < 3) inputs.current[i + 1]?.focus();
    if (next.every((d) => d !== "") && val) {
      verify(next.join(""));
    }
  };

  const handleKeyDown = (i, e) => {
    if (e.key === "Backspace" && !digits[i] && i > 0) inputs.current[i - 1]?.focus();
  };

  const verify = async (pin) => {
    setVerifying(true);
    setError("");
    try {
      const { data } = await verifyPortalPin(token, pin);
      sessionStorage.setItem(SESSION_KEY(token), data.session_token);
      onSuccess(data.session_token);
    } catch {
      setError("Incorrect PIN. Please try again.");
      setDigits(["", "", "", ""]);
      inputs.current[0]?.focus();
    } finally {
      setVerifying(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 px-4">
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 w-full max-w-sm text-center space-y-5">
        <div className="h-14 w-14 rounded-full bg-green-100 flex items-center justify-center mx-auto">
          <Lock size={24} className="text-green-600" />
        </div>
        <div>
          <h1 className="text-lg font-bold text-gray-900">Enter your PIN</h1>
          <p className="text-sm text-gray-400 mt-1">This portal is PIN protected. Enter the 4-digit PIN provided to you.</p>
        </div>

        <div className="flex gap-3 justify-center">
          {digits.map((d, i) => (
            <input
              key={i}
              ref={(el) => (inputs.current[i] = el)}
              type="text"
              inputMode="numeric"
              maxLength={1}
              value={d}
              onChange={(e) => handleChange(i, e.target.value)}
              onKeyDown={(e) => handleKeyDown(i, e)}
              className="h-14 w-12 text-center text-2xl font-bold border-2 border-gray-200 rounded-xl focus:border-green-500 focus:ring-0 outline-none transition-colors"
              autoFocus={i === 0}
            />
          ))}
        </div>

        {verifying && <Loader size={20} className="animate-spin text-green-600 mx-auto" />}
        {error && (
          <div className="flex items-center gap-2 text-red-600 text-sm justify-center">
            <AlertCircle size={14} /> {error}
          </div>
        )}

        <p className="text-xs text-gray-400">
          Powered by <span className="font-semibold text-green-600">Kastra</span>
        </p>
      </div>
    </div>
  );
}

export default function ClientPortal() {
  const { token } = useParams();
  const [portal, setPortal] = useState(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [pinRequired, setPinRequired] = useState(false);
  const [sessionToken, setSessionToken] = useState(() => sessionStorage.getItem(SESSION_KEY(token)));
  const [tab, setTab] = useState("invoices");

  const load = async (st) => {
    setLoading(true);
    try {
      const { data } = await getClientPortal(token, st);
      setPortal(data);
      setPinRequired(false);
    } catch (err) {
      if (err.response?.status === 403) {
        setPinRequired(true);
        setSessionToken(null);
        sessionStorage.removeItem(SESSION_KEY(token));
      } else {
        setNotFound(true);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(sessionToken); }, [token]);

  const handlePinSuccess = (st) => {
    setSessionToken(st);
    load(st);
  };

  if (pinRequired) return <PinEntry token={token} onSuccess={handlePinSuccess} />;

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
        <h1 className="text-lg font-bold text-gray-800 mb-1">Portal not found</h1>
        <p className="text-sm text-gray-500">This link may be invalid or expired. Contact the business for a new link.</p>
      </div>
    );

  const unpaidInvoices = portal.invoices.filter((i) => i.payment_status !== "paid").length;

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-2xl mx-auto space-y-5">
        {/* Header */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <p className="text-xs font-semibold uppercase tracking-widest text-green-600 mb-1">
            {portal.business_name}
          </p>
          <h1 className="text-xl font-bold text-gray-900">Welcome, {portal.client_name}</h1>
          <p className="text-sm text-gray-400 mt-0.5">Your documents portal</p>

          {unpaidInvoices > 0 && (
            <div className="mt-4 flex items-center gap-3 p-3 bg-amber-50 border border-amber-200 rounded-xl">
              <CreditCard size={18} className="text-amber-600 shrink-0" />
              <p className="text-sm text-amber-800">
                You have <strong>{unpaidInvoices} unpaid invoice{unpaidInvoices > 1 ? "s" : ""}</strong>. Click an invoice to pay.
              </p>
            </div>
          )}
        </div>

        {/* Tabs */}
        <div className="flex gap-1 bg-white rounded-xl border border-gray-100 p-1 shadow-sm">
          {[
            { key: "invoices", label: `Invoices (${portal.invoices.length})`, icon: Receipt },
            { key: "quotations", label: `Quotations (${portal.quotations.length})`, icon: FileText },
          ].map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium transition-colors ${tab === key ? "bg-green-600 text-white" : "text-gray-500 hover:text-gray-700 hover:bg-gray-50"}`}
            >
              <Icon size={15} /> {label}
            </button>
          ))}
        </div>

        {/* Invoices */}
        {tab === "invoices" && (
          <div className="space-y-2">
            {portal.invoices.length === 0 ? (
              <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 text-center text-sm text-gray-400">No invoices yet.</div>
            ) : portal.invoices.map((inv) => (
              <Link key={inv.id} to={`/pay/${inv.id}?back=/portal/c/${token}`}
                className="block bg-white rounded-2xl shadow-sm border border-gray-100 p-4 hover:border-green-300 transition-colors">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="font-mono font-semibold text-gray-900">{inv.id}</p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {fmtDate(inv.created_at)}
                      {inv.due_date && (
                        <span className={`ml-2 ${inv.is_overdue ? "text-red-500 font-medium" : ""}`}>
                          · Due {fmtDate(inv.due_date)}{inv.is_overdue ? " (Overdue)" : ""}
                        </span>
                      )}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="font-bold text-gray-900">{ksh(inv.grand_total)}</p>
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold mt-1 ${INVOICE_STATUS[inv.payment_status] ?? "bg-gray-100 text-gray-600"}`}>
                      {inv.payment_status === "paid" ? "Paid" : inv.payment_status === "partial" ? "Partial — Pay balance →" : "Pay Now →"}
                    </span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}

        {/* Quotations */}
        {tab === "quotations" && (
          <div className="space-y-2">
            {portal.quotations.length === 0 ? (
              <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 text-center text-sm text-gray-400">No quotations yet.</div>
            ) : portal.quotations.map((qt) => (
              <Link key={qt.id} to={`/portal/q/${qt.id}?back=/portal/c/${token}`}
                className="block bg-white rounded-2xl shadow-sm border border-gray-100 p-4 hover:border-green-300 transition-colors">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="font-mono font-semibold text-gray-900">{qt.id}</p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {fmtDate(qt.created_at)}
                      {qt.expires_at && (
                        <span className={`ml-2 ${qt.is_expired ? "text-orange-500" : ""}`}>
                          · {qt.is_expired ? "Expired" : `Valid until ${fmtDate(qt.expires_at)}`}
                        </span>
                      )}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="font-bold text-gray-900">{ksh(qt.grand_total)}</p>
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold mt-1 ${QUOTE_STATUS[qt.status] ?? "bg-gray-100 text-gray-600"}`}>
                      {qt.status === "pending" ? "Review →" : qt.status.charAt(0).toUpperCase() + qt.status.slice(1)}
                    </span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}

        <p className="text-center text-xs text-gray-400 pb-4">
          Powered by <span className="font-semibold text-green-600">Kastra</span>
        </p>
      </div>
    </div>
  );
}
