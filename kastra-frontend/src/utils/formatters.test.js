import { describe, expect, it } from "vitest";
import { CURRENCY_SYMBOLS, date, ksh, money, normalizePhone, phone, statusBadgeClass } from "./formatters";

describe("ksh", () => {
  it("formats with KSh prefix and two decimals", () => {
    expect(ksh(50000)).toBe("KSh 50,000.00");
    expect(ksh("1234.5")).toBe("KSh 1,234.50");
    expect(ksh(0)).toBe("KSh 0.00");
  });
});

describe("money", () => {
  it("defaults to KES", () => {
    expect(money(1000)).toBe("KSh 1,000.00");
    expect(money(1000, null)).toBe("KSh 1,000.00");
  });

  it("uses the known symbol for supported currencies", () => {
    expect(money(99.9, "USD")).toBe("$ 99.90");
    expect(money(99.9, "usd")).toBe("$ 99.90");
    expect(money(1500, "EUR")).toBe("€ 1,500.00");
  });

  it("falls back to the raw code for unknown currencies", () => {
    expect(money(10, "JPY")).toBe("JPY 10.00");
  });

  it("has a symbol for every advertised currency", () => {
    for (const code of Object.keys(CURRENCY_SYMBOLS)) {
      expect(money(1, code)).not.toContain("undefined");
    }
  });
});

describe("date", () => {
  it("renders DD/MM/YYYY", () => {
    // midday UTC so the assertion holds in any timezone west of UTC-11
    expect(date("2026-06-12T12:00:00Z")).toBe("12/06/2026");
  });
});

describe("phone", () => {
  it("pretty-prints 254 numbers", () => {
    expect(phone("254712345678")).toBe("+254 712 345 678");
  });

  it("leaves other formats untouched", () => {
    expect(phone("0712345678")).toBe("0712345678");
    expect(phone("")).toBe("");
    expect(phone(null)).toBe("");
  });
});

describe("normalizePhone", () => {
  it("converts local format to WhatsApp format", () => {
    expect(normalizePhone("0712345678")).toBe("254712345678");
  });

  it("strips plus and whitespace", () => {
    expect(normalizePhone("+254 712 345 678")).toBe("254712345678");
    expect(normalizePhone("254712345678")).toBe("254712345678");
  });

  it("strips non-numeric characters", () => {
    expect(normalizePhone("(0712) 345-678")).toBe("254712345678");
  });

  it("handles empty input", () => {
    expect(normalizePhone("")).toBe("");
    expect(normalizePhone(null)).toBe("");
  });
});

describe("statusBadgeClass", () => {
  it("maps known statuses", () => {
    expect(statusBadgeClass("paid")).toBe("badge-paid");
    expect(statusBadgeClass("overdue")).toBe("badge-overdue");
  });

  it("falls back to draft for unknown statuses", () => {
    expect(statusBadgeClass("whatever")).toBe("badge-draft");
    expect(statusBadgeClass(undefined)).toBe("badge-draft");
  });
});
