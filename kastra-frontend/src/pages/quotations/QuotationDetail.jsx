import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { publicOrigin } from "../../utils/publicUrl";
import { getQuotation, updateQuotationStatus, convertToInvoice, emailQuotation } from "../../api/quotations";
import { getOrganization } from "../../api/organization";
import { ksh, date, phone, statusBadgeClass } from "../../utils/formatters";
import { ArrowLeft, Edit2, RefreshCw, MessageCircle, FileDown, Copy, Mail } from "lucide-react";
import Spinner from "../../components/ui/Spinner";
import ConfirmDialog from "../../components/ui/ConfirmDialog";
import PDFPreviewModal from "../../components/ui/PDFPreviewModal";
import QuotationDocument from "../../components/documents/QuotationDocument";

export default function QuotationDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [quotation, setQuotation] = useState(null);
  const [org, setOrg] = useState({});
  const [loading, setLoading] = useState(true);
  const [showConvert, setShowConvert] = useState(false);
  const [showPDF, setShowPDF] = useState(false);
  const [converting, setConverting] = useState(false);
  const [linkCopied, setLinkCopied] = useState(false);
  const [emailSent, setEmailSent] = useState(false);

  const load = (silent = false) => {
    if (!silent) setLoading(true);
    getQuotation(id).then(({ data }) => setQuotation(data.data)).finally(() => { if (!silent) setLoading(false); });
  };

  useEffect(() => { load(); }, [id]);
  useEffect(() => { getOrganization().then(({ data }) => setOrg(data.data)).catch(() => {}); }, []);

  // Poll every 15s while quotation is pending — auto-update when client accepts/declines
  useEffect(() => {
    const interval = setInterval(() => {
      if (quotation && ["draft", "pending"].includes(quotation.status)) {
        load(true);
      }
    }, 15000);
    return () => clearInterval(interval);
  }, [id, quotation?.status]);

  const handleStatusChange = async (status) => {
    await updateQuotationStatus(id, status);
    load();
  };

  const handleConvert = async () => {
    setConverting(true);
    try {
      const { data } = await convertToInvoice(id);
      navigate(`/invoices/${data.data.invoice_id}`);
    } finally {
      setConverting(false);
    }
  };

  const handleWhatsApp = () => {
    if (!quotation) return;
    const portalLink = `${publicOrigin()}/portal/q/${id}`;
    const msg = [
      `Hello ${quotation.client.name},`,
      ``,
      `Please find quotation *${quotation.id}* for *${ksh(quotation.grand_total)}*.`,
      ``,
      `View and respond here: ${portalLink}`,
      ``,
      `Thank you.`,
    ].join("\n");
    const ph = quotation.client.phone ?? "";
    window.open(`https://wa.me/${ph}?text=${encodeURIComponent(msg)}`, "_blank");
  };

  const handleCopyLink = () => {
    const link = `${publicOrigin()}/portal/q/${id}`;
    navigator.clipboard.writeText(link).then(() => {
      setLinkCopied(true);
      setTimeout(() => setLinkCopied(false), 2000);
    });
  };

  if (loading) return <div className="flex h-96 items-center justify-center"><Spinner size="lg" /></div>;
  if (!quotation) return null;

  const canEdit = ["draft", "pending", "declined"].includes(quotation.status);
  const canConvert = quotation.status === "accepted" && !quotation.converted_to_invoice;
  const nextStatuses = { draft: ["pending"], pending: ["accepted", "declined"], accepted: [], declined: ["pending"] }[quotation.status] ?? [];

  return (
    <div className="p-4 md:p-6 max-w-3xl mx-auto space-y-5">
      <div className="flex items-start gap-3">
        <button onClick={() => navigate(-1)} className="mt-1 text-gray-400 hover:text-gray-600">
          <ArrowLeft size={20} />
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-xl font-bold text-gray-900 font-mono">{quotation.id}</h1>
            <span className={statusBadgeClass(quotation.status)}>{quotation.status}</span>
            {quotation.is_expired && <span className="badge-expired">Expired</span>}
            {quotation.converted_to_invoice && <span className="badge-paid">Converted</span>}
          </div>
          <p className="text-sm text-gray-400 mt-0.5">
            Created {date(quotation.created_at)}
            {quotation.expires_at && (
              <span className={`ml-2 ${quotation.is_expired ? "text-orange-500" : "text-gray-400"}`}>
                · Expires {date(quotation.expires_at)}
              </span>
            )}
          </p>
        </div>
        <div className="flex gap-2 flex-wrap justify-end">
          {canEdit && (
            <button className="btn-secondary" onClick={() => navigate(`/quotations/${id}/edit`)}>
              <Edit2 size={15} /> Edit
            </button>
          )}
          <button className="btn-secondary" onClick={() => setShowPDF(true)}>
            <FileDown size={15} /> PDF
          </button>
          {quotation.client?.email && (
            <button className="btn-secondary" onClick={async () => { try { await emailQuotation(id); setEmailSent(true); setTimeout(() => setEmailSent(false), 3000); } catch {} }} disabled={emailSent}>
              <Mail size={15} /> {emailSent ? "Sent!" : "Email"}
            </button>
          )}
          <button className="btn-secondary" onClick={handleCopyLink}>
            <Copy size={15} /> {linkCopied ? "Copied!" : "Copy Link"}
          </button>
          <button className="btn-secondary" onClick={handleWhatsApp}>
            <MessageCircle size={15} /> WhatsApp
          </button>
          {canConvert && (
            <button className="btn-primary" onClick={() => setShowConvert(true)} disabled={converting}>
              <RefreshCw size={15} /> Convert to Invoice
            </button>
          )}
        </div>
      </div>

      {/* Status actions */}
      {nextStatuses.length > 0 && (
        <div className="flex gap-2 flex-wrap items-center">
          <span className="text-sm text-gray-500">Move to:</span>
          {nextStatuses.map((s) => (
            <button key={s} onClick={() => handleStatusChange(s)}
              className={s === "declined" ? "btn-danger" : "btn-primary"}>
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Client */}
      <div className="card p-4">
        <h2 className="text-xs text-gray-500 uppercase tracking-wide mb-2">Client</h2>
        <p className="font-semibold text-gray-900">{quotation.client.name}</p>
        <p className="text-sm text-gray-500">{quotation.client.email}</p>
        <p className="text-sm text-gray-500">{phone(quotation.client.phone)}</p>
      </div>

      {/* Decline reason */}
      {quotation.status === "declined" && quotation.decline_reason && (
        <div className="card p-4 border-l-4 border-red-400 bg-red-50">
          <h2 className="text-xs text-red-500 uppercase tracking-wide font-semibold mb-1">Decline Reason</h2>
          <p className="text-sm text-red-800 whitespace-pre-line">{quotation.decline_reason}</p>
          {canEdit && (
            <p className="text-xs text-red-400 mt-2">You can edit and re-send this quotation — it will reset to Draft.</p>
          )}
        </div>
      )}
      {quotation.status === "declined" && !quotation.decline_reason && canEdit && (
        <div className="card p-4 bg-amber-50 border border-amber-200">
          <p className="text-xs text-amber-700">Client declined without giving a reason. You can edit and re-send this quotation — it will reset to Draft.</p>
        </div>
      )}

      {/* Items */}
      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left text-xs text-gray-500 uppercase tracking-wide">
            <tr>
              <th className="px-4 py-3">Description</th>
              <th className="px-4 py-3 text-right">Qty</th>
              <th className="px-4 py-3 text-right">Unit Price</th>
              <th className="px-4 py-3 text-right">Total</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {quotation.items.map((item) => (
              <tr key={item.id}>
                <td className="px-4 py-3 text-gray-900">{item.description}</td>
                <td className="px-4 py-3 text-right text-gray-600">{item.quantity}</td>
                <td className="px-4 py-3 text-right text-gray-600">{ksh(item.unit_price)}</td>
                <td className="px-4 py-3 text-right font-medium">{ksh(item.line_total)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="px-4 py-3 border-t border-gray-100 space-y-1.5 text-sm">
          <div className="flex justify-between text-gray-600"><span>Subtotal</span><span>{ksh(quotation.subtotal)}</span></div>
          {Number(quotation.vat_amount) > 0 && (
            <div className="flex justify-between text-gray-600"><span>VAT (16%)</span><span>{ksh(quotation.vat_amount)}</span></div>
          )}
          <div className="flex justify-between font-bold text-gray-900 text-base border-t pt-2">
            <span>Grand Total</span><span>{ksh(quotation.grand_total)}</span>
          </div>
        </div>
      </div>

      {quotation.notes && (
        <div className="card p-4">
          <h2 className="text-xs text-gray-500 uppercase tracking-wide mb-1">Notes</h2>
          <p className="text-sm text-gray-700 whitespace-pre-line">{quotation.notes}</p>
        </div>
      )}

      {/* PDF Preview Modal */}
      <PDFPreviewModal
        open={showPDF}
        onClose={() => setShowPDF(false)}
        title={`${quotation.id} — Quotation`}
      >
        <QuotationDocument quotation={quotation} org={org} />
      </PDFPreviewModal>

      <ConfirmDialog
        open={showConvert}
        onClose={() => setShowConvert(false)}
        onConfirm={handleConvert}
        title="Convert to Invoice"
        message={`Convert ${quotation.id} to an invoice? This creates a new invoice and cannot be undone.`}
      />
    </div>
  );
}
