import QRCode from "react-qr-code";
import { ksh, date, phone } from "../../../utils/formatters";

const KRA_VERIFY_URL = "https://etims.kra.go.ke/etims-portal/searchDetails/";

function EtimsQr({ cuInvoiceNo }) {
  const url = `${KRA_VERIFY_URL}${cuInvoiceNo}`;
  return (
    <div style={{ display: "flex", alignItems: "flex-start", gap: 14, background: "#fffbeb", border: "1px solid #fde68a", borderRadius: 8, padding: "12px 16px", marginBottom: 20 }}>
      <QRCode value={url} size={72} style={{ flexShrink: 0 }} fgColor="#1e293b" />
      <div>
        <div style={{ fontSize: 10, fontWeight: 700, color: "#92400e", textTransform: "uppercase", letterSpacing: 1, marginBottom: 4 }}>KRA eTIMS Verified Receipt</div>
        <div style={{ fontSize: 11, color: "#78350f" }}>CU Invoice No: <strong style={{ fontFamily: "monospace" }}>{cuInvoiceNo}</strong></div>
        <div style={{ fontSize: 10, color: "#b45309", marginTop: 3 }}>Scan QR code to verify on KRA portal</div>
        <div style={{ fontSize: 9, color: "#6b7280", marginTop: 2, wordBreak: "break-all" }}>{url}</div>
      </div>
    </div>
  );
}

const DARK = "#0f172a";
const DARK2 = "#1e293b";
const SLATE = "#475569";
const ACCENT = "#f59e0b";

function LogoOrInitials({ org, size = 52 }) {
  if (org.logo_url) {
    return (
      <img
        src={org.logo_url}
        alt="logo"
        style={{ width: size, height: size, objectFit: "contain", borderRadius: 6, background: "#fff" }}
      />
    );
  }
  const initials = (org.name || "B").split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();
  return (
    <div style={{
      width: size, height: size, borderRadius: 6, background: "rgba(255,255,255,0.15)",
      border: "1.5px solid rgba(255,255,255,0.35)", display: "flex", alignItems: "center",
      justifyContent: "center", fontSize: size * 0.38, fontWeight: 700, color: "#fff",
    }}>
      {initials}
    </div>
  );
}

function ItemsTable({ items }) {
  return (
    <table style={{ width: "100%", borderCollapse: "collapse", marginBottom: 24, fontSize: 13 }}>
      <thead>
        <tr style={{ borderBottom: `2px solid ${DARK2}` }}>
          <th style={{ textAlign: "left", padding: "10px 8px", fontWeight: 700, color: DARK, textTransform: "uppercase", fontSize: 10, letterSpacing: 1 }}>Description</th>
          <th style={{ textAlign: "right", padding: "10px 8px", fontWeight: 700, color: DARK, textTransform: "uppercase", fontSize: 10, letterSpacing: 1, width: 50 }}>Qty</th>
          <th style={{ textAlign: "right", padding: "10px 8px", fontWeight: 700, color: DARK, textTransform: "uppercase", fontSize: 10, letterSpacing: 1, width: 110 }}>Unit Price</th>
          <th style={{ textAlign: "right", padding: "10px 8px", fontWeight: 700, color: DARK, textTransform: "uppercase", fontSize: 10, letterSpacing: 1, width: 110 }}>Amount</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item, i) => (
          <tr key={item.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
            <td style={{ padding: "11px 8px", color: "#1e293b" }}>{item.description}</td>
            <td style={{ padding: "11px 8px", textAlign: "right", color: SLATE }}>{item.quantity}</td>
            <td style={{ padding: "11px 8px", textAlign: "right", color: SLATE }}>{ksh(item.unit_price)}</td>
            <td style={{ padding: "11px 8px", textAlign: "right", fontWeight: 600, color: DARK }}>{ksh(item.line_total)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function ExecutiveTemplate({ org, doc, type }) {
  const isInvoice = type === "invoice";
  const isPaid = isInvoice && doc.payment_status === "paid";
  const isPartial = isInvoice && doc.payment_status === "partial";
  const statusLabel = isInvoice ? doc.payment_status : doc.status;

  return (
    <div id="kastra-document" style={{
      fontFamily: "'Segoe UI', system-ui, sans-serif", fontSize: 13, color: "#334155",
      background: "#fff", minHeight: 900, maxWidth: 700, margin: "0 auto", lineHeight: 1.55,
    }}>
      {/* Dark header band */}
      <div style={{ background: DARK2, padding: "32px 44px 28px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div style={{ display: "flex", alignItems: "flex-start", gap: 14 }}>
            <LogoOrInitials org={org} size={52} />
            <div>
              <div style={{ fontSize: 19, fontWeight: 700, color: "#f8fafc", letterSpacing: -0.3 }}>{org.name || "Your Business"}</div>
              {org.address && <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 3 }}>{org.address}</div>}
              <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 1 }}>
                {[org.phone && phone(org.phone), org.email].filter(Boolean).join("  ·  ")}
              </div>
              {org.kra_pin && <div style={{ fontSize: 11, color: "#64748b", marginTop: 2 }}>KRA PIN: {org.kra_pin}</div>}
            </div>
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: 10, color: "#94a3b8", textTransform: "uppercase", letterSpacing: 2, marginBottom: 6 }}>
              {isInvoice ? "Tax Invoice" : "Quotation"}
            </div>
            <div style={{ fontSize: 26, fontWeight: 800, color: "#f8fafc", fontFamily: "monospace", letterSpacing: -0.5 }}>{doc.id}</div>
            <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 6 }}>Issued: {date(doc.created_at)}</div>
            {isInvoice && doc.due_date && (
              <div style={{ fontSize: 11, color: isPaid ? "#64748b" : ACCENT, marginTop: 2, fontWeight: 600 }}>
                Due: {date(doc.due_date)}
              </div>
            )}
            {isInvoice && doc.quotation_id && (
              <div style={{ fontSize: 11, color: "#64748b", marginTop: 2 }}>Ref: {doc.quotation_id}</div>
            )}
            {isInvoice && doc.lpo_number && (
              <div style={{ fontSize: 11, color: "#64748b", marginTop: 2 }}>LPO: {doc.lpo_number}</div>
            )}
          </div>
        </div>
      </div>

      {/* Amber accent strip */}
      <div style={{ height: 4, background: ACCENT }} />

      {/* Body */}
      <div style={{ padding: "32px 44px" }}>
        {/* Bill To + Status row */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 32 }}>
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, color: "#94a3b8", textTransform: "uppercase", letterSpacing: 1.5, marginBottom: 8 }}>Bill To</div>
            <div style={{ fontWeight: 700, fontSize: 15, color: DARK }}>{doc.client.name}</div>
            {doc.client.email && <div style={{ color: SLATE, marginTop: 3 }}>{doc.client.email}</div>}
            {doc.client.phone && <div style={{ color: SLATE }}>{phone(doc.client.phone)}</div>}
            {doc.client.address && <div style={{ color: SLATE }}>{doc.client.address}</div>}
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: "#94a3b8", textTransform: "uppercase", letterSpacing: 1.5, marginBottom: 8 }}>Status</div>
            <div style={{
              display: "inline-block", padding: "5px 16px", borderRadius: 4,
              fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: 1,
              background: isInvoice
                ? ({ paid: "#dcfce7", partial: "#ffedd5", unpaid: "#fef3c7" }[doc.payment_status] ?? "#fef3c7")
                : ({ accepted: "#dcfce7", pending: "#fef3c7", declined: "#fee2e2", draft: "#f1f5f9" }[doc.status] ?? "#f1f5f9"),
              color: isInvoice
                ? ({ paid: "#15803d", partial: "#c2410c", unpaid: "#92400e" }[doc.payment_status] ?? "#92400e")
                : ({ accepted: "#15803d", pending: "#92400e", declined: "#b91c1c", draft: "#475569" }[doc.status] ?? "#475569"),
            }}>{statusLabel}</div>
          </div>
        </div>

        <ItemsTable items={doc.items} />

        {doc.charges?.length > 0 && (
          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: "#94a3b8", textTransform: "uppercase", letterSpacing: 1.5, marginBottom: 6 }}>Other Charges</div>
            {doc.charges.map((c, i) => (
              <div key={c.id ?? i} style={{ display: "flex", justifyContent: "space-between", padding: "4px 0", fontSize: 12, color: SLATE, borderBottom: "1px solid #f1f5f9" }}>
                <span>{c.description}</span><span>{ksh(c.amount)}</span>
              </div>
            ))}
          </div>
        )}

        {/* Totals */}
        <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 28 }}>
          <div style={{ width: 270, border: "1px solid #e2e8f0", borderRadius: 8, overflow: "hidden" }}>
            <div style={{ display: "flex", justifyContent: "space-between", padding: "9px 16px", background: "#f8fafc", color: SLATE }}>
              <span>Items subtotal</span><span>{ksh(doc.subtotal)}</span>
            </div>
            {Number(doc.total_discount) > 0 && (
              <div style={{ display: "flex", justifyContent: "space-between", padding: "9px 16px", color: "#dc2626", borderTop: "1px solid #e2e8f0" }}>
                <span>Total discount</span><span>− {ksh(doc.total_discount)}</span>
              </div>
            )}
            {Number(doc.charges_total) > 0 && (
              <div style={{ display: "flex", justifyContent: "space-between", padding: "9px 16px", color: SLATE, borderTop: "1px solid #e2e8f0" }}>
                <span>Other charges</span><span>{ksh(doc.charges_total)}</span>
              </div>
            )}
            {Number(doc.vat_amount) > 0 && (
              <div style={{ display: "flex", justifyContent: "space-between", padding: "9px 16px", color: SLATE, borderTop: "1px solid #e2e8f0" }}>
                <span>VAT (16%)</span><span>{ksh(doc.vat_amount)}</span>
              </div>
            )}
            <div style={{ display: "flex", justifyContent: "space-between", padding: "12px 16px", background: DARK2, color: "#fff", fontWeight: 700, fontSize: 15, borderTop: "1px solid #e2e8f0" }}>
              <span>Grand Total</span><span style={{ color: ACCENT }}>{ksh(doc.grand_total)}</span>
            </div>
            {Number(doc.wht_amount) > 0 && (
              <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 16px", background: "#fffbeb", color: "#92400e", fontSize: 11, borderTop: "1px solid #fde68a" }}>
                <span>WHT ({doc.wht_pct}%) — deducted by client</span><span>− {ksh(doc.wht_amount)}</span>
              </div>
            )}
            {isInvoice && Number(doc.deposit_amount) > 0 && (
              <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 16px", background: "#f0fdf4", color: "#15803d", fontSize: 11, borderTop: "1px solid #bbf7d0" }}>
                <span>Deposit received</span><span>− {ksh(doc.deposit_amount)}</span>
              </div>
            )}
            {(Number(doc.wht_amount) > 0 || (isInvoice && Number(doc.deposit_amount) > 0)) && (
              <div style={{ display: "flex", justifyContent: "space-between", padding: "12px 16px", background: DARK2, color: "#fff", fontWeight: 700, fontSize: 14, borderTop: "2px solid #475569" }}>
                <span>Amount Payable</span>
                <span style={{ color: ACCENT }}>{ksh(Number(doc.grand_total) - Number(doc.wht_amount) - (isInvoice ? Number(doc.deposit_amount) : 0))}</span>
              </div>
            )}
            {isInvoice && isPartial && (
              <>
                <div style={{ display: "flex", justifyContent: "space-between", padding: "9px 16px", background: "#f0fdf4", color: "#15803d", fontSize: 13, borderTop: "1px solid #bbf7d0" }}>
                  <span>Amount Paid</span><span>{ksh(doc.amount_paid)}</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", padding: "10px 16px", background: "#fff1f2", color: "#b91c1c", fontWeight: 700, fontSize: 14, borderTop: "1px solid #fecdd3" }}>
                  <span>Balance Due</span><span>{ksh(doc.balance_due)}</span>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Notes */}
        {doc.notes && (
          <div style={{ background: "#f8fafc", borderLeft: `4px solid ${DARK2}`, padding: "12px 16px", marginBottom: 20, borderRadius: "0 6px 6px 0" }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: "#94a3b8", textTransform: "uppercase", letterSpacing: 1, marginBottom: 5 }}>Notes</div>
            <div style={{ color: SLATE, whiteSpace: "pre-line" }}>{doc.notes}</div>
          </div>
        )}

        {/* Payment info */}
        {isInvoice && isPartial && (
          <div style={{ background: "#fff7ed", border: "1px solid #fed7aa", borderRadius: 8, padding: "14px 16px", marginBottom: 20 }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: "#c2410c", textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 }}>Partial Payment Received</div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8, fontSize: 12 }}>
              <div style={{ color: "#15803d" }}><strong>Paid:</strong> {ksh(doc.amount_paid)}</div>
              <div style={{ color: "#b91c1c" }}><strong>Balance:</strong> {ksh(doc.balance_due)}</div>
            </div>
            <div style={{ background: "#fee2e2", borderRadius: 4, height: 6, overflow: "hidden" }}>
              <div style={{ background: "#16a34a", height: "100%", borderRadius: 4, width: `${Math.min(100, (Number(doc.amount_paid) / Number(doc.grand_total)) * 100)}%` }} />
            </div>
            <div style={{ fontSize: 10, color: "#9a3412", marginTop: 4 }}>
              {Math.round((Number(doc.amount_paid) / Number(doc.grand_total)) * 100)}% paid — balance of {ksh(doc.balance_due)} outstanding
            </div>
          </div>
        )}
        {isInvoice && doc.payment_detail && (
          <div style={{ background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: 8, padding: "14px 16px", marginBottom: 20 }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: "#15803d", textTransform: "uppercase", letterSpacing: 1, marginBottom: 6 }}>{isPartial ? "Last Payment Detail" : "Payment Received"}</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "4px 24px", color: "#166534", fontSize: 12 }}>
              <div><strong>Method:</strong> {doc.payment_detail.payment_method}</div>
              <div><strong>Date:</strong> {date(doc.payment_detail.payment_date)}</div>
              {doc.payment_detail.mpesa_receipt_number && <div><strong>M-Pesa Ref:</strong> {doc.payment_detail.mpesa_receipt_number}</div>}
              {doc.payment_detail.transaction_id && !doc.payment_detail.mpesa_receipt_number && <div><strong>Reference:</strong> {doc.payment_detail.transaction_id}</div>}
            </div>
          </div>
        )}
        {isInvoice && !isPaid && (
          <div style={{ background: "#fffbeb", border: "1px solid #fde68a", borderRadius: 8, padding: "14px 16px", marginBottom: 20 }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: "#92400e", textTransform: "uppercase", letterSpacing: 1, marginBottom: 5 }}>Payment Instructions</div>
            <div style={{ color: "#78350f", fontSize: 12 }}>
              {isPartial
                ? <>Balance of <strong style={{ color: "#b91c1c" }}>{ksh(doc.balance_due)}</strong> remaining. Pay via M-Pesa, Bank Transfer, or Cash. Reference: <strong style={{ fontFamily: "monospace" }}>{doc.id}</strong></>
                : <>Pay via M-Pesa, Bank Transfer, or Cash. Reference: <strong style={{ fontFamily: "monospace" }}>{doc.id}</strong></>
              }
            </div>
          </div>
        )}

        {/* eTIMS QR — invoices only */}
        {isInvoice && doc.etims_cu_invoice_no && <EtimsQr cuInvoiceNo={doc.etims_cu_invoice_no} />}

        {/* Signature block — quotations only */}
        {!isInvoice && org.authorised_by && (
          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 36, marginBottom: 8 }}>
            <div style={{ textAlign: "center", minWidth: 220 }}>
              <div style={{ height: 40 }} />
              <div style={{ borderTop: `1.5px solid ${DARK}`, paddingTop: 8 }}>
                <div style={{ fontWeight: 700, fontSize: 13, color: DARK }}>{org.authorised_by}</div>
                <div style={{ fontSize: 11, color: SLATE, marginTop: 2 }}>Authorised Signatory</div>
                <div style={{ fontSize: 11, color: "#94a3b8" }}>{org.name}</div>
              </div>
            </div>
          </div>
        )}

        {/* Footer */}
        <div style={{ borderTop: "1px solid #e2e8f0", marginTop: 32, paddingTop: 14, display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 11, color: "#94a3b8" }}>
          <div>{isInvoice ? "Computer-generated tax invoice. No signature required." : `Valid for ${org.payment_terms_days ?? 30} days from issue date.`}</div>
          <div style={{ fontWeight: 600, color: "#64748b" }}>{org.name || "Your Business"}</div>
        </div>
      </div>
    </div>
  );
}
