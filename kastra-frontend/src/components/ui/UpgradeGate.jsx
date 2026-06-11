import { Link } from "react-router-dom";
import { Lock, ArrowRight, Zap } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { hasFeature, UNLOCK_PLAN, PLAN_LABELS } from "../../utils/planFeatures";

const PLAN_COLOR = {
  starter:  { bg: "bg-blue-600",   ring: "ring-blue-200",  badge: "bg-blue-100 text-blue-700"  },
  business: { bg: "bg-purple-600", ring: "ring-purple-200", badge: "bg-purple-100 text-purple-700" },
  premium:  { bg: "bg-amber-500",  ring: "ring-amber-200",  badge: "bg-amber-100 text-amber-700"  },
};

/**
 * Wrap a page with this to show an upgrade prompt instead of the real content
 * when the user's plan doesn't include the feature.
 *
 * Usage:
 *   <UpgradeGate feature="recurring" title="Recurring Invoices" description="...">
 *     <ActualPageContent />
 *   </UpgradeGate>
 */
export default function UpgradeGate({ feature, title, description, bullets, children }) {
  const { user } = useAuth();
  const plan = user?.organization?.plan ?? "free";

  if (hasFeature(plan, feature)) {
    return children;
  }

  const required = UNLOCK_PLAN[feature] ?? "starter";
  const colors = PLAN_COLOR[required] ?? PLAN_COLOR.starter;
  const planLabel = PLAN_LABELS[required];

  return (
    <div className="flex items-center justify-center min-h-[60vh] px-4 py-10">
      <div className={`w-full max-w-md bg-white rounded-2xl border border-gray-200 shadow-sm ring-2 ${colors.ring} overflow-hidden`}>
        {/* Header strip */}
        <div className={`${colors.bg} px-6 py-4 flex items-center gap-3`}>
          <div className="w-9 h-9 rounded-xl bg-white/20 flex items-center justify-center">
            <Lock size={18} className="text-white" />
          </div>
          <div>
            <p className="text-white font-bold text-sm">{title}</p>
            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${colors.badge} mt-0.5 inline-block`}>
              {planLabel} plan &amp; above
            </span>
          </div>
        </div>

        {/* Body */}
        <div className="px-6 py-5">
          <p className="text-sm text-gray-600 leading-relaxed">{description}</p>

          {bullets?.length > 0 && (
            <ul className="mt-3 space-y-1.5">
              {bullets.map((b, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
                  <Zap size={13} className={`mt-0.5 shrink-0 ${required === "business" ? "text-purple-500" : required === "premium" ? "text-amber-500" : "text-blue-500"}`} />
                  {b}
                </li>
              ))}
            </ul>
          )}

          <div className="mt-5 flex items-center justify-between">
            <div>
              <p className="text-xs text-gray-400">Your current plan</p>
              <p className="text-sm font-semibold text-gray-800 capitalize">{plan}</p>
            </div>
            <Link
              to="/settings"
              className={`inline-flex items-center gap-2 ${colors.bg} text-white font-semibold px-4 py-2 rounded-xl text-sm hover:opacity-90 transition-opacity`}
            >
              Upgrade to {planLabel} <ArrowRight size={14} />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
