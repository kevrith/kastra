import QRCode from "react-qr-code";
import { ksh, date, phone } from "../../../utils/formatters";

const KRA_VERIFY_URL = "https://etims.kra.go.ke/etims-portal/searchDetails/";

function EtimsQr({ cuInvoiceNo }) {
  const url = `${KRA_VERIFY_URL}${cuInvoiceNo}`;
  return (
    <div style={{ display: "flex", alignItems: "flex-start", gap: 14, background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: 8, padding: "12px 16px", marginBottom: 20 }}>
      <QRCode value={url} size={72} style={{ flexShrink: 0 }} />
      <div>
        <div style={{ fontSize: 10, fontWeight: 700, color: "#15803d", textTransform: "uppercase", letterSpacing: 1, marginBottom: 4 }}>KRA eTIMS Verified Receipt</div>
        <div style={{ fontSize: 11, color: "#166534" }}>CU Invoice No: <strong style={{ fontFamily: "monospace" }}>{cuInvoiceNo}</strong></div>
        <div style={{ fontSize: 10, color: "#4ade80", marginTop: 3 }}>Scan QR code to verify on KRA portal</div>
        <div style={{ fontSize: 9, color: "#6b7280", marginTop: 2, wordBreak: "break-all" }}>{url}</div>
      </div>
    </div>
  );
}

const G = "#16a34a";
const G_LIGHT = "#f0fdf4";

function LogoOrInitials({ org, size = 56 }) {
  if (org.logo_url) {
    return (
      <img
        src={org.logo_url}
        alt="logo"
        style={{ width: size, height: size, objectFit: "contain", borderRadius: 8, border: "1px solid #e5e7eb" }}
      />
    );
  }
  const initials = (org.name || "B").split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();
  return (
    <div style={{
      width: size, height: size, borderRadius: 8, background: G_LIGHT,
      border: `2px solid ${G}`, display: "flex", alignItems: "center",
      justifyContent: "center", fontSize: size * 0.38, fontWeight: 700, color: G,
    }}>
      {initials}
    </div>
  );
}

function ItemsTable({ items }) {
  return (
    <table style={{ width: "100%", borderCollapse: "collapse", marginBottom: 24, fontSize: 13 }}>
      <thead>
        <tr style={{ background: "#f9fafb", borderBottom: `2px solid ${G}` }}>
          <th style={{ textAlign: "left", padding: "10px 12px", fontWeight: 600, color: "#374151" }}>Description</th>
          <th style={{ textAlign: "right", padding: "10px 12px", fontWeight: 600, color: "#374151", width: 55 }}>Qty</th>
          <th style={{ textAlign: "right", padding: "10px 12px", fontWeight: 600, color: "#374151", width: 110 }}>Unit Price</th>
          <th style={{ textAlign: "right", padding: "10px 12px", fontWeight: 600, color: "#374151", width: 110 }}>Total</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item, i) => (
          <tr key={item.id} style={{ background: i % 2 === 0 ? "#fff" : "#f9fafb", borderBottom: "1px solid #f3f4f6" }}>
            <td style={{ padding: "10px 12px", color: "#1f2937" }}>{item.description}</td>
            <td style={{ padding: "10px 12px", textAlign: "right", color: "#6b7280" }}>{item.quantity}</td>
            <td style={{ padding: "10px 12px", textAlign: "right", color: "#6b7280" }}>{ksh(item.unit_price)}</td>
            <td style={{ padding: "10px 12px", textAlign: "right", fontWeight: 500 }}>{ksh(item.line_total)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function ClassicTemplate({ org, doc, type }) {
  const isInvoice = type === "invoice";
  const isPaid = isInvoice && doc.payment_status === "paid";
  const isPartial = isInvoice && doc.payment_status === "partial";

  const statusColor = isInvoice
    ? (
        doc.payment_status === "paid"    ? { bg: "#dcfce7", text: "#15803d" } :
        doc.payment_status === "partial" ? { bg: "#ffedd5", text: "#c2410c" } :
                                           { bg: "#fee2e2", text: "#b91c1c" }
      )
    : ({
        accepted: { bg: "#dcfce7", text: "#15803d" },
        pending:  { bg: "#ffedd5", text: "#c2410c" },
        declined: { bg: "#fee2e2", text: "#b91c1c" },
        draft:    { bg: "#f3f4f6", text: "#374151" },
      }[doc.status] ?? { bg: "#f3f4f6", text: "#374151" });

  const statusLabel = isInvoice ? doc.payment_status : doc.status;

  return (
    <div id="kastra-document" style={{
      fontFamily: "'Segoe UI', system-ui, sans-serif", fontSize: 13, color: "#1f2937",
      background: "#fff", padding: "44px 52px", minHeight: 900, maxWidth: 700,
      margin: "0 auto", lineHeight: 1.55,
    }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 32 }}>
        <div style={{ display: "flex", alignItems: "flex-start", gap: 14 }}>
          <LogoOrInitials org={org} size={56} />
          <div>
            <div style={{ fontSize: 20, fontWeight: 700, color: G, letterSpacing: -0.5 }}>{org.name || "Your Business"}</div>
            {org.address && <div style={{ fontSize: 11, color: "#6b7280", marginTop: 2 }}>{org.address}</div>}
            {org.phone && <div style={{ fontSize: 11, color: "#6b7280" }}>{phone(org.phone)}</div>}
            {org.email && <div style={{ fontSize: 11, color: "#6b7280" }}>{org.email}</div>}
            {org.kra_pin && <div style={{ fontSize: 11, color: "#9ca3af", marginTop: 2 }}>KRA PIN: {org.kra_pin}</div>}
          </div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: 11, color: "#9ca3af", textTransform: "uppercase", letterSpacing: 1.5, marginBottom: 4 }}>
            {isInvoice ? "Tax Invoice" : "Quotation"}
          </div>
          <div style={{ fontSize: 24, fontWeight: 800, color: "#111827", letterSpacing: -0.5, fontFamily: "monospace" }}>{doc.id}</div>
          <div style={{ fontSize: 11, color: "#6b7280", marginTop: 6 }}>Date: {date(doc.created_at)}</div>
          {isInvoice && doc.due_date && (
            <div style={{ fontSize: 11, color: isPaid ? "#9ca3af" : "#b91c1c", marginTop: 2, fontWeight: 600 }}>
              Due: {date(doc.due_date)}
            </div>
          )}
          {isInvoice && doc.quotation_id && (
            <div style={{ fontSize: 11, color: "#9ca3af", marginTop: 2 }}>Ref: {doc.quotation_id}</div>
          )}
          <div style={{
            display: "inline-block", marginTop: 8, padding: "3px 12px", borderRadius: 20,
            fontSize: 10, fontWeight: 600, textTransform: "uppercase", letterSpacing: 0.8,
            background: statusColor.bg, color: statusColor.text,
          }}>{statusLabel}</div>
        </div>
      </div>

      <div style={{ borderTop: `3px solid ${G}`, marginBottom: 28 }} />

      {/* Bill To */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: "#9ca3af", textTransform: "uppercase", letterSpacing: 1.5, marginBottom: 6 }}>Bill To</div>
        <div style={{ fontWeight: 700, fontSize: 14, color: "#111827" }}>{doc.client.name}</div>
        {doc.client.email && <div style={{ color: "#4b5563", marginTop: 2 }}>{doc.client.email}</div>}
        {doc.client.phone && <div style={{ color: "#4b5563" }}>{phone(doc.client.phone)}</div>}
        {doc.client.address && <div style={{ color: "#4b5563" }}>{doc.client.address}</div>}
      </div>

      <ItemsTable items={doc.items} />

      {/* Totals */}
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 28 }}>
        <div style={{ width: 230 }}>
          <div style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", color: "#6b7280" }}>
            <span>Subtotal</span><span>{ksh(doc.subtotal)}</span>
          </div>
          {Number(doc.vat_amount) > 0 && (
            <div style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", color: "#6b7280", borderBottom: "1px solid #e5e7eb" }}>
              <span>VAT (16%)</span><span>{ksh(doc.vat_amount)}</span>
            </div>
          )}
          <div style={{ display: "flex", justifyContent: "space-between", padding: "10px 0 6px", fontWeight: 800, fontSize: 16, marginTop: 4, color: "#111827" }}>
            <span>Grand Total</span><span style={{ color: G }}>{ksh(doc.grand_total)}</span>
          </div>
          {isInvoice && isPartial && (
            <>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", color: "#15803d", borderTop: "1px dashed #e5e7eb", marginTop: 2, fontSize: 13 }}>
                <span>Amount Paid</span><span>{ksh(doc.amount_paid)}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", fontWeight: 700, color: "#b91c1c", fontSize: 14 }}>
                <span>Balance Due</span><span>{ksh(doc.balance_due)}</span>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Notes */}
      {doc.notes && (
        <div style={{ background: "#f9fafb", border: "1px solid #e5e7eb", borderRadius: 8, padding: "14px 16px", marginBottom: 20 }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: "#9ca3af", textTransform: "uppercase", letterSpacing: 1, marginBottom: 6 }}>Notes</div>
          <div style={{ color: "#4b5563", whiteSpace: "pre-line" }}>{doc.notes}</div>
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
        <div style={{ background: G_LIGHT, border: `1px solid #bbf7d0`, borderRadius: 8, padding: "14px 16px", marginBottom: 20 }}>
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
        <div style={{ background: "#f9fafb", border: "1px solid #e5e7eb", borderRadius: 8, padding: "14px 16px", marginBottom: 20 }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: "#9ca3af", textTransform: "uppercase", letterSpacing: 1, marginBottom: 6 }}>Payment Instructions</div>
          <div style={{ color: "#4b5563", fontSize: 12 }}>
            {isPartial
              ? <>Balance of <strong style={{ color: "#b91c1c" }}>{ksh(doc.balance_due)}</strong> remaining. Pay via M-Pesa, Bank Transfer, or Cash. Reference: <strong style={{ fontFamily: "monospace" }}>{doc.id}</strong></>
              : <>Pay via M-Pesa, Bank Transfer, or Cash. Use reference: <strong style={{ fontFamily: "monospace" }}>{doc.id}</strong></>
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
            <div style={{ borderTop: `1.5px solid #374151`, paddingTop: 8 }}>
              <div style={{ fontWeight: 700, fontSize: 13, color: "#111827" }}>{org.authorised_by}</div>
              <div style={{ fontSize: 11, color: "#6b7280", marginTop: 2 }}>Authorised Signatory</div>
              <div style={{ fontSize: 11, color: "#9ca3af" }}>{org.name}</div>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <div style={{ borderTop: "1px solid #e5e7eb", marginTop: 32, paddingTop: 16, textAlign: "center", fontSize: 11, color: "#9ca3af" }}>
        <div>{isInvoice ? "This is a computer-generated tax invoice. No signature required." : `This quotation is valid for ${org.payment_terms_days ?? 30} days.`}</div>
        <div style={{ marginTop: 4 }}>{org.name || "Your Business"}</div>
      </div>
    </div>
  );
}
