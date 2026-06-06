import { useEffect, useRef, useState } from "react";
import { Calculator } from "lucide-react";
import { getCurrencies, getExchangeRate } from "../../api/currency";

const FALLBACK_CURRENCIES = ["USD", "EUR", "GBP", "UGX", "TZS", "ZAR", "CNY", "INR", "AED"];

/**
 * Small popover that converts a foreign-currency amount to its KES equivalent
 * using the live rate, then hands the converted amount back to the caller.
 * Keeps documents single-currency (clean accounting/VAT/eTIMS basis) while
 * making it painless to price dollar-denominated costs like domains/hosting.
 */
export default function PriceConverter({ onApply }) {
  const [open, setOpen] = useState(false);
  const [currencies, setCurrencies] = useState(FALLBACK_CURRENCIES);
  const [code, setCode] = useState("USD");
  const [amount, setAmount] = useState("");
  const [rate, setRate] = useState(null);
  const [loadingRate, setLoadingRate] = useState(false);
  const [error, setError] = useState("");
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    getCurrencies()
      .then(({ data }) => {
        const list = (data?.data ?? []).filter((c) => c !== "KES");
        if (list.length) setCurrencies(list);
      })
      .catch(() => {});
  }, [open]);

  useEffect(() => {
    if (!open) return undefined;
    let cancelled = false;
    setLoadingRate(true);
    setError("");
    setRate(null);
    getExchangeRate(code)
      .then(({ data }) => { if (!cancelled) setRate(data.rate_to_kes); })
      .catch(() => { if (!cancelled) setError("Could not fetch a live rate — enter the converted amount manually instead."); })
      .finally(() => { if (!cancelled) setLoadingRate(false); });
    return () => { cancelled = true; };
  }, [open, code]);

  const numericAmount = Number(amount);
  const kesAmount = rate && amount && numericAmount > 0 ? numericAmount * rate : null;

  const handleApply = () => {
    if (!kesAmount) return;
    onApply({
      kesAmount: Math.round(kesAmount * 100) / 100,
      originalAmount: numericAmount,
      currency: code,
      rate,
    });
    setOpen(false);
    setAmount("");
  };

  return (
    <div className="relative inline-block" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="text-gray-400 hover:text-green-600 p-0.5 transition-colors"
        title="Convert from a foreign currency to KES"
      >
        <Calculator size={14} />
      </button>
      {open && (
        <div className="absolute z-20 right-0 mt-1.5 w-64 bg-white border border-gray-200 rounded-lg shadow-lg p-3 space-y-2 text-left">
          <p className="text-xs font-semibold text-gray-600">Convert to KES</p>
          <div className="flex gap-2">
            <select
              className="rounded-lg border border-gray-300 px-2 py-1.5 text-sm w-24 focus:border-green-500 focus:outline-none focus:ring-1 focus:ring-green-500"
              value={code} onChange={(e) => setCode(e.target.value)}
            >
              {currencies.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
            <input
              className="flex-1 min-w-0 rounded-lg border border-gray-300 px-2 py-1.5 text-sm focus:border-green-500 focus:outline-none focus:ring-1 focus:ring-green-500"
              type="number" min="0" step="any" placeholder="Amount"
              value={amount} onChange={(e) => setAmount(e.target.value)}
              autoFocus
            />
          </div>
          {loadingRate ? (
            <p className="text-xs text-gray-400">Fetching live rate…</p>
          ) : error ? (
            <p className="text-xs text-red-500">{error}</p>
          ) : rate ? (
            <p className="text-xs text-gray-400">1 {code} ≈ KES {rate.toLocaleString()}</p>
          ) : null}
          {kesAmount != null && (
            <p className="text-sm font-semibold text-gray-900">
              ≈ KES {kesAmount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </p>
          )}
          <div className="flex justify-end gap-2 pt-0.5">
            <button type="button" className="text-xs px-2 py-1 rounded-md text-gray-500 hover:bg-gray-100" onClick={() => setOpen(false)}>
              Cancel
            </button>
            <button
              type="button"
              className="text-xs px-2.5 py-1 rounded-md bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
              onClick={handleApply}
              disabled={!kesAmount}
            >
              Use this amount
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
