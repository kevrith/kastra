import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { affiliateMe, affiliateReferrals, affiliateCommissions, affiliatePayouts, requestPayout } from "../../api/affiliate";
import { Copy, LogOut, DollarSign, Users, TrendingUp, Clock } from "lucide-react";

const BASE_URL = import.meta.env.VITE_PUBLIC_URL || window.location.origin;

function StatCard({ label, value, sub, icon: Icon, color }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">{label}</p>
          <p className={`text-2xl font-bold mt-1 ${color ?? "text-gray-900"}`}>{value}</p>
          {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
        </div>
        {Icon && <div className="p-2 bg-gray-50 rounded-lg"><Icon size={18} className="text-gray-400" /></div>}
      </div>
    </div>
  );
}

export default function AffiliateDashboard() {
  const navigate = useNavigate();
  const [me, setMe] = useState(null);
  const [referrals, setReferrals] = useState([]);
  const [commissions, setCommissions] = useState([]);
  const [payouts, setPayouts] = useState([]);
  const [tab, setTab] = useState("referrals");
  const [copied, setCopied] = useState(false);
  const [payoutAmount, setPayoutAmount] = useState("");
  const [payoutLoading, setPayoutLoading] = useState(false);
  const [payoutError, setPayoutError] = useState("");
  const [payoutSuccess, setPayoutSuccess] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("affiliate_token");
    if (!token) { navigate("/affiliate/login"); return; }
    load();
  }, []);

  const load = async () => {
    try {
      const [meRes, refRes, comRes, payRes] = await Promise.all([
        affiliateMe(), affiliateReferrals(), affiliateCommissions(), affiliatePayouts(),
      ]);
      setMe(meRes.data);
      setReferrals(refRes.data);
      setCommissions(comRes.data);
      setPayouts(payRes.data);
    } catch {
      localStorage.removeItem("affiliate_token");
      navigate("/affiliate/login");
    }
  };

  const copyLink = () => {
    const link = `${BASE_URL}/register?ref=${me.code}`;
    navigator.clipboard.writeText(link);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handlePayout = async (e) => {
    e.preventDefault();
    setPayoutError("");
    setPayoutSuccess("");
    const amount = parseFloat(payoutAmount);
    if (!amount || amount <= 0) { setPayoutError("Enter a valid amount"); return; }
    setPayoutLoading(true);
    try {
      await requestPayout(amount);
      setPayoutSuccess("Payout initiated! Funds will arrive on your M-Pesa shortly.");
      setPayoutAmount("");
      await load();
    } catch (err) {
      setPayoutError(err.response?.data?.detail ?? "Payout failed. Please try again.");
    } finally {
      setPayoutLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("affiliate_token");
    navigate("/affiliate/login");
  };

  if (!me) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600" />
      </div>
    );
  }

  const referralLink = `${BASE_URL}/register?ref=${me.code}`;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-4 py-3">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <img src="/kastra1.png" alt="Kastra" className="h-7 w-7 object-contain" />
            <span className="font-bold text-green-600">Partner Portal</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-500 hidden sm:block">{me.name}</span>
            <button onClick={handleLogout} className="text-gray-400 hover:text-gray-600 p-1">
              <LogOut size={17} />
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        {/* Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <StatCard label="Balance" value={`KSh ${me.balance_ksh.toFixed(0)}`} sub="Available" icon={DollarSign} color="text-green-600" />
          <StatCard label="Active Clients" value={me.active_referrals} sub="Paying subscribers" icon={Users} />
          <StatCard label="Total Earned" value={`KSh ${me.total_earned_ksh.toFixed(0)}`} sub="Lifetime" icon={TrendingUp} />
          <StatCard label="Commission" value={`KSh ${me.commission_rate_ksh}`} sub="Per client/month" icon={Clock} />
        </div>

        {/* Referral link */}
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <p className="text-sm font-semibold text-gray-700 mb-2">Your Referral Link</p>
          <div className="flex items-center gap-2">
            <input
              readOnly
              value={referralLink}
              className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-600 bg-gray-50 font-mono"
            />
            <button
              onClick={copyLink}
              className="flex items-center gap-1.5 px-3 py-2 bg-green-600 hover:bg-green-700 text-white text-sm rounded-lg font-medium transition-colors"
            >
              <Copy size={14} />
              {copied ? "Copied!" : "Copy"}
            </button>
          </div>
          <p className="text-xs text-gray-400 mt-2">
            Share this link. When someone registers and subscribes to a paid plan, you earn KSh {me.commission_rate_ksh}/month.
            Free and trial accounts do not generate commission.
          </p>
        </div>

        {/* Payout */}
        {me.balance_ksh > 0 && (
          <div className="bg-green-50 border border-green-200 rounded-xl p-4">
            <p className="text-sm font-semibold text-green-800 mb-3">
              Withdraw to M-Pesa ({me.payout_phone})
            </p>
            {payoutError && <div className="text-red-600 text-sm mb-2">{payoutError}</div>}
            {payoutSuccess && <div className="text-green-700 text-sm mb-2">{payoutSuccess}</div>}
            <form onSubmit={handlePayout} className="flex gap-2">
              <input
                type="number"
                min="1"
                max={me.balance_ksh}
                step="1"
                placeholder={`Max KSh ${me.balance_ksh.toFixed(0)}`}
                value={payoutAmount}
                onChange={(e) => setPayoutAmount(e.target.value)}
                className="flex-1 border border-green-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 bg-white"
              />
              <button
                type="submit"
                disabled={payoutLoading}
                className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-sm font-semibold rounded-lg transition-colors disabled:opacity-60"
              >
                {payoutLoading ? "…" : "Withdraw"}
              </button>
            </form>
          </div>
        )}

        {/* Tabs */}
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="flex border-b border-gray-100">
            {[
              { id: "referrals", label: `Referrals (${referrals.length})` },
              { id: "commissions", label: `Commissions (${commissions.length})` },
              { id: "payouts", label: `Payouts (${payouts.length})` },
            ].map((t) => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`flex-1 py-3 text-sm font-medium transition-colors ${
                  tab === t.id ? "text-green-600 border-b-2 border-green-600" : "text-gray-500 hover:text-gray-700"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          <div className="p-4">
            {tab === "referrals" && (
              referrals.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-6">No referrals yet. Share your link to get started.</p>
              ) : (
                <div className="space-y-2">
                  {referrals.map((r) => (
                    <div key={r.organization_id} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                      <div>
                        <p className="text-sm font-medium text-gray-800">{r.organization_name}</p>
                        <p className="text-xs text-gray-400">{new Date(r.joined_at).toLocaleDateString("en-KE")}</p>
                      </div>
                      <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                        r.is_paying ? "bg-green-100 text-green-700" :
                        r.is_trial ? "bg-blue-100 text-blue-700" :
                        "bg-gray-100 text-gray-500"
                      }`}>
                        {r.is_paying ? "Paying" : r.is_trial ? "Trial" : r.plan === "free" ? "Free" : r.plan}
                      </span>
                    </div>
                  ))}
                </div>
              )
            )}

            {tab === "commissions" && (
              commissions.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-6">No commissions yet. Commissions are credited on the 1st of each month.</p>
              ) : (
                <div className="space-y-2">
                  {commissions.map((c) => (
                    <div key={c.id} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                      <div>
                        <p className="text-sm font-medium text-gray-800">{c.organization_name}</p>
                        <p className="text-xs text-gray-400">{c.month}</p>
                      </div>
                      <span className="text-sm font-semibold text-green-600">+KSh {c.amount_ksh.toFixed(0)}</span>
                    </div>
                  ))}
                </div>
              )
            )}

            {tab === "payouts" && (
              payouts.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-6">No payouts yet.</p>
              ) : (
                <div className="space-y-2">
                  {payouts.map((p) => (
                    <div key={p.id} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                      <div>
                        <p className="text-sm font-medium text-gray-800">KSh {p.amount_ksh.toFixed(0)} → {p.payout_phone}</p>
                        <p className="text-xs text-gray-400">{new Date(p.requested_at).toLocaleDateString("en-KE")}</p>
                        {p.failure_reason && <p className="text-xs text-red-500">{p.failure_reason}</p>}
                      </div>
                      <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                        p.status === "completed" ? "bg-green-100 text-green-700" :
                        p.status === "processing" ? "bg-blue-100 text-blue-700" :
                        p.status === "failed" ? "bg-red-100 text-red-700" :
                        "bg-gray-100 text-gray-500"
                      }`}>
                        {p.status}
                      </span>
                    </div>
                  ))}
                </div>
              )
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
