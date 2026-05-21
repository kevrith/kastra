import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { register as apiRegister, me } from "../../api/auth";
import { useAuth } from "../../context/AuthContext";
import { Eye, EyeOff, Check } from "lucide-react";

const PLANS = [
  {
    id: "free",
    name: "Free",
    price: "KES 0",
    period: "forever",
    highlights: ["20 invoices/mo", "20 quotations/mo", "1 user", "5 OCR scans/mo"],
  },
  {
    id: "starter",
    name: "Starter",
    price: "KES 1,500",
    period: "/month",
    highlights: ["200 invoices/mo", "150 quotations/mo", "3 users", "10 OCR scans/mo"],
    popular: false,
  },
  {
    id: "business",
    name: "Business",
    price: "KES 3,000",
    period: "/month",
    highlights: ["400 invoices/mo", "250 quotations/mo", "6 users", "35 OCR scans/mo"],
    popular: true,
  },
  {
    id: "premium",
    name: "Premium",
    price: "KES 5,500",
    period: "/month",
    highlights: ["Unlimited invoices", "Unlimited quotations", "15 users", "100 OCR scans/mo"],
  },
];

export default function Register() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const defaultPlan = searchParams.get("plan") || "free";

  const [step, setStep] = useState(1);
  const [selectedPlan, setSelectedPlan] = useState(defaultPlan);
  const [form, setForm] = useState({ business_name: "", display_name: "", email: "", password: "" });
  const [showPassword, setShowPassword] = useState(false);
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!consent) { setError("You must agree to the Privacy Policy and Terms of Service."); return; }
    setError("");
    setLoading(true);
    try {
      const { data } = await apiRegister(form.email, form.password, form.display_name, form.business_name, true, selectedPlan);
      localStorage.setItem("access_token", data.access_token);
      const { data: userData } = await me();
      login(data.access_token, userData);
      navigate("/dashboard");
    } catch (err) {
      localStorage.removeItem("access_token");
      setError(err.response?.data?.detail ?? "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-8">
      <div className="text-center mb-6">
        <img src="/kastra.png" alt="Kastra" className="h-14 w-14 object-contain mx-auto mb-2" />
        <h1 className="text-2xl font-bold text-green-600">Kastra</h1>
        <p className="text-gray-500 text-sm">Create your account — it's free to start</p>
      </div>

      {/* Step indicator */}
      <div className="flex items-center justify-center gap-3 mb-6">
        <div className={`flex items-center gap-1.5 text-sm font-medium ${step === 1 ? "text-green-600" : "text-gray-400"}`}>
          <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs border-2 ${step === 1 ? "border-green-600 bg-green-600 text-white" : "border-gray-300"}`}>1</span>
          Choose Plan
        </div>
        <div className="h-px w-8 bg-gray-300" />
        <div className={`flex items-center gap-1.5 text-sm font-medium ${step === 2 ? "text-green-600" : "text-gray-400"}`}>
          <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs border-2 ${step === 2 ? "border-green-600 bg-green-600 text-white" : "border-gray-300"}`}>2</span>
          Your Details
        </div>
      </div>

      {step === 1 && (
        <div className="max-w-2xl mx-auto space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {PLANS.map((plan) => (
              <button
                key={plan.id}
                type="button"
                onClick={() => setSelectedPlan(plan.id)}
                className={`relative text-left rounded-xl border-2 p-4 transition-all ${
                  selectedPlan === plan.id
                    ? "border-green-500 bg-green-50"
                    : "border-gray-200 bg-white hover:border-green-300"
                }`}
              >
                {plan.popular && (
                  <span className="absolute -top-2.5 left-4 bg-green-600 text-white text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wide">
                    Most Popular
                  </span>
                )}
                {plan.id !== "free" && !plan.popular && (
                  <span className="absolute -top-2.5 left-4 bg-blue-600 text-white text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wide">
                    14-day free trial
                  </span>
                )}
                {plan.popular && (
                  <span className="absolute -top-2.5 right-4 bg-blue-600 text-white text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wide">
                    14-day free trial
                  </span>
                )}
                {selectedPlan === plan.id && (
                  <span className="absolute top-3 right-3 w-5 h-5 bg-green-600 rounded-full flex items-center justify-center">
                    <Check size={11} className="text-white" />
                  </span>
                )}
                <p className="font-bold text-gray-900">{plan.name}</p>
                <p className="text-lg font-extrabold text-green-600">{plan.price}<span className="text-xs text-gray-400 font-normal">{plan.period}</span></p>
                <ul className="mt-2 space-y-1">
                  {plan.highlights.map((h) => (
                    <li key={h} className="text-xs text-gray-600 flex items-center gap-1.5">
                      <Check size={10} className="text-green-500 flex-shrink-0" /> {h}
                    </li>
                  ))}
                </ul>
              </button>
            ))}
          </div>
          <button
            type="button"
            className="btn-primary w-full justify-center"
            onClick={() => setStep(2)}
          >
            Continue with {PLANS.find((p) => p.id === selectedPlan)?.name} plan →
          </button>
          <p className="text-center text-xs text-gray-500">
            Already have an account?{" "}
            <Link to="/login" className="text-green-600 hover:underline font-medium">Sign in</Link>
          </p>
        </div>
      )}

      {step === 2 && (
        <div className="max-w-sm mx-auto">
          <div className="card p-6 space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-sm text-gray-500">
                Selected: <span className="font-semibold text-green-600">{PLANS.find((p) => p.id === selectedPlan)?.name}</span>
              </p>
              <button type="button" onClick={() => setStep(1)} className="text-xs text-gray-400 hover:text-gray-600 underline">Change</button>
            </div>

            {error && <div className="bg-red-50 text-red-700 text-sm px-3 py-2 rounded-lg">{error}</div>}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="label">Business Name</label>
                <input className="input" placeholder="Acme Enterprises" value={form.business_name}
                  onChange={(e) => setForm({ ...form, business_name: e.target.value })} required />
              </div>
              <div>
                <label className="label">Your Full Name</label>
                <input className="input" placeholder="Jane Mwangi" value={form.display_name}
                  onChange={(e) => setForm({ ...form, display_name: e.target.value })} required />
              </div>
              <div>
                <label className="label">Email</label>
                <input className="input" type="email" placeholder="you@company.co.ke" value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })} required />
              </div>
              <div>
                <label className="label">Password</label>
                <div className="relative">
                  <input
                    className="input pr-10"
                    type={showPassword ? "text" : "password"}
                    placeholder="Min 8 characters"
                    value={form.password}
                    onChange={(e) => setForm({ ...form, password: e.target.value })}
                    required
                    minLength={8}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    tabIndex={-1}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <input
                  id="consent"
                  type="checkbox"
                  checked={consent}
                  onChange={(e) => setConsent(e.target.checked)}
                  className="mt-0.5 h-4 w-4 rounded border-gray-300 text-green-600 focus:ring-green-500"
                />
                <label htmlFor="consent" className="text-xs text-gray-600 leading-relaxed">
                  I agree to the{" "}
                  <Link to="/privacy" className="text-green-600 hover:underline" target="_blank">Privacy Policy</Link>
                  {" "}and{" "}
                  <Link to="/terms" className="text-green-600 hover:underline" target="_blank">Terms of Service</Link>.
                  Kastra processes data under the Kenya Data Protection Act 2019.
                </label>
              </div>
              <button className="btn-primary w-full justify-center" disabled={loading || !consent}>
                {loading ? "Creating account…" : "Create account"}
              </button>
            </form>
            <p className="text-center text-xs text-gray-500">
              Already have an account?{" "}
              <Link to="/login" className="text-green-600 hover:underline font-medium">Sign in</Link>
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
