export const ksh = (amount) =>
  `KSh ${Number(amount).toLocaleString("en-KE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export const CURRENCY_SYMBOLS = {
  KES: "KSh", USD: "$", EUR: "€", GBP: "£", UGX: "USh",
  TZS: "TSh", ZAR: "R", CNY: "¥", INR: "₹", AED: "AED",
};

// Generic currency formatter — defaults to KES (KSh) when no code given
export const money = (amount, currency = "KES") => {
  const code = (currency || "KES").toUpperCase();
  const symbol = CURRENCY_SYMBOLS[code] ?? code;
  return `${symbol} ${Number(amount).toLocaleString("en-KE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

export const date = (iso) =>
  new Date(iso).toLocaleDateString("en-GB"); // DD/MM/YYYY

export const phone = (p) => {
  if (!p) return "";
  if (p.startsWith("254") && p.length === 12)
    return `+${p.slice(0, 3)} ${p.slice(3, 6)} ${p.slice(6, 9)} ${p.slice(9)}`;
  return p;
};

// Converts any local/international format to WhatsApp-compatible (no +, with country code)
// 0712345678 → 254712345678, +254712345678 → 254712345678, 254712345678 → 254712345678
export const normalizePhone = (raw) => {
  if (!raw) return "";
  let p = raw.replace(/\s+/g, "").replace(/[^0-9+]/g, "");
  if (p.startsWith("+")) p = p.slice(1);
  if (p.startsWith("0")) p = "254" + p.slice(1);
  return p;
};

export const statusBadgeClass = (status) => {
  const map = {
    paid: "badge-paid",
    unpaid: "badge-unpaid",
    pending: "badge-pending",
    accepted: "badge-accepted",
    declined: "badge-declined",
    draft: "badge-draft",
    active: "badge-accepted",
    inactive: "badge-draft",
    overdue: "badge-overdue",
    expired: "badge-expired",
  };
  return map[status] ?? "badge-draft";
};
