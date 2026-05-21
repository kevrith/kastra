import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { register as apiRegister, me } from "../../api/auth";
import { useAuth } from "../../context/AuthContext";
import { Eye, EyeOff } from "lucide-react";

export default function Register() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ business_name: "", display_name: "", email: "", password: "" });
  const [showPassword, setShowPassword] = useState(false);
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!consent) { setError("You must agree to the Privacy Policy and Terms of Service to create an account."); return; }
    setError("");
    setLoading(true);
    try {
      const { data } = await apiRegister(form.email, form.password, form.display_name, form.business_name, true);
      localStorage.setItem("access_token", data.access_token);
      const { data: userData } = await me();
      login(data.access_token, userData);
      navigate("/");
    } catch (err) {
      localStorage.removeItem("access_token");
      setError(err.response?.data?.detail ?? "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-green-600">Kastra</h1>
          <p className="text-gray-500 text-sm mt-1">Create your account</p>
        </div>
        <div className="card p-6 space-y-4">
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
                Kastra processes your data in compliance with the Kenya Data Protection Act 2019.
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
    </div>
  );
}
