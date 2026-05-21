import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { Zap, X } from "lucide-react";

export default function TrialBanner() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [dismissed, setDismissed] = useState(false);

  const org = user?.organization;
  const isTrialActive = org?.is_trial && org?.trial_ends_at;

  const daysLeft = isTrialActive
    ? Math.max(0, Math.ceil((new Date(org.trial_ends_at) - Date.now()) / 86400000))
    : null;

  // Reset dismissed state each day so the banner reappears
  useEffect(() => {
    const key = `trial_banner_dismissed_${new Date().toDateString()}`;
    if (sessionStorage.getItem(key)) setDismissed(true);
  }, []);

  const dismiss = () => {
    setDismissed(true);
    sessionStorage.setItem(`trial_banner_dismissed_${new Date().toDateString()}`, "1");
  };

  if (!isTrialActive || dismissed || daysLeft === null) return null;

  const urgent = daysLeft <= 3;
  const warning = daysLeft <= 7;

  return (
    <div className={`flex items-center gap-3 px-4 py-2.5 text-sm ${
      urgent
        ? "bg-red-600 text-white"
        : warning
        ? "bg-yellow-500 text-white"
        : "bg-green-600 text-white"
    }`}>
      <Zap size={15} className="flex-shrink-0" />
      <span className="flex-1">
        {daysLeft === 0
          ? `Your ${org.plan} trial ends today — upgrade now to keep your features.`
          : `Your ${org.plan} trial: ${daysLeft} day${daysLeft === 1 ? "" : "s"} remaining.`}
        {" "}
        <button
          onClick={() => navigate("/settings")}
          className="underline font-semibold hover:no-underline"
        >
          Upgrade now →
        </button>
      </span>
      <button onClick={dismiss} className="opacity-70 hover:opacity-100 flex-shrink-0">
        <X size={14} />
      </button>
    </div>
  );
}
