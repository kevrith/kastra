import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { login as apiLogin, getGoogleAuthUrl, me, resendVerification, twoFactorVerifyLogin } from "../../api/auth";
import { useAuth } from "../../context/AuthContext";
import { Eye, EyeOff } from "lucide-react";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [form, setForm] = useState({ email: "", password: "" });
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [unverified, setUnverified] = useState(false);
  const [resendStatus, setResendStatus] = useState("");
  // Set when the password checked out but a 2FA code is still owed.
  const [mfaToken, setMfaToken] = useState("");
  const [mfaCode, setMfaCode] = useState("");

  const alreadyVerified = searchParams.get("verified") === "already";

  const handleMfaSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { data } = await twoFactorVerifyLogin(mfaToken, mfaCode);
      localStorage.setItem("access_token", data.access_token);
      const { data: userData } = await me();
      login(data.access_token, userData);
      navigate("/dashboard");
    } catch (err) {
      localStorage.removeItem("access_token");
      setError(err.response?.data?.detail ?? "That code is not valid");
      setMfaCode("");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setUnverified(false);
    setResendStatus("");
    setLoading(true);
    try {
      const { data } = await apiLogin(form.email, form.password);
      if (data.mfa_required) {
        // Nothing is stored yet — this is not a session until the code passes.
        setMfaToken(data.mfa_token);
        return;
      }
      localStorage.setItem("access_token", data.access_token);
      const { data: userData } = await me();
      login(data.access_token, userData);
      navigate("/dashboard");
    } catch (err) {
      localStorage.removeItem("access_token");
      if (err.response?.data?.detail === "EMAIL_NOT_VERIFIED") {
        setUnverified(true);
      } else {
        setError(err.response?.data?.detail ?? "Login failed");
      }
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

  const handleGoogle = async () => {
    try {
      const { data } = await getGoogleAuthUrl();
      window.location.href = data.auth_url;
    } catch {
      setError("Could not initiate Google login");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <Link to="/" className="inline-block">
            <img src="/kastra1.png" alt="Kastra" className="h-16 w-16 object-contain mx-auto mb-3" />
            <h1 className="text-3xl font-bold text-green-600">Kastra</h1>
          </Link>
          <p className="text-gray-500 text-sm mt-1">Sign in to your account</p>
        </div>

        <div className="card p-6 space-y-4">
          {alreadyVerified && (
            <div className="bg-green-50 text-green-700 text-sm px-3 py-2 rounded-lg">
              Your email is already verified. Sign in below.
            </div>
          )}
          {error && (
            <div className="bg-red-50 text-red-700 text-sm px-3 py-2 rounded-lg">{error}</div>
          )}
          {unverified && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg px-3 py-3 space-y-2">
              <p className="text-amber-800 text-sm font-medium">Email not verified</p>
              <p className="text-amber-700 text-xs">
                Please check your inbox for the activation link we sent when you signed up.
              </p>
              <button
                type="button"
                onClick={handleResend}
                disabled={resendStatus === "sending" || resendStatus === "sent"}
                className="text-xs font-semibold text-amber-800 underline disabled:opacity-50"
              >
                {resendStatus === "sending" ? "Sending…" : resendStatus === "sent" ? "Sent ✓ — check your inbox" : "Resend activation email"}
              </button>
              {resendStatus === "error" && (
                <p className="text-red-600 text-xs">Failed to resend. Please try again.</p>
              )}
            </div>
          )}

          {mfaToken ? (
            <form onSubmit={handleMfaSubmit} className="space-y-4">
              <div>
                <label className="label">Authentication code</label>
                <input
                  className="input text-center text-xl tracking-[0.4em] font-mono"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  autoFocus
                  maxLength={14}
                  placeholder="000000"
                  value={mfaCode}
                  onChange={(e) => setMfaCode(e.target.value)}
                />
                <p className="text-xs text-gray-500 mt-1.5">
                  Open your authenticator app for the 6-digit code, or enter one of your
                  recovery codes.
                </p>
              </div>
              <button type="submit" className="btn-primary w-full" disabled={loading || !mfaCode}>
                {loading ? "Verifying…" : "Verify and sign in"}
              </button>
              <button
                type="button"
                className="text-xs text-gray-500 hover:text-gray-700 w-full text-center"
                onClick={() => { setMfaToken(""); setMfaCode(""); setError(""); }}
              >
                Back to sign in
              </button>
            </form>
          ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="label">Email</label>
              <input
                className="input"
                type="email"
                placeholder="you@company.co.ke"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                required
              />
            </div>
            <div>
              <label className="label">Password</label>
              <div className="relative">
                <input
                  className="input pr-10"
                  type={showPassword ? "text" : "password"}
                  placeholder="••••••••"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  required
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
            <div className="text-right">
              <Link to="/forgot-password" className="text-xs text-green-600 hover:underline">
                Forgot password?
              </Link>
            </div>
            <button className="btn-primary w-full justify-center" disabled={loading}>
              {loading ? "Signing in…" : "Sign in"}
            </button>
          </form>
          )}

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-200" />
            </div>
            <div className="relative flex justify-center text-xs text-gray-400 bg-white px-2">or</div>
          </div>

          <button onClick={handleGoogle} className="btn-secondary w-full justify-center gap-3">
            <svg className="h-4 w-4" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Continue with Google
          </button>

          <p className="text-center text-xs text-gray-500">
            Don't have an account?{" "}
            <Link to="/register" className="text-green-600 hover:underline font-medium">Sign up</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
