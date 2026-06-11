import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { register as apiRegister, getGoogleAuthUrl, resendVerification } from "../../api/auth";
import { Eye, EyeOff, Check, Mail } from "lucide-react";

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
  const [searchParams] = useSearchParams();
  const defaultPlan = searchParams.get("plan") || "free";
  const referralCode = searchParams.get("ref") || localStorage.getItem("kastra_ref") || null;

  if (searchParams.get("ref")) localStorage.setItem("kastra_ref", searchParams.get("ref"));

  const [step, setStep] = useState(1);
  const [selectedPlan, setSelectedPlan] = useState(defaultPlan);
  const [form, setForm] = useState({ business_name: "", display_name: "", email: "", password: "" });
  const [showPassword, setShowPassword] = useState(false);
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [registered, setRegistered] = useState(false);
  const [resendStatus, setResendStatus] = useState("");

  const handleGoogle = async () => {
    try {
      const { data } = await getGoogleAuthUrl(selectedPlan);
      window.location.href = data.auth_url;
    } catch {
      setError("Could not initiate Google sign-up");
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!consent) { setError("You must agree to the Privacy Policy and Terms of Service."); return; }
    setError("");
    setLoading(true);
    try {
      await apiRegister(form.email, form.password, form.display_name, form.business_name, true, selectedPlan, referralCode);
      localStorage.removeItem("kastra_ref");
      setRegistered(true);
    } catch (err) {
      setError(err.response?.data?.detail ?? "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    setResendStatus("sending");
    try {
      await resendVerification(form.email);
      setResendStatus("sent");
    } catch {
      setResendStatus("error");
    }
  };

  if (registered) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="w-full max-w-sm text-center">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <Mail size={28} className="text-green-600" />
          </div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">Check your email</h2>
          <p className="text-gray-600 text-sm mb-1">
            We sent an activation link to
          </p>
          <p className="font-semibold text-gray-900 mb-5">{form.email}</p>
          <p className="text-gray-500 text-xs mb-6">
            Click the link in the email to activate your account. The link expires in 48 hours.
            Check your spam folder if you don't see it.
          </p>
          <button
            type="button"
            onClick={handleResend}
            disabled={resendStatus === "sending" || resendStatus === "sent"}
            className="btn-secondary w-full justify-center text-sm"
          >
            {resendStatus === "sending" ? "Sending…" : resendStatus === "sent" ? "Email sent ✓" : "Resend activation email"}
          </button>
          {resendStatus === "error" && (
            <p className="text-red-600 text-xs mt-2">Failed to resend. Please try again.</p>
          )}
          <p className="text-xs text-gray-400 mt-4">
            Wrong email?{" "}
            <button type="button" onClick={() => setRegistered(false)} className="text-green-600 hover:underline">Go back</button>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-8">
      <div className="text-center mb-6">
        <img src="/kastra1.png" alt="Kastra" className="h-14 w-14 object-contain mx-auto mb-2" />
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

          <div className="relative">
            <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-gray-200" /></div>
            <div className="relative flex justify-center text-xs text-gray-400 bg-gray-50 px-2">or sign up instantly</div>
          </div>

          <button type="button" onClick={handleGoogle} className="btn-secondary w-full justify-center gap-3">
            <svg className="h-4 w-4" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Sign up with Google ({PLANS.find((p) => p.id === selectedPlan)?.name})
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

            <div className="relative">
              <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-gray-200" /></div>
              <div className="relative flex justify-center text-xs text-gray-400 bg-white px-2">or</div>
            </div>

            <button type="button" onClick={handleGoogle} className="btn-secondary w-full justify-center gap-3">
              <svg className="h-4 w-4" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Continue with Google
            </button>

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
