export const ksh = (amount) =>
  `KSh ${Number(amount).toLocaleString("en-KE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export const date = (iso) =>
  new Date(iso).toLocaleDateString("en-GB"); // DD/MM/YYYY

export const phone = (p) => {
  if (!p) return "";
  if (p.startsWith("254") && p.length === 12)
    return `+${p.slice(0, 3)} ${p.slice(3, 6)} ${p.slice(6, 9)} ${p.slice(9)}`;
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
