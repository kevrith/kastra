import { Plus, Trash2 } from "lucide-react";
import { ksh } from "../../utils/formatters";

const emptyCharge = () => ({ description: "", amount: "", vat_exempt: false });

/**
 * Reusable section for the financial extras on quotation / invoice forms:
 * per-item discount, other charges, overall discount %, WHT, and (optionally) deposit.
 *
 * Props:
 *   items / setItems  — line items array + setter
 *   charges / setCharges — extra charges array + setter
 *   discountPct / setDiscountPct
 *   whtPct / setWhtPct
 *   depositAmount / setDepositAmount  (pass null/undefined to hide deposit)
 *   showDeposit — bool (true for invoices only)
 */
export default function FinancialsForm({
  items,
  setItems,
  charges,
  setCharges,
  discountPct,
  setDiscountPct,
  whtPct,
  setWhtPct,
  depositAmount,
  setDepositAmount,
  showDeposit = false,
}) {
  const setItem = (i, field, value) =>
    setItems((prev) => prev.map((item, idx) => (idx === i ? { ...item, [field]: value } : item)));

  const addCharge = () => setCharges((prev) => [...prev, emptyCharge()]);
  const removeCharge = (i) => setCharges((prev) => prev.filter((_, idx) => idx !== i));
  const setCharge = (i, field, value) =>
    setCharges((prev) => prev.map((c, idx) => (idx === i ? { ...c, [field]: value } : c)));

  // Live totals
  const itemsGross = items.reduce((s, it) => s + (parseFloat(it.quantity) || 0) * (parseFloat(it.unit_price) || 0), 0);
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
  const vat = (taxableItemsDiscounted + taxableCharges) * 0.16;
  const grandTotal = finalItems + chargesTotal + vat;
  const whtAmount = finalItems * (parseFloat(whtPct) || 0) / 100;
  const depositAmt = showDeposit ? (parseFloat(depositAmount) || 0) : 0;
  const amountPayable = grandTotal - whtAmount - depositAmt;

  return (
    <div className="space-y-5">
      {/* Per-item discount column is shown inline in the parent items table via items prop */}
      {/* This section handles Other Charges + document-level settings */}

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
        <div className={`grid gap-4 ${showDeposit ? "grid-cols-3" : "grid-cols-2"}`}>
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
          <div className="flex justify-between text-gray-600"><span>Items subtotal</span><span>{ksh(itemsGross)}</span></div>
          {totalDiscount > 0 && (
            <div className="flex justify-between text-red-500"><span>Total discount</span><span>- {ksh(totalDiscount)}</span></div>
          )}
          {chargesTotal > 0 && (
            <div className="flex justify-between text-gray-600"><span>Other charges</span><span>{ksh(chargesTotal)}</span></div>
          )}
          {vat > 0 && (
            <div className="flex justify-between text-gray-600"><span>VAT (16%)</span><span>{ksh(vat)}</span></div>
          )}
          <div className="flex justify-between font-bold text-gray-900 text-base border-t pt-2">
            <span>Grand Total</span><span>{ksh(grandTotal)}</span>
          </div>
          {whtAmount > 0 && (
            <div className="flex justify-between text-amber-600 text-xs">
              <span>WHT ({whtPct}%) — deducted by client</span><span>- {ksh(whtAmount)}</span>
            </div>
          )}
          {depositAmt > 0 && (
            <div className="flex justify-between text-green-600 text-xs">
              <span>Deposit received</span><span>- {ksh(depositAmt)}</span>
            </div>
          )}
          {(whtAmount > 0 || depositAmt > 0) && (
            <div className="flex justify-between font-bold text-gray-900 border-t pt-2">
              <span>Amount Payable</span><span>{ksh(amountPayable)}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
