import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { me } from "../../api/auth";
import { CheckCircle, XCircle, Loader } from "lucide-react";

export default function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const { login } = useAuth();
  const token = searchParams.get("token");
  const error = searchParams.get("error");

  const [status, setStatus] = useState("checking"); // checking | success | invalid | already

  useEffect(() => {
    if (error) {
      setStatus("invalid");
      return;
    }

    // The backend verify-email endpoint is a GET redirect — when the user
    // clicks the email link they are sent to the backend which then redirects
    // to /auth/callback?token=... (same as Google OAuth).
    // This page is only reached when something goes wrong (error param) or
    // when the backend redirects here with ?verified=already.
    const already = searchParams.get("verified");
    if (already === "already") {
      setStatus("already");
    }
  }, [error, searchParams]);

  // If there's a raw JWT token in the URL (from a redirect), log the user in
  useEffect(() => {
    if (!token) return;
    (async () => {
      try {
        localStorage.setItem("access_token", token);
        const { data: userData } = await me();
        login(token, userData);
        setStatus("success");
      } catch {
        localStorage.removeItem("access_token");
        setStatus("invalid");
      }
    })();
  }, [token, login]);

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="w-full max-w-sm text-center">
        <img src="/kastra1.png" alt="Kastra" className="h-12 w-12 object-contain mx-auto mb-6" />

        {status === "checking" && (
          <>
            <Loader size={40} className="text-green-500 mx-auto mb-4 animate-spin" />
            <p className="text-gray-600">Verifying your email…</p>
          </>
        )}

        {status === "success" && (
          <>
            <CheckCircle size={48} className="text-green-500 mx-auto mb-4" />
            <h2 className="text-xl font-bold text-gray-900 mb-2">Email verified!</h2>
            <p className="text-gray-600 text-sm mb-6">Your account is now active. Redirecting you to the dashboard…</p>
            <Link to="/dashboard" className="btn-primary w-full justify-center">Go to dashboard</Link>
          </>
        )}

        {status === "already" && (
          <>
            <CheckCircle size={48} className="text-green-400 mx-auto mb-4" />
            <h2 className="text-xl font-bold text-gray-900 mb-2">Already verified</h2>
            <p className="text-gray-600 text-sm mb-6">This email has already been verified. Sign in to continue.</p>
            <Link to="/login" className="btn-primary w-full justify-center">Sign in</Link>
          </>
        )}

        {status === "invalid" && (
          <>
            <XCircle size={48} className="text-red-500 mx-auto mb-4" />
            <h2 className="text-xl font-bold text-gray-900 mb-2">Link invalid or expired</h2>
            <p className="text-gray-600 text-sm mb-6">
              This activation link is no longer valid. Links expire after 48 hours.
              Sign in to request a new one.
            </p>
            <Link to="/login" className="btn-primary w-full justify-center">Back to sign in</Link>
          </>
        )}
      </div>
    </div>
  );
}
