import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import FinancialsForm from "./FinancialsForm";

vi.mock("../../api/currency", () => ({ getExchangeRate: vi.fn() }));

/**
 * The live totals preview is what the user checks before sending a quotation
 * or invoice, so the arithmetic behind it is worth pinning: VAT is 16% on the
 * taxable portion only, line discounts come off before the overall discount,
 * and WHT and deposits reduce what's payable without changing the grand total.
 */
const item = (over = {}) => ({ quantity: "1", unit_price: "1000", ...over });

function renderForm(props = {}) {
  return render(
    <FinancialsForm
      items={props.items ?? [item()]}
      charges={props.charges ?? []}
      setCharges={vi.fn()}
      discountPct={props.discountPct ?? ""}
      setDiscountPct={vi.fn()}
      whtPct={props.whtPct ?? ""}
      setWhtPct={vi.fn()}
      {...props}
    />
  );
}

/**
 * Read the amount rendered next to a totals row label.
 *
 * Each row is `<span>label</span><span>amount</span>`, so take the last span.
 * Deduction rows render as "- KSh 15.00"; the sign is styling, not part of the
 * figure under test, so it is stripped.
 */
function amountFor(label) {
  const row = screen.getByText(label).closest("div");
  const spans = row.querySelectorAll("span");
  return spans[spans.length - 1].textContent.replace(/^-\s*/, "").trim();
}

describe("FinancialsForm totals", () => {
  it("subtotals the line items", () => {
    renderForm({ items: [item({ quantity: "10", unit_price: "5000" })] });
    expect(amountFor("Items subtotal")).toBe("KSh 50,000.00");
  });

  it("sums multiple lines", () => {
    renderForm({
      items: [item({ quantity: "2", unit_price: "1500" }), item({ quantity: "3", unit_price: "1000" })],
    });
    expect(amountFor("Items subtotal")).toBe("KSh 6,000.00");
  });

  it("treats blank quantities and prices as zero", () => {
    renderForm({ items: [item({ quantity: "", unit_price: "" })] });
    expect(amountFor("Items subtotal")).toBe("KSh 0.00");
  });

  it("charges 16% VAT on a plain taxable item", () => {
    renderForm({ items: [item({ quantity: "1", unit_price: "1000" })] });
    expect(amountFor("VAT (16%)")).toBe("KSh 160.00");
    expect(amountFor("Grand Total")).toBe("KSh 1,160.00");
  });

  it("exempts an item from VAT when flagged", () => {
    renderForm({ items: [item({ unit_price: "1000", vat_exempt: true })] });
    expect(screen.queryByText("VAT (16%)")).not.toBeInTheDocument();
    expect(amountFor("Grand Total")).toBe("KSh 1,000.00");
  });

  it("taxes only the non-exempt portion of a mixed document", () => {
    renderForm({
      items: [item({ unit_price: "1000" }), item({ unit_price: "1000", vat_exempt: true })],
    });
    expect(amountFor("VAT (16%)")).toBe("KSh 160.00");
    expect(amountFor("Grand Total")).toBe("KSh 2,160.00");
  });

  it("applies a per-line discount", () => {
    renderForm({ items: [item({ unit_price: "1000", discount_pct: "10" })] });
    expect(amountFor("Total discount")).toBe("KSh 100.00");
    // 900 net, VAT 144
    expect(amountFor("Grand Total")).toBe("KSh 1,044.00");
  });

  it("applies the overall discount on top of line discounts", () => {
    renderForm({ items: [item({ unit_price: "1000", discount_pct: "10" })], discountPct: "10" });
    // line 100, then 10% of the 900 net = 90
    expect(amountFor("Total discount")).toBe("KSh 190.00");
  });

  it("discounts the VAT base too, not just the total", () => {
    renderForm({ items: [item({ unit_price: "1000" })], discountPct: "50" });
    expect(amountFor("VAT (16%)")).toBe("KSh 80.00");
    expect(amountFor("Grand Total")).toBe("KSh 580.00");
  });

  it("hides the discount row when there is no discount", () => {
    renderForm();
    expect(screen.queryByText("Total discount")).not.toBeInTheDocument();
  });

  it("adds extra charges to the total and the VAT base", () => {
    renderForm({ charges: [{ description: "Delivery", amount: "500", vat_exempt: false }] });
    expect(amountFor("Other charges")).toBe("KSh 500.00");
    expect(amountFor("VAT (16%)")).toBe("KSh 240.00"); // 16% of 1500
    expect(amountFor("Grand Total")).toBe("KSh 1,740.00");
  });

  it("keeps a VAT-exempt charge out of the VAT base", () => {
    renderForm({ charges: [{ description: "Permit", amount: "500", vat_exempt: true }] });
    expect(amountFor("VAT (16%)")).toBe("KSh 160.00"); // items only
    expect(amountFor("Grand Total")).toBe("KSh 1,660.00");
  });

  it("computes labour as a percentage of the items subtotal", () => {
    renderForm({ labourPct: "20", setLabourPct: vi.fn() });
    expect(amountFor("Labour (20%)")).toBe("KSh 200.00");
    expect(amountFor("VAT (16%)")).toBe("KSh 192.00"); // 16% of 1200
    expect(amountFor("Grand Total")).toBe("KSh 1,392.00");
  });

  it("bases labour on the subtotal before discounts", () => {
    renderForm({ labourPct: "10", setLabourPct: vi.fn(), discountPct: "50" });
    expect(amountFor("Labour (10%)")).toBe("KSh 100.00");
  });

  it("can exempt labour from VAT", () => {
    renderForm({
      labourPct: "20", setLabourPct: vi.fn(),
      labourVatExempt: true, setLabourVatExempt: vi.fn(),
    });
    expect(amountFor("VAT (16%)")).toBe("KSh 160.00"); // items only
    expect(amountFor("Grand Total")).toBe("KSh 1,360.00");
  });

  it("hides labour entirely when the parent does not use it", () => {
    renderForm();
    expect(screen.queryByText(/^Labour/)).not.toBeInTheDocument();
  });

  it("deducts WHT from what is payable but not from the grand total", () => {
    renderForm({ whtPct: "1.5" });
    expect(amountFor("Grand Total")).toBe("KSh 1,160.00");
    expect(amountFor("WHT (1.5%) — deducted by client")).toBe("KSh 15.00");
    expect(amountFor("Amount Payable")).toBe("KSh 1,145.00");
  });

  it("bases WHT on the discounted items, excluding VAT", () => {
    renderForm({ items: [item({ unit_price: "1000", discount_pct: "10" })], whtPct: "10" });
    expect(amountFor("WHT (10%) — deducted by client")).toBe("KSh 90.00");
  });

  it("deducts a deposit from what is payable", () => {
    renderForm({ showDeposit: true, depositAmount: "500", setDepositAmount: vi.fn() });
    expect(amountFor("Grand Total")).toBe("KSh 1,160.00");
    expect(amountFor("Deposit received")).toBe("KSh 500.00");
    expect(amountFor("Amount Payable")).toBe("KSh 660.00");
  });

  it("ignores a deposit on documents that do not take one", () => {
    renderForm({ depositAmount: "500", setDepositAmount: vi.fn(), showDeposit: false });
    expect(screen.queryByText("Deposit received")).not.toBeInTheDocument();
    expect(screen.queryByText("Amount Payable")).not.toBeInTheDocument();
  });

  it("stacks WHT and a deposit", () => {
    renderForm({
      whtPct: "1.5", showDeposit: true, depositAmount: "500", setDepositAmount: vi.fn(),
    });
    expect(amountFor("Amount Payable")).toBe("KSh 645.00"); // 1160 − 15 − 500
  });

  it("shows no payable line when nothing is deducted", () => {
    renderForm();
    expect(screen.queryByText("Amount Payable")).not.toBeInTheDocument();
  });

  it("renders totals in the document currency", () => {
    renderForm({
      items: [item({ unit_price: "100" })],
      currency: "USD", setCurrency: vi.fn(), exchangeRate: "130", setExchangeRate: vi.fn(),
    });
    expect(amountFor("Items subtotal")).toContain("$");
  });

  it("holds up under a full document with every modifier at once", () => {
    renderForm({
      items: [
        item({ quantity: "10", unit_price: "5000", discount_pct: "10" }), // 50,000 → 45,000
        item({ quantity: "1", unit_price: "10000", vat_exempt: true }),   // 10,000 exempt
      ],
      charges: [{ description: "Delivery", amount: "2000", vat_exempt: false }],
      discountPct: "5",
      whtPct: "1.5",
      labourPct: "10", setLabourPct: vi.fn(),
      showDeposit: true, depositAmount: "5000", setDepositAmount: vi.fn(),
    });

    // items gross 60,000; line discounts 5,000; net 55,000; overall 5% = 2,750
    expect(amountFor("Total discount")).toBe("KSh 7,750.00");
    // labour 10% of gross 60,000
    expect(amountFor("Labour (10%)")).toBe("KSh 6,000.00");
    // taxable items 45,000 → less 5% = 42,750; + charges 2,000 + labour 6,000 = 50,750
    expect(amountFor("VAT (16%)")).toBe("KSh 8,120.00");
    // final items 52,250 + charges 2,000 + labour 6,000 + VAT 8,120
    expect(amountFor("Grand Total")).toBe("KSh 68,370.00");
    // WHT 1.5% of final items 52,250
    expect(amountFor("WHT (1.5%) — deducted by client")).toBe("KSh 783.75");
    expect(amountFor("Amount Payable")).toBe("KSh 62,586.25");
  });
});
