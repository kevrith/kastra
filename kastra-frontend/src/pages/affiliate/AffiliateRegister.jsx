import { useState } from "react";
import { Link } from "react-router-dom";
import { affiliateRegister } from "../../api/affiliate";
import { Eye, EyeOff } from "lucide-react";

export default function AffiliateRegister() {
  const [form, setForm] = useState({ name: "", email: "", phone: "", password: "", payout_phone: "" });
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await affiliateRegister(form);
      setSuccess("Application submitted! We'll review and notify you within 24 hours.");
    } catch (err) {
      setError(err.response?.data?.detail ?? "Registration failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-md">
        <div className="text-center mb-6">
          <img src="/kastra1.png" alt="Kastra" className="h-12 w-12 object-contain mx-auto mb-2" />
          <h1 className="text-2xl font-bold text-green-600">Become a Kastra Partner</h1>
          <p className="text-gray-500 text-sm mt-1">Earn KSh commission for every paying client you refer</p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
          {success ? (
            <div className="text-center py-4 space-y-3">
              <div className="w-14 h-14 bg-green-100 rounded-full flex items-center justify-center mx-auto">
                <svg className="w-7 h-7 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <p className="font-semibold text-gray-800">Application Received!</p>
              <p className="text-sm text-gray-500">{success}</p>
              <Link to="/affiliate/login" className="inline-block mt-2 text-green-600 hover:underline text-sm font-medium">
                Go to login →
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && <div className="bg-red-50 text-red-700 text-sm px-3 py-2 rounded-lg">{error}</div>}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
                <input className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
                  placeholder="John Kamau" value={form.name} onChange={set("name")} required />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                <input className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
                  type="email" placeholder="you@example.com" value={form.email} onChange={set("email")} required />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Phone Number</label>
                <input className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
                  placeholder="0712 345 678" value={form.phone} onChange={set("phone")} required />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  M-Pesa Payout Number
                  <span className="text-gray-400 font-normal ml-1">(commissions sent here)</span>
                </label>
                <input className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
                  placeholder="0712 345 678" value={form.payout_phone} onChange={set("payout_phone")} required />
                <p className="text-xs text-gray-400 mt-1">
                  Payouts are sent via M-Pesa — please use a Safaricom number registered for M-Pesa.
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                <div className="relative">
                  <input
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
                    type={showPassword ? "text" : "password"}
                    placeholder="Min 8 characters"
                    value={form.password}
                    onChange={set("password")}
                    required
                    minLength={8}
                  />
                  <button type="button" onClick={() => setShowPassword(v => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-2.5 rounded-lg text-sm transition-colors disabled:opacity-60"
              >
                {loading ? "Submitting…" : "Apply as Partner"}
              </button>

              <p className="text-center text-xs text-gray-500">
                Already a partner?{" "}
                <Link to="/affiliate/login" className="text-green-600 hover:underline font-medium">Sign in</Link>
              </p>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
