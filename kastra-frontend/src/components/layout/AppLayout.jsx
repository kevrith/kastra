import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import Sidebar from "./Sidebar";
import BottomNav from "./BottomNav";
import Spinner from "../ui/Spinner";
import NotificationBell from "../ui/NotificationBell";
import GlobalSearch from "../ui/GlobalSearch";
import TrialBanner from "../ui/TrialBanner";

// Routes restricted to admin only
const ADMIN_ONLY = ["/team", "/settings"];
// Routes restricted to admin + manager
const MANAGER_PLUS = ["/reports", "/expenses", "/clients", "/quotations", "/invoices", "/products", "/recurring"];

function RoleGuard({ user }) {
  const { pathname } = useLocation();
  const isAdminOnly = ADMIN_ONLY.some(p => pathname.startsWith(p));
  const isManagerPlus = MANAGER_PLUS.some(p => pathname.startsWith(p));

  if (isAdminOnly && user.role !== 'admin')
    return <Navigate to="/dashboard" replace />;
  if (isManagerPlus && !['admin', 'manager'].includes(user.role))
    return <Navigate to="/dashboard" replace />;
  return <Outlet />;
}

export default function AppLayout() {
  const { user, loading } = useAuth();

  if (loading)
    return (
      <div className="flex h-screen items-center justify-center">
        <Spinner size="lg" />
      </div>
    );

  if (!user) return <Navigate to="/login" replace />;

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-auto">
        <TrialBanner />
        {/* Mobile-only top header */}
        <header className="md:hidden sticky top-0 z-30 bg-white border-b border-gray-200 px-4 py-2.5 flex items-center justify-between gap-3">
          <span className="text-base font-bold text-green-600 tracking-tight">Kastra</span>
          <div className="flex-1 max-w-xs">
            <GlobalSearch />
          </div>
          <NotificationBell />
        </header>
        <main className="flex-1 pb-16 md:pb-0">
          <RoleGuard user={user} />
        </main>
      </div>
      <BottomNav />
    </div>
  );
}
