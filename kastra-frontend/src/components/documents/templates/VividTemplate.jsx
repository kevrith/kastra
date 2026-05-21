import QRCode from "react-qr-code";
import { ksh, date, phone } from "../../../utils/formatters";

const KRA_VERIFY_URL = "https://etims.kra.go.ke/etims-portal/searchDetails/";

function EtimsQr({ cuInvoiceNo }) {
  const url = `${KRA_VERIFY_URL}${cuInvoiceNo}`;
  return (
    <div style={{ display: "flex", alignItems: "flex-start", gap: 14, background: "#f0fdf4", border: "1px solid #86efac", borderRadius: 10, padding: "14px 16px", marginBottom: 20 }}>
      <QRCode value={url} size={72} style={{ flexShrink: 0 }} fgColor="#15803d" />
      <div>
        <div style={{ fontSize: 10, fontWeight: 700, color: "#15803d", textTransform: "uppercase", letterSpacing: 1, marginBottom: 4 }}>KRA eTIMS Verified Receipt</div>
        <div style={{ fontSize: 11, color: "#166534" }}>CU Invoice No: <strong style={{ fontFamily: "monospace" }}>{cuInvoiceNo}</strong></div>
        <div style={{ fontSize: 10, color: "#4ade80", marginTop: 3 }}>Scan QR code to verify on KRA portal</div>
        <div style={{ fontSize: 9, color: "#6b7280", marginTop: 2, wordBreak: "break-all" }}>{url}</div>
      </div>
    </div>
  );
}

const G1 = "#15803d";
const G2 = "#166534";
const G_LIGHT = "#f0fdf4";
const G_MID = "#dcfce7";

function LogoOrInitials({ org, size = 60 }) {
  if (org.logo_url) {
    return (
      <img
        src={org.logo_url}
        alt="logo"
        style={{ width: size, height: size, objectFit: "contain", borderRadius: 10, background: "#fff", padding: 4 }}
      />
    );
  }
  const initials = (org.name || "B").split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();
  return (
    <div style={{
      width: size, height: size, borderRadius: 10, background: "#fff",
      display: "flex", alignItems: "center", justifyContent: "center",
      fontSize: size * 0.38, fontWeight: 800, color: G1,
    }}>
      {initials}
    </div>
  );
}

function ItemsTable({ items }) {
  return (
    <table style={{ width: "100%", borderCollapse: "collapse", marginBottom: 24, fontSize: 13 }}>
      <thead>
        <tr style={{ background: G1 }}>
          <th style={{ textAlign: "left", padding: "11px 14px", fontWeight: 600, color: "#fff", fontSize: 11, textTransform: "uppercase", letterSpacing: 0.8 }}>Description</th>
          <th style={{ textAlign: "right", padding: "11px 14px", fontWeight: 600, color: "#fff", fontSize: 11, textTransform: "uppercase", letterSpacing: 0.8, width: 50 }}>Qty</th>
          <th style={{ textAlign: "right", padding: "11px 14px", fontWeight: 600, color: "#fff", fontSize: 11, textTransform: "uppercase", letterSpacing: 0.8, width: 115 }}>Unit Price</th>
          <th style={{ textAlign: "right", padding: "11px 14px", fontWeight: 600, color: "#fff", fontSize: 11, textTransform: "uppercase", letterSpacing: 0.8, width: 115 }}>Total</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item, i) => (
          <tr key={item.id} style={{ background: i % 2 === 0 ? "#fff" : G_LIGHT }}>
            <td style={{ padding: "11px 14px", color: "#1f2937", borderBottom: "1px solid #dcfce7" }}>{item.description}</td>
            <td style={{ padding: "11px 14px", textAlign: "right", color: "#6b7280", borderBottom: "1px solid #dcfce7" }}>{item.quantity}</td>
            <td style={{ padding: "11px 14px", textAlign: "right", color: "#6b7280", borderBottom: "1px solid #dcfce7" }}>{ksh(item.unit_price)}</td>
            <td style={{ padding: "11px 14px", textAlign: "right", fontWeight: 600, color: "#111827", borderBottom: "1px solid #dcfce7" }}>{ksh(item.line_total)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function VividTemplate({ org, doc, type }) {
  const isInvoice = type === "invoice";
  const isPaid = isInvoice && doc.payment_status === "paid";
  const isPartial = isInvoice && doc.payment_status === "partial";
  const statusLabel = isInvoice ? doc.payment_status : doc.status;

  const statusBg = isInvoice
    ? ({ paid: "#dcfce7", partial: "#ffedd5", unpaid: "#fee2e2" }[doc.payment_status] ?? "#fee2e2")
    : ({ accepted: "#dcfce7", pending: "#fef3c7", declined: "#fee2e2", draft: "#f3f4f6" }[doc.status] ?? "#f3f4f6");
  const statusText = isInvoice
    ? ({ paid: "#166534", partial: "#c2410c", unpaid: "#991b1b" }[doc.payment_status] ?? "#991b1b")
    : ({ accepted: "#166534", pending: "#92400e", declined: "#991b1b", draft: "#374151" }[doc.status] ?? "#374151");

  return (
    <div id="kastra-document" style={{
      fontFamily: "'Segoe UI', system-ui, sans-serif", fontSize: 13, color: "#1f2937",
      background: "#fff", minHeight: 900, maxWidth: 700, margin: "0 auto", lineHeight: 1.55,
    }}>
      {/* Bold green header */}
      <div style={{ background: `linear-gradient(135deg, ${G1} 0%, ${G2} 100%)`, padding: "36px 48px 0" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", paddingBottom: 28 }}>
          {/* Left: Logo + Business */}
          <div style={{ display: "flex", alignItems: "flex-start", gap: 16 }}>
            <LogoOrInitials org={org} size={60} />
            <div>
              <div style={{ fontSize: 20, fontWeight: 800, color: "#fff", letterSpacing: -0.3 }}>{org.name || "Your Business"}</div>
              {org.address && <div style={{ fontSize: 11, color: "rgba(255,255,255,0.75)", marginTop: 3 }}>{org.address}</div>}
              <div style={{ fontSize: 11, color: "rgba(255,255,255,0.75)", marginTop: 1 }}>
                {[org.phone && phone(org.phone), org.email].filter(Boolean).join("  ·  ")}
              </div>
              {org.kra_pin && <div style={{ fontSize: 11, color: "rgba(255,255,255,0.55)", marginTop: 2 }}>KRA PIN: {org.kra_pin}</div>}
            </div>
          </div>
          {/* Right: Doc info */}
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: 11, color: "rgba(255,255,255,0.65)", textTransform: "uppercase", letterSpacing: 2, marginBottom: 4 }}>
              {isInvoice ? "Tax Invoice" : "Quotation"}
            </div>
            <div style={{ fontSize: 28, fontWeight: 900, color: "#fff", fontFamily: "monospace", letterSpacing: -1 }}>{doc.id}</div>
            <div style={{ fontSize: 11, color: "rgba(255,255,255,0.75)", marginTop: 6 }}>Date: {date(doc.created_at)}</div>
            {isInvoice && doc.due_date && (
              <div style={{ fontSize: 11, color: isPaid ? "rgba(255,255,255,0.55)" : "#fde68a", marginTop: 2, fontWeight: 600 }}>
                Due: {date(doc.due_date)}
              </div>
            )}
            {isInvoice && doc.quotation_id && (
              <div style={{ fontSize: 11, color: "rgba(255,255,255,0.55)", marginTop: 2 }}>Ref: {doc.quotation_id}</div>
            )}
            {isInvoice && doc.lpo_number && (
              <div style={{ fontSize: 11, color: "rgba(255,255,255,0.55)", marginTop: 2 }}>LPO: {doc.lpo_number}</div>
            )}
          </div>
        </div>
        {/* Wave bottom of header */}
        <svg viewBox="0 0 700 40" style={{ display: "block", marginBottom: -1 }} xmlns="http://www.w3.org/2000/svg">
          <path d="M0,20 C175,50 525,-10 700,20 L700,40 L0,40 Z" fill="#fff" />
        </svg>
      </div>

      {/* Body */}
      <div style={{ padding: "4px 48px 40px" }}>
        {/* Bill To + Status */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 28, marginTop: 12 }}>
          <div style={{ background: G_LIGHT, borderRadius: 10, padding: "14px 20px", flex: 1, marginRight: 20 }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: G1, textTransform: "uppercase", letterSpacing: 1.5, marginBottom: 8 }}>Bill To</div>
            <div style={{ fontWeight: 700, fontSize: 15, color: "#111827" }}>{doc.client.name}</div>
            {doc.client.email && <div style={{ color: "#4b5563", marginTop: 3 }}>{doc.client.email}</div>}
            {doc.client.phone && <div style={{ color: "#4b5563" }}>{phone(doc.client.phone)}</div>}
            {doc.client.address && <div style={{ color: "#4b5563" }}>{doc.client.address}</div>}
          </div>
          <div style={{ textAlign: "center", minWidth: 100 }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: "#9ca3af", textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 }}>Status</div>
            <div style={{
              display: "inline-block", padding: "6px 18px", borderRadius: 20,
              fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.8,
              background: statusBg, color: statusText,
            }}>{statusLabel}</div>
          </div>
        </div>

        <ItemsTable items={doc.items} />

        {doc.charges?.length > 0 && (
          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: G1, textTransform: "uppercase", letterSpacing: 1.5, marginBottom: 6 }}>Charges</div>
            {doc.charges.map((c, i) => (
              <div key={c.id ?? i} style={{ display: "flex", justifyContent: "space-between", padding: "4px 0", fontSize: 12, color: "#6b7280", borderBottom: "1px solid #dcfce7" }}>
                <span>{c.description}</span><span>{ksh(c.amount)}</span>
              </div>
            ))}
          </div>
        )}

        {/* Totals */}
        <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 28 }}>
          <div style={{ width: 270, borderRadius: 10, overflow: "hidden", border: "1px solid #dcfce7" }}>
            <div style={{ display: "flex", justifyContent: "space-between", padding: "9px 16px", background: "#f9fafb", color: "#6b7280" }}>
              <span>Items subtotal</span><span>{ksh(doc.subtotal)}</span>
            </div>
            {Number(doc.total_discount) > 0 && (
              <div style={{ display: "flex", justifyContent: "space-between", padding: "9px 16px", color: "#dc2626", borderTop: "1px solid #dcfce7" }}>
                <span>Total discount</span><span>− {ksh(doc.total_discount)}</span>
              </div>
            )}
            {(() => {
              const labour = doc.charges?.find((c) => c.description === "Labour");
              const otherTotal = Number(doc.charges_total) - (labour ? Number(labour.amount) : 0);
              return (
                <>
                  {labour && (
                    <div style={{ display: "flex", justifyContent: "space-between", padding: "9px 16px", color: "#6b7280", borderTop: "1px solid #dcfce7" }}>
                      <span>Labour ({Number(doc.subtotal) > 0 ? Math.round(Number(labour.amount) / Number(doc.subtotal) * 10000) / 100 : 0}%)</span><span>{ksh(labour.amount)}</span>
                    </div>
                  )}
                  {otherTotal > 0 && (
                    <div style={{ display: "flex", justifyContent: "space-between", padding: "9px 16px", color: "#6b7280", borderTop: "1px solid #dcfce7" }}>
                      <span>Other charges</span><span>{ksh(otherTotal)}</span>
                    </div>
                  )}
                </>
              );
            })()}
            {Number(doc.vat_amount) > 0 && (
              <div style={{ display: "flex", justifyContent: "space-between", padding: "9px 16px", color: "#6b7280", borderTop: "1px solid #dcfce7" }}>
                <span>VAT (16%)</span><span>{ksh(doc.vat_amount)}</span>
              </div>
            )}
            <div style={{ display: "flex", justifyContent: "space-between", padding: "13px 16px", background: G1, fontWeight: 800, fontSize: 16, color: "#fff" }}>
              <span>Grand Total</span><span>{ksh(doc.grand_total)}</span>
            </div>
            {Number(doc.wht_amount) > 0 && (
              <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 16px", background: "#fffbeb", color: "#92400e", fontSize: 11, borderTop: "1px solid #fde68a" }}>
                <span>WHT ({doc.wht_pct}%) — deducted</span><span>− {ksh(doc.wht_amount)}</span>
              </div>
            )}
            {isInvoice && Number(doc.deposit_amount) > 0 && (
              <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 16px", background: G_LIGHT, color: G1, fontSize: 11, borderTop: `1px solid ${G_MID}` }}>
                <span>Deposit received</span><span>− {ksh(doc.deposit_amount)}</span>
              </div>
            )}
            {(Number(doc.wht_amount) > 0 || (isInvoice && Number(doc.deposit_amount) > 0)) && (
              <div style={{ display: "flex", justifyContent: "space-between", padding: "12px 16px", background: G2, fontWeight: 800, fontSize: 15, color: "#fff" }}>
                <span>Amount Payable</span>
                <span>{ksh(Number(doc.grand_total) - Number(doc.wht_amount) - (isInvoice ? Number(doc.deposit_amount) : 0))}</span>
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
          <div style={{ background: G_LIGHT, border: `1px solid ${G_MID}`, borderRadius: 8, padding: "14px 16px", marginBottom: 20 }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: G1, textTransform: "uppercase", letterSpacing: 1, marginBottom: 6 }}>Notes</div>
            <div style={{ color: "#374151", whiteSpace: "pre-line" }}>{doc.notes}</div>
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
          <div style={{ background: G_LIGHT, border: `1px solid ${G_MID}`, borderRadius: 8, padding: "14px 16px", marginBottom: 20 }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: G2, textTransform: "uppercase", letterSpacing: 1, marginBottom: 6 }}>{isPartial ? "Last Payment Detail" : "Payment Received"}</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "4px 24px", color: G2, fontSize: 12 }}>
              <div><strong>Method:</strong> {doc.payment_detail.payment_method}</div>
              <div><strong>Date:</strong> {date(doc.payment_detail.payment_date)}</div>
              {doc.payment_detail.mpesa_receipt_number && <div><strong>M-Pesa Ref:</strong> {doc.payment_detail.mpesa_receipt_number}</div>}
              {doc.payment_detail.transaction_id && !doc.payment_detail.mpesa_receipt_number && <div><strong>Reference:</strong> {doc.payment_detail.transaction_id}</div>}
            </div>
          </div>
        )}
        {isInvoice && !isPaid && (
          <div style={{ background: G_LIGHT, border: `1px solid ${G_MID}`, borderRadius: 8, padding: "14px 16px", marginBottom: 20 }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: G1, textTransform: "uppercase", letterSpacing: 1, marginBottom: 5 }}>Payment Instructions</div>
            <div style={{ color: "#374151", fontSize: 12 }}>
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
              <div style={{ borderTop: `1.5px solid ${G2}`, paddingTop: 8 }}>
                <div style={{ fontWeight: 700, fontSize: 13, color: "#111827" }}>{org.authorised_by}</div>
                <div style={{ fontSize: 11, color: "#6b7280", marginTop: 2 }}>Authorised Signatory</div>
                <div style={{ fontSize: 11, color: G1 }}>{org.name}</div>
              </div>
            </div>
          </div>
        )}

        {/* Footer */}
        <div style={{ background: G_LIGHT, borderRadius: 8, padding: "14px 20px", marginTop: 28, display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 11 }}>
          <div style={{ color: "#6b7280" }}>{isInvoice ? "Computer-generated tax invoice. No signature required." : `Valid for ${org.payment_terms_days ?? 30} days from issue date.`}</div>
          <div style={{ fontWeight: 700, color: G1 }}>{org.name || "Your Business"}</div>
        </div>
      </div>
    </div>
  );
}
