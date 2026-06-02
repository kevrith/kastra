import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  getSupplierRequest, getComparison, addInvite, removeInvite,
  closeSupplierRequest, getSuppliers,
} from "../../api/suppliers";
import { ksh } from "../../utils/formatters";
import { publicOrigin } from "../../utils/publicUrl";
import {
  ArrowLeft, Copy, MessageCircle, CheckCircle, Clock, Plus, Trash2,
  BarChart2, Users, Lock, RefreshCw,
} from "lucide-react";
import Spinner from "../../components/ui/Spinner";
import Modal from "../../components/ui/Modal";
import ConfirmDialog from "../../components/ui/ConfirmDialog";

function StatusBadge({ status }) {
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold ${
      status === "responded" ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"
    }`}>
      {status === "responded" ? <CheckCircle size={11} /> : <Clock size={11} />}
      {status === "responded" ? "Responded" : "Pending"}
    </span>
  );
}

function ComparisonTable({ comparison }) {
  const { suppliers, rows, totals } = comparison;
  if (suppliers.length === 0) {
    return (
      <div className="card p-8 text-center text-sm text-gray-400">
        No responses yet. Share the portal link with your suppliers and wait for them to submit their prices.
      </div>
    );
  }

  // Find cheapest supplier per row
  const cheapest = (prices) => {
    const valid = Object.entries(prices).filter(([, v]) => v != null);
    if (valid.length === 0) return null;
    return valid.reduce((a, b) => (Number(a[1]) <= Number(b[1]) ? a : b))[0];
  };

  return (
    <div className="card overflow-x-auto">
      <div className="px-4 py-3 border-b border-gray-100 flex items-center gap-2">
        <BarChart2 size={15} className="text-green-600" />
        <h2 className="text-sm font-semibold text-gray-800">Price Comparison</h2>
        <span className="text-xs text-gray-400 ml-auto">{suppliers.length} supplier{suppliers.length !== 1 ? "s" : ""} responded</span>
      </div>
      <table className="w-full text-sm min-w-[500px]">
        <thead className="bg-gray-50 text-xs text-gray-500 uppercase tracking-wide text-left">
          <tr>
            <th className="px-4 py-3 min-w-[180px]">Item</th>
            <th className="px-4 py-3 text-center">Qty</th>
            {suppliers.map((s) => (
              <th key={s} className="px-4 py-3 text-right">{s}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {rows.map((row, idx) => {
            const best = cheapest(row.prices);
            return (
              <tr key={idx} className="hover:bg-gray-50">
                <td className="px-4 py-2.5 font-medium text-gray-800">
                  {row.description}
                  {row.unit && <span className="text-xs text-gray-400 ml-1">({row.unit})</span>}
                </td>
                <td className="px-4 py-2.5 text-center text-gray-500">
                  {row.requested_qty != null ? Number(row.requested_qty).toLocaleString() : "—"}
                </td>
                {suppliers.map((s) => {
                  const price = row.prices[s];
                  const isBest = s === best && suppliers.length > 1;
                  return (
                    <td key={s} className={`px-4 py-2.5 text-right font-medium ${
                      price == null ? "text-gray-300" :
                      isBest ? "text-emerald-700 bg-emerald-50" : "text-gray-700"
                    }`}>
                      {price == null ? "—" : (
                        <span>
                          {ksh(price)}
                          {isBest && <span className="ml-1 text-[10px] bg-emerald-200 text-emerald-800 px-1 py-0.5 rounded">Best</span>}
                        </span>
                      )}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
        <tfoot className="border-t-2 border-gray-200 bg-gray-50">
          <tr>
            <td className="px-4 py-3 font-bold text-gray-700" colSpan={2}>Estimated Total</td>
            {suppliers.map((s) => {
              const total = totals[s];
              const bestTotal = Object.values(totals).filter(Boolean).length > 1 &&
                total != null &&
                total === Math.min(...Object.values(totals).filter(Boolean).map(Number));
              return (
                <td key={s} className={`px-4 py-3 text-right font-bold text-base ${
                  total == null ? "text-gray-300" :
                  bestTotal ? "text-emerald-700" : "text-gray-800"
                }`}>
                  {total == null ? "—" : ksh(total)}
                  {bestTotal && <span className="ml-1 text-[10px] bg-emerald-200 text-emerald-800 px-1 py-0.5 rounded align-middle">Cheapest</span>}
                </td>
              );
            })}
          </tr>
        </tfoot>
      </table>
    </div>
  );
}

export default function SupplierRequestDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [request, setRequest] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [allSuppliers, setAllSuppliers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddSupplier, setShowAddSupplier] = useState(false);
  const [selectedSupplierId, setSelectedSupplierId] = useState("");
  const [addingSupplier, setAddingSupplier] = useState(false);
  const [addError, setAddError] = useState("");
  const [removeTarget, setRemoveTarget] = useState(null);
  const [copied, setCopied] = useState({});
  const [closeConfirm, setCloseConfirm] = useState(false);
  const [activeTab, setActiveTab] = useState("overview"); // overview | comparison

  const load = async () => {
    setLoading(true);
    const [reqRes, supRes] = await Promise.all([
      getSupplierRequest(id),
      getSuppliers(),
    ]);
    setRequest(reqRes.data.data);
    setAllSuppliers(supRes.data);

    // Load comparison if there are any responded invites
    const responded = reqRes.data.data.invites.filter((i) => i.status === "responded");
    if (responded.length > 0) {
      try {
        const cmpRes = await getComparison(id);
        setComparison(cmpRes.data);
      } catch {}
    }
    setLoading(false);
  };

  useEffect(() => { load(); }, [id]);

  const handleCopyLink = (invite) => {
    const url = invite.portal_url;
    navigator.clipboard.writeText(url).then(() => {
      setCopied((p) => ({ ...p, [invite.id]: true }));
      setTimeout(() => setCopied((p) => ({ ...p, [invite.id]: false })), 2000);
    });
  };

  const handleWhatsApp = (invite) => {
    const url = invite.portal_url;
    const msg = [
      `Hello ${invite.supplier_name},`,
      ``,
      `I would like you to provide your prices for the following items: *${request.title}*`,
      ``,
      `Please click the link below to view the items and submit your prices:`,
      `${url}`,
      ``,
      `Thank you.`,
    ].join("\n");
    window.open(`https://wa.me/${invite.supplier_company ?? ""}?text=${encodeURIComponent(msg)}`, "_blank");
  };

  const handleAddSupplier = async () => {
    if (!selectedSupplierId) return;
    setAddingSupplier(true);
    setAddError("");
    try {
      await addInvite(id, selectedSupplierId);
      setShowAddSupplier(false);
      setSelectedSupplierId("");
      load();
    } catch (err) {
      setAddError(err.response?.data?.detail ?? "Failed to add supplier");
    } finally {
      setAddingSupplier(false);
    }
  };

  const handleRemoveInvite = async () => {
    await removeInvite(id, removeTarget.id);
    setRemoveTarget(null);
    load();
  };

  const handleClose = async () => {
    await closeSupplierRequest(id);
    setCloseConfirm(false);
    load();
  };

  if (loading) return <div className="flex h-96 items-center justify-center"><Spinner size="lg" /></div>;
  if (!request) return null;

  const respondedCount = request.invites.filter((i) => i.status === "responded").length;
  const uninvitedSuppliers = allSuppliers.filter((s) => !request.invites.some((inv) => inv.supplier_id === s.id));

  return (
    <div className="p-4 md:p-6 max-w-4xl mx-auto space-y-5">
      {/* Header */}
      <div className="flex items-start gap-3 flex-wrap">
        <button onClick={() => navigate("/suppliers")} className="mt-1 text-gray-400 hover:text-gray-600"><ArrowLeft size={20} /></button>
        <div className="flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-xl font-bold text-gray-900">{request.title}</h1>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium capitalize ${
              request.status === "open" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"
            }`}>{request.status}</span>
          </div>
          <p className="text-sm text-gray-400 mt-0.5">
            {request.items.length} item{request.items.length !== 1 ? "s" : ""} · {respondedCount} of {request.invites.length} supplier{request.invites.length !== 1 ? "s" : ""} responded
          </p>
          {request.notes && <p className="text-sm text-gray-500 mt-1">{request.notes}</p>}
        </div>
        {request.status === "open" && (
          <div className="flex gap-2 flex-wrap">
            <button className="btn-secondary text-sm" onClick={() => setShowAddSupplier(true)}>
              <Users size={14} /> Add Supplier
            </button>
            <button className="btn-secondary text-sm text-amber-600 border-amber-200 hover:bg-amber-50" onClick={() => setCloseConfirm(true)}>
              <Lock size={14} /> Close Request
            </button>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200">
        {[
          { key: "overview", label: "Overview & Links" },
          { key: "comparison", label: `Comparison${respondedCount > 0 ? ` (${respondedCount})` : ""}` },
        ].map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              activeTab === key ? "border-green-600 text-green-700" : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {activeTab === "overview" && (
        <>
          {/* Items requested */}
          <div className="card overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-100">
              <h2 className="text-sm font-semibold text-gray-800">Items Requested</h2>
            </div>
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500 uppercase tracking-wide text-left">
                <tr>
                  <th className="px-4 py-2">Description</th>
                  <th className="px-4 py-2 text-right">Quantity</th>
                  <th className="px-4 py-2">Unit</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {request.items.map((item) => (
                  <tr key={item.id}>
                    <td className="px-4 py-2.5 font-medium text-gray-800">{item.description}</td>
                    <td className="px-4 py-2.5 text-right text-gray-600">{item.quantity != null ? Number(item.quantity).toLocaleString() : "—"}</td>
                    <td className="px-4 py-2.5 text-gray-500">{item.unit || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Supplier invites */}
          <div className="card overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-gray-800">Supplier Links</h2>
              {request.status === "open" && (
                <button className="btn-secondary text-xs py-1.5 px-3" onClick={() => setShowAddSupplier(true)}>
                  <Plus size={12} /> Add Supplier
                </button>
              )}
            </div>

            {request.invites.length === 0 ? (
              <div className="px-4 py-8 text-center text-sm text-gray-400">
                No suppliers added yet. Add a supplier to generate a shareable link.
              </div>
            ) : (
              <div className="divide-y divide-gray-100">
                {request.invites.map((invite) => (
                  <div key={invite.id} className="px-4 py-4 space-y-3">
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <div className="flex items-center gap-3">
                        <div className="h-9 w-9 rounded-full bg-purple-100 flex items-center justify-center shrink-0">
                          <span className="text-sm font-bold text-purple-700">{invite.supplier_name[0].toUpperCase()}</span>
                        </div>
                        <div>
                          <p className="font-medium text-gray-900">{invite.supplier_name}</p>
                          {invite.supplier_company && <p className="text-xs text-gray-400">{invite.supplier_company}</p>}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <StatusBadge status={invite.status} />
                        {request.status === "open" && invite.status === "pending" && (
                          <button onClick={() => setRemoveTarget(invite)} className="p-1 text-gray-300 hover:text-red-500">
                            <Trash2 size={13} />
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Portal link row */}
                    <div className="flex gap-2 items-center">
                      <input
                        readOnly
                        value={invite.portal_url}
                        className="input flex-1 text-xs font-mono bg-gray-50 text-gray-500"
                        onFocus={(e) => e.target.select()}
                      />
                      <button
                        onClick={() => handleCopyLink(invite)}
                        className="px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-50 shrink-0"
                        title="Copy link"
                      >
                        {copied[invite.id] ? <CheckCircle size={15} className="text-green-500" /> : <Copy size={15} />}
                      </button>
                      <button
                        onClick={() => handleWhatsApp(invite)}
                        className="px-3 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm shrink-0 flex items-center gap-1.5"
                        title="Send via WhatsApp"
                      >
                        <MessageCircle size={15} /> WhatsApp
                      </button>
                    </div>

                    {/* Submitted response preview */}
                    {invite.status === "responded" && invite.response_items.length > 0 && (
                      <div className="bg-green-50 rounded-lg p-3 space-y-1">
                        <p className="text-xs font-semibold text-green-700 mb-2">
                          Submitted {invite.submitted_at ? new Date(invite.submitted_at).toLocaleDateString("en-KE", { day: "2-digit", month: "short", year: "numeric" }) : ""}
                          {invite.supplier_notes && <span className="text-gray-500 font-normal ml-2">— "{invite.supplier_notes}"</span>}
                        </p>
                        {invite.response_items.map((r) => (
                          <div key={r.id} className="flex justify-between text-sm text-gray-700">
                            <span>{r.description} {r.quantity ? `× ${r.quantity}` : ""} {r.unit || ""}</span>
                            <span className="font-semibold text-green-800">{ksh(r.unit_price)}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}

      {activeTab === "comparison" && (
        respondedCount === 0 ? (
          <div className="card p-10 text-center space-y-2">
            <BarChart2 size={32} className="mx-auto text-gray-300" />
            <p className="text-sm text-gray-500 font-medium">No responses yet</p>
            <p className="text-xs text-gray-400">Share the portal links with your suppliers. Once they submit their prices, the comparison table will appear here.</p>
            <button className="btn-secondary text-sm mt-2" onClick={() => setActiveTab("overview")}>Go to Links</button>
          </div>
        ) : comparison ? (
          <ComparisonTable comparison={comparison} />
        ) : (
          <div className="flex h-48 items-center justify-center"><Spinner size="lg" /></div>
        )
      )}

      {/* Add supplier modal */}
      <Modal open={showAddSupplier} onClose={() => { setShowAddSupplier(false); setAddError(""); }} title="Add Supplier to Request" size="sm">
        <div className="space-y-4">
          {addError && <div className="bg-red-50 text-red-700 text-sm px-3 py-2 rounded-lg">{addError}</div>}
          {uninvitedSuppliers.length === 0 ? (
            <p className="text-sm text-gray-500">All your suppliers have already been added to this request.</p>
          ) : (
            <>
              <div>
                <label className="label">Select Supplier</label>
                <select className="input" value={selectedSupplierId} onChange={(e) => setSelectedSupplierId(e.target.value)}>
                  <option value="">Choose a supplier…</option>
                  {uninvitedSuppliers.map((s) => (
                    <option key={s.id} value={s.id}>{s.name}{s.company_name ? ` — ${s.company_name}` : ""}</option>
                  ))}
                </select>
              </div>
              <p className="text-xs text-gray-400">A unique portal link will be generated for this supplier. Share it with them via WhatsApp or copy it.</p>
              <div className="flex gap-2 justify-end pt-1">
                <button className="btn-secondary" onClick={() => { setShowAddSupplier(false); setAddError(""); }}>Cancel</button>
                <button className="btn-primary" onClick={handleAddSupplier} disabled={!selectedSupplierId || addingSupplier}>
                  {addingSupplier ? "Adding…" : "Add & Generate Link"}
                </button>
              </div>
            </>
          )}
        </div>
      </Modal>

      <ConfirmDialog
        open={!!removeTarget}
        onClose={() => setRemoveTarget(null)}
        onConfirm={handleRemoveInvite}
        title="Remove Supplier"
        message={`Remove ${removeTarget?.supplier_name} from this request? Their link will stop working.`}
        danger
      />

      <ConfirmDialog
        open={closeConfirm}
        onClose={() => setCloseConfirm(false)}
        onConfirm={handleClose}
        title="Close Price Request"
        message="Close this request? You can still view all submitted prices but no new responses will be accepted."
        danger={false}
      />
    </div>
  );
}
