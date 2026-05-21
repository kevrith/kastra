import { useState } from "react";
import { Link } from "react-router-dom";
import { forgotPassword } from "../../api/auth";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await forgotPassword(email);
      setSent(true);
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-green-600">Kastra</h1>
          <p className="text-gray-500 text-sm mt-1">Reset your password</p>
        </div>
        <div className="card p-6 space-y-4">
          {sent ? (
            <div className="text-center space-y-3">
              <div className="h-12 w-12 bg-green-100 rounded-full flex items-center justify-center mx-auto">
                <svg className="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <p className="font-medium text-gray-900">Check your email</p>
              <p className="text-sm text-gray-500">
                If <strong>{email}</strong> is registered, you'll receive a reset link shortly.
              </p>
              <Link to="/login" className="btn-primary w-full justify-center block text-center mt-4">
                Back to login
              </Link>
            </div>
          ) : (
            <>
              {error && <div className="bg-red-50 text-red-700 text-sm px-3 py-2 rounded-lg">{error}</div>}
              <p className="text-sm text-gray-600">
                Enter your email and we'll send you a link to reset your password.
              </p>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="label">Email</label>
                  <input className="input" type="email" placeholder="you@company.co.ke"
                    value={email} onChange={(e) => setEmail(e.target.value)} required />
                </div>
                <button className="btn-primary w-full justify-center" disabled={loading}>
                  {loading ? "Sending…" : "Send reset link"}
                </button>
              </form>
              <p className="text-center text-xs text-gray-500">
                <Link to="/login" className="text-green-600 hover:underline">Back to login</Link>
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
