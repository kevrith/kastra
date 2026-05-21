import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { me } from "../../api/auth";
import { useAuth } from "../../context/AuthContext";
import Spinner from "../../components/ui/Spinner";

export default function AuthCallback() {
  const [params] = useSearchParams();
  const { login } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const token = params.get("token");
    if (!token) { navigate("/login"); return; }
    localStorage.setItem("access_token", token);
    me().then(({ data }) => {
      login(token, data);
      navigate("/");
    }).catch(() => navigate("/login"));
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <Spinner size="lg" />
    </div>
  );
}
