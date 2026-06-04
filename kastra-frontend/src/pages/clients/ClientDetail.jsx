import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { publicOrigin } from "../../utils/publicUrl";
import { getClient, getClientHistory, updateClient } from "../../api/clients";
import { getQuotations } from "../../api/quotations";
import { getInvoices } from "../../api/invoices";
import { getOrganization } from "../../api/organization";
import { getClientRisk } from "../../api/ai";
import { ksh, phone, date, statusBadgeClass, normalizePhone } from "../../utils/formatters";
import { ArrowLeft, Edit2, Check, X, Copy, MessageCircle, ExternalLink, Lock, LockOpen, RefreshCw, Sparkles, ShieldAlert } from "lucide-react";
import Spinner from "../../components/ui/Spinner";
import Modal from "../../components/ui/Modal";
import api from "../../api/axios";

const PIN_KEY = (id) => `kastra_pin_${id}`;

export default function ClientDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [client, setClient] = useState(null);
  const [stats, setStats] = useState(null);
  const [quotations, setQuotations] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({});
  const [orgName, setOrgName] = useState("");
  const [portalLinkCopied, setPortalLinkCopied] = useState(false);
  const [showPinModal, setShowPinModal] = useState(false);
  const [pinForm, setPinForm] = useState("");
  const [pinSaving, setPinSaving] = useState(false);
  const [generatedPin, setGeneratedPin] = useState(() => sessionStorage.getItem(PIN_KEY(id)));
  const [risk, setRisk] = useState(null);
  const [riskLoading, setRiskLoading] = useState(false);
  const [riskError, setRiskError] = useState("");

  const load = async () => {
    setLoading(true);
    const [cRes, sRes, qRes, iRes] = await Promise.all([
      getClient(id),
      getClientHistory(id),
      getQuotations({ client_id: id, limit: 5 }),
      getInvoices({ client_id: id, limit: 5 }),
    ]);
    setClient(cRes.data.data);
    setStats(sRes.data.data);
    setQuotations(qRes.data.data);
    setInvoices(iRes.data.data);
    setForm(cRes.data.data);
    setLoading(false);
  };

  useEffect(() => { load(); }, [id]);
  useEffect(() => { getOrganization().then(({ data }) => setOrgName(data.data.name)).catch(() => {}); }, []);

  const portalUrl = client ? `${publicOrigin()}/portal/c/${client.portal_token}` : "";

  const handleCopyPortalLink = () => {
    navigator.clipboard.writeText(portalUrl).then(() => {
      setPortalLinkCopied(true);
      setTimeout(() => setPortalLinkCopied(false), 2000);
    });
  };

  const handlePortalWhatsApp = () => {
    if (!client) return;
    const biz = orgName || "us";
    const msg = [
      `Hello ${client.name},`,
      ``,
      `You can view all your invoices and quotations from ${biz} here:`,
      ``,
      portalUrl,
      ``,
      `Tap the link above to pay invoices or respond to quotations.`,
    ].join("\n");
    const ph = normalizePhone(client.phone);
    window.open(`https://wa.me/${ph}?text=${encodeURIComponent(msg)}`, "_blank");
  };

  const handleGeneratePin = async () => {
    setPinSaving(true);
    try {
      const { data } = await api.post(`/api/clients/${id}/pin/generate`);
      sessionStorage.setItem(PIN_KEY(id), data.generated_pin);
      setGeneratedPin(data.generated_pin);
      load();
    } finally {
      setPinSaving(false);
    }
  };

  const handleSetPin = async () => {
    if (pinForm.length !== 4 || !/^\d+$/.test(pinForm)) return;
    setPinSaving(true);
    try {
      await api.post(`/api/clients/${id}/pin`, { pin: pinForm });
      sessionStorage.removeItem(PIN_KEY(id));
      setGeneratedPin(null);
      setShowPinModal(false);
      setPinForm("");
      load();
    } finally {
      setPinSaving(false);
    }
  };

  const handleRemovePin = async () => {
    await api.delete(`/api/clients/${id}/pin`);
    sessionStorage.removeItem(PIN_KEY(id));
    setGeneratedPin(null);
    load();
  };

  const handleSave = async () => {
    await updateClient(id, { name: form.name, email: form.email, phone: form.phone, address: form.address, status: form.status });
    setEditing(false);
    load();
  };

  const handleCheckRisk = async () => {
    setRiskLoading(true);
    setRiskError("");
    try {
      const { data } = await getClientRisk(id);
      setRisk(data);
    } catch (err) {
      setRiskError(err.response?.data?.detail ?? "Could not assess risk.");
    } finally {
      setRiskLoading(false);
    }
  };

  const riskColor = (score) => {
    if (score <= 1) return { bg: "bg-green-50", text: "text-green-700", border: "border-green-200" };
    if (score === 2) return { bg: "bg-yellow-50", text: "text-yellow-700", border: "border-yellow-200" };
    if (score === 3) return { bg: "bg-orange-50", text: "text-orange-700", border: "border-orange-200" };
    return { bg: "bg-red-50", text: "text-red-700", border: "border-red-200" };
  };

  if (loading) return <div className="flex h-96 items-center justify-center"><Spinner size="lg" /></div>;
  if (!client) return null;

  return (
    <div className="p-4 md:p-6 max-w-4xl mx-auto space-y-5">
      <div className="flex items-center gap-3">
        <button onClick={() => navigate(-1)} className="text-gray-400 hover:text-gray-600"><ArrowLeft size={20} /></button>
        <div className="flex-1">
          {editing ? (
            <input className="input text-lg font-bold" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          ) : (
            <h1 className="text-xl font-bold text-gray-900">{client.name}</h1>
          )}
        </div>
        {editing ? (
          <div className="flex gap-2">
            <button className="btn-primary" onClick={handleSave}><Check size={16} /> Save</button>
            <button className="btn-secondary" onClick={() => setEditing(false)}><X size={16} /></button>
          </div>
        ) : (
          <button className="btn-secondary" onClick={() => setEditing(true)}><Edit2 size={15} /> Edit</button>
        )}
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: "Total Billed", value: ksh(stats.total_billed) },
            { label: "Total Invoices", value: stats.invoice_count },
            { label: "Paid", value: stats.paid_count },
            { label: "Unpaid", value: stats.unpaid_count },
          ].map(({ label, value }) => (
            <div key={label} className="card p-4">
              <p className="text-lg font-bold text-gray-900">{value}</p>
              <p className="text-xs text-gray-500">{label}</p>
            </div>
          ))}
        </div>
      )}

      {/* AI Payment Risk */}
      <div className="card p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldAlert size={16} className="text-purple-600" />
            <h2 className="text-sm font-semibold text-gray-700">Payment Risk Score</h2>
          </div>
          <button
            onClick={handleCheckRisk}
            disabled={riskLoading}
            className="flex items-center gap-1.5 text-xs text-purple-700 bg-purple-50 hover:bg-purple-100 border border-purple-200 rounded-lg px-3 py-1.5 font-medium transition-colors disabled:opacity-50"
          >
            {riskLoading ? <RefreshCw size={12} className="animate-spin" /> : <Sparkles size={12} />}
            {risk ? "Re-assess" : "Assess Risk"}
          </button>
        </div>
        {riskError && <p className="text-xs text-red-600">{riskError}</p>}
        {risk && (() => {
          const c = riskColor(risk.score);
          return (
            <div className={`rounded-lg border ${c.border} ${c.bg} p-3 space-y-1.5`}>
              <div className="flex items-center gap-2">
                <span className={`text-lg font-bold ${c.text}`}>{risk.label} Risk</span>
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${c.border} ${c.bg} ${c.text}`}>
                  {risk.score}/5
                </span>
              </div>
              <p className="text-xs text-gray-600">{risk.reason}</p>
              <div className="flex gap-4 text-xs text-gray-500 pt-0.5">
                <span>{risk.late_count} late payment{risk.late_count !== 1 ? "s" : ""} of {risk.total_invoices}</span>
                {risk.avg_days_late > 0 && <span>avg {risk.avg_days_late}d late</span>}
              </div>
            </div>
          );
        })()}
        {!risk && !riskLoading && (
          <p className="text-xs text-gray-400">Click "Assess Risk" to analyse this client's payment behaviour with AI.</p>
        )}
      </div>

      {/* Details */}
      <div className="card p-4 grid sm:grid-cols-2 gap-4">
        {[
          { label: "Email", field: "email", type: "email" },
          { label: "Phone", field: "phone" },
          { label: "Address", field: "address" },
          { label: "Status", field: "status", type: "select", options: ["active", "inactive"] },
        ].map(({ label, field, type, options }) => (
          <div key={field}>
            <p className="text-xs text-gray-500 mb-1">{label}</p>
            {editing ? (
              options ? (
                <select className="input" value={form[field] ?? ""} onChange={(e) => setForm({ ...form, [field]: e.target.value })}>
                  {options.map((o) => <option key={o} value={o}>{o}</option>)}
                </select>
              ) : (
                <input className="input" type={type ?? "text"} value={form[field] ?? ""}
                  onChange={(e) => setForm({ ...form, [field]: e.target.value })} />
              )
            ) : (
              <p className="text-sm font-medium text-gray-900">
                {field === "phone" ? phone(client.phone) : client[field] || "—"}
              </p>
            )}
          </div>
        ))}
      </div>

      {/* Client Portal Link */}
      <div className="card p-4 space-y-3">
        <div>
          <h2 className="text-sm font-semibold text-gray-800">Client Portal</h2>
          <p className="text-xs text-gray-500 mt-0.5">
            Share this private link with {client.name}. They can view all their invoices and quotations, pay online, and accept or decline quotes — no login required.
          </p>
        </div>
        <div className="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-lg px-3 py-2">
          <ExternalLink size={13} className="text-gray-400 shrink-0" />
          <span className="text-xs text-gray-600 font-mono truncate flex-1">{portalUrl}</span>
        </div>
        <div className="flex gap-2">
          <button onClick={handleCopyPortalLink} className="btn-secondary text-xs flex-1">
            <Copy size={13} /> {portalLinkCopied ? "Copied!" : "Copy Link"}
          </button>
          <button onClick={handlePortalWhatsApp} className="btn-secondary text-xs flex-1" disabled={!client.phone}>
            <MessageCircle size={13} /> Send via WhatsApp
          </button>
          <a href={portalUrl} target="_blank" rel="noopener noreferrer" className="btn-secondary text-xs">
            <ExternalLink size={13} /> Preview
          </a>
        </div>
        {!client.phone && (
          <p className="text-xs text-amber-600">Add a phone number to this client to enable WhatsApp sharing.</p>
        )}
      </div>

      {/* Portal PIN */}
      <div className="card p-4 space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-gray-800">Portal PIN Protection</h2>
            <p className="text-xs text-gray-500 mt-0.5">
              {client.pin_enabled
                ? "This portal requires a PIN. The client must enter it before seeing their documents."
                : "Anyone with the portal link can view documents. Enable a PIN for privacy."}
            </p>
          </div>
          <span className={`shrink-0 inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold ${client.pin_enabled ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
            {client.pin_enabled ? <Lock size={11} /> : <LockOpen size={11} />}
            {client.pin_enabled ? "PIN On" : "No PIN"}
          </span>
        </div>

        {generatedPin && (
          <div className="flex items-center gap-3 p-3 bg-green-50 border border-green-200 rounded-xl">
            <Lock size={16} className="text-green-600 shrink-0" />
            <div>
              <p className="text-xs text-green-700 font-medium">New PIN generated — share with client now</p>
              <p className="text-2xl font-bold text-green-800 tracking-widest font-mono mt-0.5">{generatedPin}</p>
              <p className="text-xs text-green-500 mt-0.5">This PIN won't be shown again.</p>
            </div>
          </div>
        )}

        <div className="flex gap-2 flex-wrap">
          <button onClick={handleGeneratePin} disabled={pinSaving} className="btn-secondary text-xs">
            <RefreshCw size={13} /> {client.pin_enabled ? "Regenerate PIN" : "Generate PIN"}
          </button>
          <button onClick={() => { setPinForm(""); setShowPinModal(true); }} className="btn-secondary text-xs">
            <Lock size={13} /> Set Custom PIN
          </button>
          {client.pin_enabled && (
            <button onClick={handleRemovePin} className="btn-secondary text-xs text-red-600 hover:text-red-700">
              <LockOpen size={13} /> Remove PIN
            </button>
          )}
        </div>
      </div>

      <Modal open={showPinModal} onClose={() => setShowPinModal(false)} title="Set Custom PIN" size="sm">
        <div className="space-y-4">
          <p className="text-sm text-gray-500">Enter a 4-digit PIN. Share it with the client separately from the portal link.</p>
          <div>
            <label className="label">4-Digit PIN</label>
            <input
              className="input text-center text-2xl font-bold tracking-widest"
              maxLength={4}
              inputMode="numeric"
              value={pinForm}
              onChange={(e) => setPinForm(e.target.value.replace(/\D/g, "").slice(0, 4))}
              placeholder="e.g. 4829"
            />
          </div>
          <div className="flex gap-2 justify-end">
            <button className="btn-secondary" onClick={() => setShowPinModal(false)}>Cancel</button>
            <button className="btn-primary" onClick={handleSetPin} disabled={pinForm.length !== 4 || pinSaving}>
              {pinSaving ? "Saving…" : "Set PIN"}
            </button>
          </div>
        </div>
      </Modal>

      {/* Quotations */}
      <div className="card">
        <div className="flex items-center justify-between p-4 border-b border-gray-100">
          <h2 className="text-sm font-semibold">Recent Quotations</h2>
          <Link to={`/quotations?client_id=${id}`} className="text-xs text-green-600 hover:underline">View all</Link>
        </div>
        {quotations.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-6">No quotations</p>
        ) : (
          <ul className="divide-y divide-gray-100">
            {quotations.map((q) => (
              <li key={q.id} className="flex items-center gap-3 px-4 py-3">
                <Link to={`/quotations/${q.id}`} className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-green-700">{q.id}</p>
                  <p className="text-xs text-gray-400">{date(q.created_at)}</p>
                </Link>
                <span className={statusBadgeClass(q.status)}>{q.status}</span>
                <span className="text-sm font-semibold">{ksh(q.grand_total)}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Invoices */}
      <div className="card">
        <div className="flex items-center justify-between p-4 border-b border-gray-100">
          <h2 className="text-sm font-semibold">Recent Invoices</h2>
          <Link to={`/invoices?client_id=${id}`} className="text-xs text-green-600 hover:underline">View all</Link>
        </div>
        {invoices.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-6">No invoices</p>
        ) : (
          <ul className="divide-y divide-gray-100">
            {invoices.map((inv) => (
              <li key={inv.id} className="flex items-center gap-3 px-4 py-3">
                <Link to={`/invoices/${inv.id}`} className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-green-700">{inv.id}</p>
                  <p className="text-xs text-gray-400">{date(inv.created_at)}</p>
                </Link>
                <span className={statusBadgeClass(inv.payment_status)}>{inv.payment_status}</span>
                <span className="text-sm font-semibold">{ksh(inv.grand_total)}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
