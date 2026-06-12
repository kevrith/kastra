import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { verifyEmail as apiVerifyEmail, me } from "../../api/auth";
import { CheckCircle, XCircle, Loader } from "lucide-react";

export default function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const { login } = useAuth();
  const navigate = useNavigate();
  const token = searchParams.get("token");

  const [status, setStatus] = useState("checking"); // checking | success | invalid | already

  useEffect(() => {
    if (!token) {
      setStatus("invalid");
      return;
    }
    (async () => {
      try {
        const { data } = await apiVerifyEmail(token);
        localStorage.setItem("access_token", data.access_token);
        const { data: userData } = await me();
        login(data.access_token, userData);
        setStatus("success");
        setTimeout(() => navigate("/dashboard"), 2500);
      } catch (err) {
        if (err.response?.data?.detail === "ALREADY_VERIFIED") {
          setStatus("already");
        } else {
          setStatus("invalid");
        }
      }
    })();
  }, [token, login, navigate]);

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="w-full max-w-sm text-center">
        <Link to="/" className="inline-block">
          <img src="/kastra1.png" alt="Kastra" className="h-12 w-12 object-contain mx-auto mb-6" />
        </Link>

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
