import { useEffect, useRef, useState } from "react";
import { useSearchParams, Link, useNavigate } from "react-router-dom";
import { verifyPaystackPayment } from "../../api/portal";
import { CheckCircle, AlertCircle, Loader, RefreshCw, ArrowLeft, FileText } from "lucide-react";

function ksh(val) {
  return `KSh ${Number(val).toLocaleString("en-KE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

const MAX_RETRIES = 4;
const RETRY_DELAY_MS = 3000;

export default function PaystackVerify() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const reference = params.get("reference") || params.get("trxref");

  const [status, setStatus] = useState("verifying"); // verifying | paid | failed
  const [info, setInfo] = useState(null); // { invoice_id, amount, business_name }
  const [retryCount, setRetryCount] = useState(0);
  const [retrying, setRetrying] = useState(false);
  const timerRef = useRef(null);

  // Recover the portal back-link saved before the Paystack redirect
  const backUrl = sessionStorage.getItem("paystack_back_url") || null;

  const verify = async (attempt = 0) => {
    if (!reference) {
      setStatus("failed");
      return;
    }
    try {
      const { data } = await verifyPaystackPayment(reference);
      setInfo({ invoice_id: data.invoice_id, amount: data.amount, business_name: data.business_name });

      if (data.status === "paid") {
        sessionStorage.removeItem("paystack_back_url");
        setStatus("paid");
      } else if (attempt < MAX_RETRIES) {
        setRetryCount(attempt + 1);
        timerRef.current = setTimeout(() => verify(attempt + 1), RETRY_DELAY_MS);
      } else {
        setStatus("failed");
      }
    } catch {
      if (attempt < MAX_RETRIES) {
        setRetryCount(attempt + 1);
        timerRef.current = setTimeout(() => verify(attempt + 1), RETRY_DELAY_MS);
      } else {
        setStatus("failed");
      }
    }
  };

  useEffect(() => {
    verify(0);
    return () => clearTimeout(timerRef.current);
  }, [reference]);

  const handleManualRetry = async () => {
    clearTimeout(timerRef.current);
    setRetrying(true);
    setStatus("verifying");
    setRetryCount(0);
    await verify(0);
    setRetrying(false);
  };

  if (status === "verifying")
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 gap-4 px-4 text-center">
        <Loader size={32} className="animate-spin text-green-600" />
        <p className="font-semibold text-gray-800">Confirming your payment…</p>
        <p className="text-sm text-gray-500">
          {retryCount > 0
            ? `Still verifying… (attempt ${retryCount + 1} of ${MAX_RETRIES + 1})`
            : "Checking with Paystack — this usually takes just a second."}
        </p>
      </div>
    );

  if (status === "paid")
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 px-4 py-10 gap-4">
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 max-w-sm w-full space-y-5 text-center">
          {/* Success icon */}
          <div className="h-16 w-16 rounded-full bg-green-50 flex items-center justify-center mx-auto">
            <CheckCircle size={36} className="text-green-500" />
          </div>

          {/* Headline */}
          <div>
            {info?.business_name && (
              <p className="text-xs font-semibold uppercase tracking-widest text-green-600 mb-1">
                {info.business_name}
              </p>
            )}
            <p className="text-2xl font-bold text-gray-900">Payment Confirmed</p>
            <p className="text-sm text-gray-400 mt-1">
              Your card payment was processed successfully.
            </p>
          </div>

          {/* Amount */}
          {info && (
            <div className="bg-gray-50 rounded-xl py-3 px-4">
              <p className="text-xs text-gray-400 mb-0.5">Amount Paid</p>
              <p className="text-2xl font-bold text-gray-900">{ksh(info.amount)}</p>
              <p className="text-xs text-gray-400 mt-0.5 font-mono">{info.invoice_id}</p>
            </div>
          )}

          <p className="text-xs text-gray-500">
            A receipt has been sent to your email address.
          </p>

          <p className="text-xs text-gray-300 font-mono">Ref: {reference}</p>

          {/* Actions */}
          <div className="space-y-2 pt-1">
            {backUrl ? (
              <button
                onClick={() => navigate(backUrl)}
                className="w-full flex items-center justify-center gap-2 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-xl py-3 transition-colors text-sm"
              >
                <ArrowLeft size={15} />
                Return to Portal
              </button>
            ) : null}
            {info?.invoice_id && (
              <Link
                to={`/pay/${info.invoice_id}${backUrl ? `?back=${encodeURIComponent(backUrl)}` : ""}`}
                className={`w-full flex items-center justify-center gap-2 rounded-xl py-2.5 text-sm font-medium transition-colors border ${
                  backUrl
                    ? "border-gray-200 text-gray-600 hover:border-gray-300 hover:text-gray-800"
                    : "bg-green-600 hover:bg-green-700 text-white border-transparent font-semibold"
                }`}
              >
                <FileText size={15} />
                View Invoice / Receipt
              </Link>
            )}
          </div>
        </div>

        <p className="text-xs text-gray-400">
          Powered by <span className="font-semibold text-green-600">Kastra</span>
        </p>
      </div>
    );

  // Failed / unconfirmed state
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 px-4 text-center gap-4">
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 max-w-sm w-full space-y-4">
        <AlertCircle size={40} className="text-amber-400 mx-auto" />
        <p className="text-lg font-bold text-gray-800">Payment Not Confirmed Yet</p>
        <p className="text-sm text-gray-600">
          We couldn't automatically verify your payment. If you completed it, tap below — it may
          just need another moment to process.
        </p>
        {reference && (
          <p className="text-xs text-gray-400">
            Reference: <span className="font-mono">{reference}</span>
          </p>
        )}

        <button
          onClick={handleManualRetry}
          disabled={retrying}
          className="w-full flex items-center justify-center gap-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white font-semibold rounded-xl py-2.5 transition-colors text-sm"
        >
          {retrying ? <Loader size={15} className="animate-spin" /> : <RefreshCw size={15} />}
          {retrying ? "Checking…" : "Check Payment Status"}
        </button>

        <div className="flex flex-col gap-1.5">
          {backUrl && (
            <button
              onClick={() => navigate(backUrl)}
              className="w-full flex items-center justify-center gap-2 border border-gray-200 text-gray-600 hover:border-gray-300 hover:text-gray-800 rounded-xl py-2.5 text-sm font-medium transition-colors"
            >
              <ArrowLeft size={15} />
              Return to Portal
            </button>
          )}
          {info?.invoice_id && (
            <Link
              to={`/pay/${info.invoice_id}${backUrl ? `?back=${encodeURIComponent(backUrl)}` : ""}`}
              className="block text-sm text-gray-400 hover:text-gray-600 underline"
            >
              View invoice
            </Link>
          )}
        </div>

        <p className="text-xs text-gray-400">
          If you were charged and this keeps happening, contact the business with your reference number.
        </p>
      </div>

      <p className="text-xs text-gray-400">
        Powered by <span className="font-semibold text-green-600">Kastra</span>
      </p>
    </div>
  );
}
