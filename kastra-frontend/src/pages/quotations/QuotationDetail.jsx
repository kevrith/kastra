import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { publicOrigin } from "../../utils/publicUrl";
import { getQuotation, updateQuotationStatus, convertToInvoice, emailQuotation, getQuotationNotes, addQuotationNote } from "../../api/quotations";
import { getInvoices } from "../../api/invoices";
import { getOrganization } from "../../api/organization";
import { createProject, listProjects } from "../../api/projects";
import { ksh, date, phone, statusBadgeClass } from "../../utils/formatters";
import { ArrowLeft, Edit2, RefreshCw, MessageCircle, FileDown, Copy, Mail, Receipt, StickyNote, Send, Briefcase } from "lucide-react";
import Spinner from "../../components/ui/Spinner";
import Modal from "../../components/ui/Modal";
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
  const [convertError, setConvertError] = useState("");
  const [lpoNumber, setLpoNumber] = useState("");
  const [lpoQtys, setLpoQtys] = useState({});
  const [relatedInvoices, setRelatedInvoices] = useState([]);
  const [linkCopied, setLinkCopied] = useState(false);
  const [emailSent, setEmailSent] = useState(false);
  const [notes, setNotes] = useState([]);
  const [noteBody, setNoteBody] = useState("");
  const [addingNote, setAddingNote] = useState(false);
  const [showProjectModal, setShowProjectModal] = useState(false);
  const [creatingProject, setCreatingProject] = useState(false);
  const [projectError, setProjectError] = useState("");
  const [existingProject, setExistingProject] = useState(null);

  const load = (silent = false) => {
    if (!silent) setLoading(true);
    getQuotation(id).then(({ data }) => setQuotation(data.data)).finally(() => { if (!silent) setLoading(false); });
  };

  useEffect(() => { load(); }, [id]);
  useEffect(() => { getOrganization().then(({ data }) => setOrg(data.data)).catch(() => {}); }, []);
  useEffect(() => {
    getInvoices({ quotation_id: id, limit: 50 }).then(({ data }) => setRelatedInvoices(data.data)).catch(() => {});
  }, [id]);

  useEffect(() => {
    listProjects().then(({ data }) => {
      // Handle both direct array and wrapped response
      const projects = Array.isArray(data) ? data : (data.data || []);
      const proj = projects.find(p => p.quotation_id === id);
      console.log('Projects loaded:', projects);
      console.log('Looking for quotation_id:', id);
      console.log('Found project:', proj);
      setExistingProject(proj || null);
    }).catch((err) => {
      console.error('Failed to load projects:', err);
      setExistingProject(null);
    });
  }, [id]);

  useEffect(() => {
    getQuotationNotes(id).then(({ data }) => setNotes(data)).catch(() => {});
  }, [id]);

  const handleAddNote = async () => {
    if (!noteBody.trim()) return;
    setAddingNote(true);
    try {
      const { data } = await addQuotationNote(id, noteBody.trim());
      setNotes((prev) => [...prev, data]);
      setNoteBody("");
    } finally {
      setAddingNote(false);
    }
  };

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
    setConvertError("");
    try {
      const item_quantities = quotation.items
        .filter((item) => lpoQtys[item.sort_order] !== undefined && lpoQtys[item.sort_order] !== String(item.quantity))
        .map((item) => ({ sort_order: item.sort_order, quantity: parseFloat(lpoQtys[item.sort_order]) }));

      const { data } = await convertToInvoice(id, {
        lpo_number: lpoNumber || null,
        item_quantities: item_quantities.length > 0 ? item_quantities : null,
      });
      const newInvId = data.data.invoice_id;
      setShowConvert(false);
      setLpoNumber("");
      setLpoQtys({});
      setRelatedInvoices((prev) => [...prev, { id: newInvId, lpo_number: lpoNumber || null }]);
      navigate(`/invoices/${newInvId}`);
    } catch (err) {
      setConvertError(err.response?.data?.detail ?? "Failed to create invoice");
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
      ...(quotation.project_description ? [`Project: *${quotation.project_description}*`, ``] : []),
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

  const handleCreateProject = async () => {
    setCreatingProject(true);
    setProjectError("");
    try {
      const { data } = await createProject({
        quotation_id: id,
        title: quotation.project_description || `Project for ${quotation.client.name}`,
        description: quotation.notes || null,
        assigned_to: null,
        target_date: null
      });
      setShowProjectModal(false);
      navigate(`/projects/${data.id}`);
    } catch (err) {
      setProjectError(err.response?.data?.detail ?? "Failed to create project");
    } finally {
      setCreatingProject(false);
    }
  };

  if (loading) return <div className="flex h-96 items-center justify-center"><Spinner size="lg" /></div>;
  if (!quotation) return null;

  const canEdit = ["draft", "pending", "declined"].includes(quotation.status);
  const canConvert = quotation.status === "accepted";
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
            {quotation.accepted_at && (
              <span className="ml-2 text-green-600">
                · Accepted {new Date(quotation.accepted_at).toLocaleString("en-KE", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" })}
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
          {canConvert && !existingProject && (
            <button className="btn-secondary" onClick={() => { setShowProjectModal(true); setProjectError(""); }}>
              <Briefcase size={15} /> Convert to Project
            </button>
          )}
          {existingProject && (
            <button className="btn-secondary" onClick={() => navigate(`/projects/${existingProject.id}`)}>
              <Briefcase size={15} /> View Project
            </button>
          )}
          {canConvert && (
            <button className="btn-primary" onClick={() => { setShowConvert(true); setConvertError(""); setLpoNumber(""); setLpoQtys({}); }} disabled={converting}>
              <RefreshCw size={15} /> {quotation.converted_to_invoice ? "New Invoice (LPO)" : "Convert to Invoice"}
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

      {/* Project description */}
      {quotation.project_description && (
        <div className="card p-4">
          <h2 className="text-xs text-gray-500 uppercase tracking-wide mb-1">Project</h2>
          <p className="text-sm text-gray-800 whitespace-pre-line">{quotation.project_description}</p>
        </div>
      )}

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
        {quotation.charges?.length > 0 && (
          <div className="px-4 py-2 border-t border-gray-100">
            <p className="text-xs text-gray-400 uppercase tracking-wide mb-1.5">Charges</p>
            {quotation.charges.map((c) => (
              <div key={c.id} className="flex justify-between text-sm text-gray-600 py-0.5">
                <span>{c.description}</span><span>{ksh(c.amount)}</span>
              </div>
            ))}
          </div>
        )}
        <div className="px-4 py-3 border-t border-gray-100 space-y-1.5 text-sm">
          <div className="flex justify-between text-gray-600"><span>Items subtotal</span><span>{ksh(quotation.subtotal)}</span></div>
          {Number(quotation.total_discount) > 0 && (
            <div className="flex justify-between text-red-500"><span>Total discount</span><span>− {ksh(quotation.total_discount)}</span></div>
          )}
          {(() => {
            const labourCharge = quotation.charges?.find((c) => c.description === "Labour");
            const otherChargesTotal = Number(quotation.charges_total) - (labourCharge ? Number(labourCharge.amount) : 0);
            return (
              <>
                {labourCharge && (
                  <div className="flex justify-between text-gray-600"><span>Labour ({Number(quotation.subtotal) > 0 ? Math.round(Number(labourCharge.amount) / Number(quotation.subtotal) * 10000) / 100 : 0}%)</span><span>{ksh(labourCharge.amount)}</span></div>
                )}
                {otherChargesTotal > 0 && (
                  <div className="flex justify-between text-gray-600"><span>Other charges</span><span>{ksh(otherChargesTotal)}</span></div>
                )}
              </>
            );
          })()}
          {Number(quotation.vat_amount) > 0 && (
            <div className="flex justify-between text-gray-600"><span>VAT (16%)</span><span>{ksh(quotation.vat_amount)}</span></div>
          )}
          <div className="flex justify-between font-bold text-gray-900 text-base border-t pt-2">
            <span>Grand Total</span><span>{ksh(quotation.grand_total)}</span>
          </div>
          {Number(quotation.wht_amount) > 0 && (
            <div className="flex justify-between text-amber-600 text-xs">
              <span>WHT ({quotation.wht_pct}%) — deducted by client</span>
              <span>− {ksh(quotation.wht_amount)}</span>
            </div>
          )}
          {Number(quotation.wht_amount) > 0 && (
            <div className="flex justify-between font-bold text-gray-900 border-t pt-2">
              <span>Amount Payable</span>
              <span>{ksh(Number(quotation.grand_total) - Number(quotation.wht_amount))}</span>
            </div>
          )}
        </div>
      </div>

      {quotation.notes && (
        <div className="card p-4">
          <h2 className="text-xs text-gray-500 uppercase tracking-wide mb-1">Notes</h2>
          <p className="text-sm text-gray-700 whitespace-pre-line">{quotation.notes}</p>
        </div>
      )}

      {/* Related invoices */}
      {relatedInvoices.length > 0 && (
        <div className="card p-4 space-y-2">
          <h2 className="text-xs text-gray-500 uppercase tracking-wide flex items-center gap-1.5">
            <Receipt size={13} /> Invoices from this Quotation
          </h2>
          <div className="divide-y divide-gray-100">
            {relatedInvoices.map((inv) => (
              <div key={inv.id} className="flex items-center justify-between py-2 text-sm">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-xs text-green-700 font-medium">{inv.id}</span>
                  {inv.lpo_number && (
                    <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">LPO: {inv.lpo_number}</span>
                  )}
                </div>
                <button className="text-xs text-green-600 hover:underline" onClick={() => navigate(`/invoices/${inv.id}`)}>
                  View →
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Internal Notes */}
      <div className="card p-4 space-y-3">
        <h2 className="text-xs text-gray-500 uppercase tracking-wide flex items-center gap-1.5">
          <StickyNote size={13} /> Internal Notes
          <span className="text-gray-300 font-normal normal-case">— private, not visible to client</span>
        </h2>
        {notes.length > 0 && (
          <div className="space-y-2">
            {notes.map((n) => (
              <div key={n.id} className="bg-amber-50 border border-amber-100 rounded-lg px-3 py-2.5">
                <p className="text-sm text-gray-800 whitespace-pre-line">{n.body}</p>
                <p className="text-[10px] text-gray-400 mt-1">
                  {n.author_name} · {new Date(n.created_at).toLocaleString("en-KE", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}
                </p>
              </div>
            ))}
          </div>
        )}
        <div className="flex gap-2">
          <textarea
            className="input flex-1 resize-none"
            rows={2}
            placeholder="Add a note… e.g. Called Kevin, said he'll decide by Friday"
            value={noteBody}
            onChange={(e) => setNoteBody(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleAddNote(); }}
          />
          <button
            className="btn-primary self-end"
            onClick={handleAddNote}
            disabled={addingNote || !noteBody.trim()}
          >
            <Send size={14} />
          </button>
        </div>
      </div>

      {/* PDF Preview Modal */}
      <PDFPreviewModal
        open={showPDF}
        onClose={() => setShowPDF(false)}
        title={`${quotation.id} — Quotation`}
      >
        <QuotationDocument quotation={quotation} org={org} />
      </PDFPreviewModal>

      {/* Convert to Project Modal */}
      <Modal
        open={showProjectModal}
        onClose={() => setShowProjectModal(false)}
        title="Convert to Project"
        size="sm"
      >
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            Create a project to track work for <strong>{quotation.client.name}</strong>.
          </p>
          <div className="bg-gray-50 p-3 rounded-lg space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">Project Title:</span>
              <span className="font-medium text-gray-900">{quotation.project_description || `Project for ${quotation.client.name}`}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Client:</span>
              <span className="font-medium text-gray-900">{quotation.client.name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Quotation:</span>
              <span className="font-mono text-xs text-gray-700">{quotation.id}</span>
            </div>
          </div>
          <p className="text-xs text-gray-500">
            You can assign team members and set target dates after creating the project.
          </p>
          {projectError && <p className="text-xs text-red-600">{projectError}</p>}
        </div>
        <div className="mt-4 flex justify-end gap-2">
          <button className="btn-secondary" onClick={() => setShowProjectModal(false)}>Cancel</button>
          <button className="btn-primary" onClick={handleCreateProject} disabled={creatingProject}>
            {creatingProject ? "Creating…" : "Create Project"}
          </button>
        </div>
      </Modal>

      {/* LPO / Invoice creation modal */}
      <Modal
        open={showConvert}
        onClose={() => setShowConvert(false)}
        title={quotation.converted_to_invoice ? "Create Invoice from LPO" : "Convert to Invoice"}
        size="md"
      >
        <p className="text-sm text-gray-500 mb-4">
          Invoice for <strong>{quotation.client.name}</strong> · <span className="font-mono">{quotation.id}</span>
        </p>
        <div className="space-y-4">
          <div>
            <label className="label">LPO Number <span className="text-gray-400 font-normal">(optional)</span></label>
            <input
              className="input"
              type="text"
              placeholder="e.g. LPO-2026-001"
              value={lpoNumber}
              onChange={(e) => setLpoNumber(e.target.value)}
            />
          </div>

          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
              Delivery Quantities <span className="normal-case text-gray-400 font-normal">(adjust for partial LPO — unit prices are locked)</span>
            </p>
            <div className="border border-gray-100 rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-xs text-gray-500">
                  <tr>
                    <th className="px-3 py-2 text-left">Item</th>
                    <th className="px-3 py-2 text-right">Quoted Qty</th>
                    <th className="px-3 py-2 text-right w-28">This LPO Qty</th>
                    <th className="px-3 py-2 text-right">Unit Price</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {quotation.items.map((item) => (
                    <tr key={item.id}>
                      <td className="px-3 py-2 text-gray-800 truncate max-w-[160px]">{item.description}</td>
                      <td className="px-3 py-2 text-right text-gray-400">{item.quantity}</td>
                      <td className="px-3 py-2 text-right">
                        <input
                          type="number"
                          min="0.01"
                          step="any"
                          className="input text-right py-1 px-2 text-xs w-24"
                          value={lpoQtys[item.sort_order] ?? String(item.quantity)}
                          onChange={(e) => setLpoQtys((prev) => ({ ...prev, [item.sort_order]: e.target.value }))}
                        />
                      </td>
                      <td className="px-3 py-2 text-right text-gray-500 text-xs">{ksh(item.unit_price)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {convertError && <p className="text-xs text-red-600">{convertError}</p>}
        </div>
        <div className="mt-4 flex justify-end gap-2">
          <button className="btn-secondary" onClick={() => setShowConvert(false)}>Cancel</button>
          <button className="btn-primary" onClick={handleConvert} disabled={converting}>
            {converting ? "Creating…" : "Create Invoice"}
          </button>
        </div>
      </Modal>
    </div>
  );
}
