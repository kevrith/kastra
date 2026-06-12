import { useState } from "react";
import { Plus, Trash2, RefreshCw } from "lucide-react";
import { money } from "../../utils/formatters";
import { getExchangeRate } from "../../api/currency";

const CURRENCIES = ["KES", "USD", "EUR", "GBP", "UGX", "TZS", "ZAR", "CNY", "INR", "AED"];

const emptyCharge = () => ({ description: "", amount: "", vat_exempt: false });

/**
 * Reusable section for the financial extras on quotation / invoice forms.
 *
 * Props:
 *   items — line items array (read-only here; edited via ProductAutocomplete rows in the parent)
 *   charges / setCharges — extra charges array + setter
 *   discountPct / setDiscountPct
 *   whtPct / setWhtPct
 *   labourPct / setLabourPct — labour as % of items subtotal (omit to hide)
 *   depositAmount / setDepositAmount  (pass null/undefined to hide deposit)
 *   showDeposit — bool (true for invoices only)
 */
export default function FinancialsForm({
  items,
  charges,
  setCharges,
  discountPct,
  setDiscountPct,
  whtPct,
  setWhtPct,
  labourPct,
  setLabourPct,
  labourVatExempt = false,
  setLabourVatExempt,
  depositAmount,
  setDepositAmount,
  showDeposit = false,
  currency = "KES",
  setCurrency,
  exchangeRate = "1",
  setExchangeRate,
}) {
  const [fetchingRate, setFetchingRate] = useState(false);
  const [rateError, setRateError] = useState("");
  const showCurrency = setCurrency !== undefined && setExchangeRate !== undefined;

  const fetchLiveRate = async () => {
    setFetchingRate(true);
    setRateError("");
    try {
      const { data } = await getExchangeRate(currency);
      setExchangeRate(String(data.rate_to_kes));
    } catch (err) {
      setRateError(err.response?.data?.detail ?? "Could not fetch live rate. Enter it manually.");
    } finally {
      setFetchingRate(false);
    }
  };


  const addCharge = () => setCharges((prev) => [...prev, emptyCharge()]);
  const removeCharge = (i) => setCharges((prev) => prev.filter((_, idx) => idx !== i));
  const setCharge = (i, field, value) =>
    setCharges((prev) => prev.map((c, idx) => (idx === i ? { ...c, [field]: value } : c)));

  const showLabour = labourPct !== undefined && setLabourPct !== undefined;

  // Live totals
  const itemsGross = items.reduce((s, it) => s + (parseFloat(it.quantity) || 0) * (parseFloat(it.unit_price) || 0), 0);
  const labourAmount = showLabour ? itemsGross * (parseFloat(labourPct) || 0) / 100 : 0;
  const lineDiscounts = items.reduce((s, it) => {
    const gross = (parseFloat(it.quantity) || 0) * (parseFloat(it.unit_price) || 0);
    return s + gross * (parseFloat(it.discount_pct) || 0) / 100;
  }, 0);
  const itemsNet = itemsGross - lineDiscounts;
  const overallDiscount = itemsNet * (parseFloat(discountPct) || 0) / 100;
  const totalDiscount = lineDiscounts + overallDiscount;
  const finalItems = itemsGross - totalDiscount;
  const chargesTotal = charges.reduce((s, c) => s + (parseFloat(c.amount) || 0), 0);
  const taxableItems = items.reduce((s, it) => {
    if (it.vat_exempt) return s;
    const gross = (parseFloat(it.quantity) || 0) * (parseFloat(it.unit_price) || 0);
    const ld = gross * (parseFloat(it.discount_pct) || 0) / 100;
    return s + (gross - ld);
  }, 0);
  const taxableItemsDiscounted = taxableItems * (1 - (parseFloat(discountPct) || 0) / 100);
  const taxableCharges = charges.reduce((s, c) => c.vat_exempt ? s : s + (parseFloat(c.amount) || 0), 0);
  const taxableLabour = labourVatExempt ? 0 : labourAmount;
  const vat = (taxableItemsDiscounted + taxableCharges + taxableLabour) * 0.16;
  const grandTotal = finalItems + chargesTotal + labourAmount + vat;
  const whtAmount = finalItems * (parseFloat(whtPct) || 0) / 100;
  const depositAmt = showDeposit ? (parseFloat(depositAmount) || 0) : 0;
  const amountPayable = grandTotal - whtAmount - depositAmt;

  return (
    <div className="space-y-5">
      {/* Labour */}
      {showLabour && (
        <div className="card p-4 space-y-3">
          <h2 className="text-sm font-semibold text-gray-700">Labour</h2>
          <div className="flex items-end gap-4">
            <div className="flex-1">
              <label className="label">Labour % of items subtotal</label>
              <div className="relative">
                <input className="input pr-6" type="number" min="0" max="100" step="0.01" placeholder="0"
                  value={labourPct} onChange={(e) => setLabourPct(e.target.value)} />
                <span className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 text-sm">%</span>
              </div>
              <p className="text-xs text-gray-400 mt-1">Calculated on items subtotal before discounts</p>
            </div>
            {labourAmount > 0 && (
              <div className="pb-6 text-sm font-medium text-gray-700">= {money(labourAmount, currency)}</div>
            )}
            {setLabourVatExempt && (
              <div className="pb-6" title={labourVatExempt ? "VAT exempt" : "VAT applies (16%)"}>
                <label className="flex flex-col items-center gap-0.5 cursor-pointer select-none">
                  <input type="checkbox" checked={!labourVatExempt}
                    onChange={(e) => setLabourVatExempt(!e.target.checked)}
                    className="accent-green-600" />
                  <span className="text-[10px] text-gray-400 leading-none">VAT</span>
                </label>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Currency */}
      {showCurrency && (
        <div className="card p-4 space-y-3">
          <h2 className="text-sm font-semibold text-gray-700">Currency</h2>
          <div className={`grid gap-4 ${currency !== "KES" ? "grid-cols-1 sm:grid-cols-2" : "grid-cols-1"}`}>
            <div>
              <label className="label">Document Currency</label>
              <select className="input" value={currency}
                onChange={(e) => {
                  const next = e.target.value;
                  setCurrency(next);
                  if (next === "KES") setExchangeRate("1");
                  setRateError("");
                }}>
                {CURRENCIES.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
              <p className="text-xs text-gray-400 mt-1">Issue this document in a foreign currency for export/diaspora/NGO clients</p>
            </div>
            {currency !== "KES" && (
              <div>
                <label className="label">Exchange Rate (1 {currency} = ? KES)</label>
                <div className="flex gap-2">
                  <input className="input" type="number" min="0" step="any" placeholder="e.g. 129.50"
                    value={exchangeRate} onChange={(e) => setExchangeRate(e.target.value)} required />
                  <button type="button" onClick={fetchLiveRate} disabled={fetchingRate}
                    className="btn-secondary text-xs whitespace-nowrap shrink-0" title="Fetch live rate">
                    <RefreshCw size={13} className={fetchingRate ? "animate-spin" : ""} />
                    {fetchingRate ? "Fetching…" : "Live Rate"}
                  </button>
                </div>
                {rateError && <p className="text-xs text-red-500 mt-1">{rateError}</p>}
                {!rateError && <p className="text-xs text-gray-400 mt-1">Used to report this document's KES equivalent</p>}
              </div>
            )}
          </div>
          {currency !== "KES" && (
            <p className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
              Online payment (M-Pesa / card) is only available for KES documents. Foreign-currency clients should be settled by bank transfer or wire.
            </p>
          )}
        </div>
      )}

      {/* Other Charges */}
      <div className="card p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-700">Other Charges</h2>
          <button type="button" className="btn-secondary text-xs" onClick={addCharge}>
            <Plus size={13} /> Add Charge
          </button>
        </div>
        {charges.length === 0 && (
          <p className="text-xs text-gray-400">No additional charges. Add transport, delivery, installation, etc.</p>
        )}
        {charges.map((charge, i) => (
          <div key={i} className="grid grid-cols-12 gap-2 items-center">
            <div className="col-span-12 sm:col-span-5">
              <input className="input" placeholder="e.g. Transport, Installation" value={charge.description}
                onChange={(e) => setCharge(i, "description", e.target.value)} required />
            </div>
            <div className="col-span-5 sm:col-span-4">
              <input className="input" type="number" placeholder="Amount" min="0" step="any" value={charge.amount}
                onChange={(e) => setCharge(i, "amount", e.target.value)} required />
            </div>
            <div className="col-span-5 sm:col-span-2 flex items-center justify-center" title={charge.vat_exempt ? "VAT exempt" : "VAT applies (16%)"}>
              <label className="flex flex-col items-center gap-0.5 cursor-pointer select-none">
                <input type="checkbox" checked={!charge.vat_exempt}
                  onChange={(e) => setCharge(i, "vat_exempt", !e.target.checked)}
                  className="accent-green-600" />
                <span className="text-[10px] text-gray-400 leading-none">VAT</span>
              </label>
            </div>
            <div className="col-span-2 sm:col-span-1 flex justify-center">
              <button type="button" onClick={() => removeCharge(i)} className="text-gray-400 hover:text-red-600">
                <Trash2 size={14} />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Document-level settings: overall discount, WHT, deposit */}
      <div className="card p-4 space-y-3">
        <h2 className="text-sm font-semibold text-gray-700">Pricing Settings</h2>
        <div className={`grid gap-4 ${showDeposit ? "grid-cols-1 sm:grid-cols-3" : "grid-cols-1 sm:grid-cols-2"}`}>
          <div>
            <label className="label">Overall Discount %</label>
            <div className="relative">
              <input className="input pr-6" type="number" min="0" max="100" step="0.01" placeholder="0"
                value={discountPct} onChange={(e) => setDiscountPct(e.target.value)} />
              <span className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 text-sm">%</span>
            </div>
            <p className="text-xs text-gray-400 mt-1">Applied on net items after line discounts</p>
          </div>
          <div>
            <label className="label">WHT %</label>
            <div className="relative">
              <input className="input pr-6" type="number" min="0" max="100" step="0.01" placeholder="0"
                value={whtPct} onChange={(e) => setWhtPct(e.target.value)} />
              <span className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 text-sm">%</span>
            </div>
            <p className="text-xs text-gray-400 mt-1">Withholding tax deducted by client (1.5%)</p>
          </div>
          {showDeposit && (
            <div>
              <label className="label">Deposit Received</label>
              <input className="input" type="number" min="0" step="any" placeholder="0.00"
                value={depositAmount} onChange={(e) => setDepositAmount(e.target.value)} />
              <p className="text-xs text-gray-400 mt-1">Advance/retainer already paid</p>
            </div>
          )}
        </div>
      </div>

      {/* Live totals preview */}
      <div className="card p-4">
        <div className="space-y-1.5 text-sm">
          <div className="flex justify-between text-gray-600"><span>Items subtotal</span><span>{money(itemsGross, currency)}</span></div>
          {totalDiscount > 0 && (
            <div className="flex justify-between text-red-500"><span>Total discount</span><span>- {money(totalDiscount, currency)}</span></div>
          )}
          {labourAmount > 0 && (
            <div className="flex justify-between text-gray-600"><span>Labour ({labourPct}%)</span><span>{money(labourAmount, currency)}</span></div>
          )}
          {chargesTotal > 0 && (
            <div className="flex justify-between text-gray-600"><span>Other charges</span><span>{money(chargesTotal, currency)}</span></div>
          )}
          {vat > 0 && (
            <div className="flex justify-between text-gray-600"><span>VAT (16%)</span><span>{money(vat, currency)}</span></div>
          )}
          <div className="flex justify-between font-bold text-gray-900 text-base border-t pt-2">
            <span>Grand Total</span><span>{money(grandTotal, currency)}</span>
          </div>
          {whtAmount > 0 && (
            <div className="flex justify-between text-amber-600 text-xs">
              <span>WHT ({whtPct}%) — deducted by client</span><span>- {money(whtAmount, currency)}</span>
            </div>
          )}
          {depositAmt > 0 && (
            <div className="flex justify-between text-green-600 text-xs">
              <span>Deposit received</span><span>- {money(depositAmt, currency)}</span>
            </div>
          )}
          {(whtAmount > 0 || depositAmt > 0) && (
            <div className="flex justify-between font-bold text-gray-900 border-t pt-2">
              <span>Amount Payable</span><span>{money(amountPayable, currency)}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
