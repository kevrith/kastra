import { NavLink, useNavigate } from "react-router-dom";
import {
  BarChart2, FileText, Home, LogOut, Settings, Users, Receipt,
  TrendingDown, RefreshCw, Package, Kanban, UserCog, FolderKanban, Truck,
  UserCheck, Wallet, ShieldCheck, HelpCircle, Lock, Download, Landmark,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import GlobalSearch from "../ui/GlobalSearch";
import NotificationBell from "../ui/NotificationBell";
import { hasFeature, SIDEBAR_FEATURE, UNLOCK_PLAN, PLAN_LABELS } from "../../utils/planFeatures";
import { usePWAInstall } from "../../hooks/usePWAInstall";

const links = [
  { to: "/dashboard", icon: Home, label: "Dashboard" },
  { to: "/quotations", icon: FileText, label: "Quotations", roles: ["admin", "manager", "viewer"] },
  { to: "/quotations/pipeline", icon: Kanban, label: "Pipeline", roles: ["admin", "manager", "viewer"] },
  { to: "/projects", icon: FolderKanban, label: "Projects" },
  { to: "/invoices", icon: Receipt, label: "Invoices", roles: ["admin", "manager", "viewer"] },
  { to: "/reconciliation", icon: Landmark, label: "Reconcile", roles: ["admin", "manager"] },
  { to: "/clients", icon: Users, label: "Clients", roles: ["admin", "manager", "viewer"] },
  { to: "/products", icon: Package, label: "Products", roles: ["admin", "manager"] },
  { to: "/suppliers", icon: Truck, label: "Suppliers", roles: ["admin", "manager"] },
  { to: "/employees", icon: UserCheck, label: "Employees", roles: ["admin", "manager"] },
  { to: "/payroll", icon: Wallet, label: "Payroll", roles: ["admin", "manager"] },
  { to: "/expenses", icon: TrendingDown, label: "Expenses", roles: ["admin", "manager"] },
  { to: "/recurring", icon: RefreshCw, label: "Recurring", roles: ["admin", "manager"] },
  { to: "/reports", icon: BarChart2, label: "Reports", roles: ["admin", "manager", "viewer"] },
  { to: "/team", icon: UserCog, label: "Team", adminOnly: true },
  { to: "/audit-log", icon: ShieldCheck, label: "Audit Log", adminOnly: true },
  { to: "/settings", icon: Settings, label: "Settings", roles: ["admin", "manager"] },
];

export default function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { canInstall, promptInstall } = usePWAInstall();

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <aside className="hidden md:flex flex-col w-56 min-h-screen bg-white border-r border-gray-200">
      <div className="px-5 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <img src="/kastra1.png" alt="Kastra" className="h-8 w-8 object-contain" />
            <div>
              <span className="text-lg font-bold text-green-600 tracking-tight">Kastra</span>
              <p className="text-xs text-gray-400">Enterprise Management</p>
            </div>
          </div>
          <NotificationBell />
        </div>
        <GlobalSearch />
      </div>

      <nav className="flex-1 py-4 px-3 space-y-0.5">
        {links
          .filter(link => {
            if (link.adminOnly) return user?.role === 'admin';
            if (link.roles) return link.roles.includes(user?.role);
            return true;
          })
          .map(({ to, icon: Icon, label }) => {
            const featureKey = SIDEBAR_FEATURE[to];
            const plan = user?.organization?.plan ?? "free";
            const locked = featureKey ? !hasFeature(plan, featureKey) : false;
            const requiredPlan = locked ? PLAN_LABELS[UNLOCK_PLAN[featureKey]] : null;
            return (
              <NavLink
                key={to}
                to={to}
                end={to === "/dashboard"}
                title={locked ? `Requires ${requiredPlan} plan` : undefined}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-green-50 text-green-700"
                      : locked
                      ? "text-gray-400 hover:bg-gray-50 hover:text-gray-500"
                      : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                  }`
                }
              >
                <Icon size={17} />
                <span className="flex-1">{label}</span>
                {locked && (
                  <span className="flex items-center gap-1 text-[10px] font-semibold text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded-full">
                    <Lock size={9} /> {requiredPlan}
                  </span>
                )}
              </NavLink>
            );
          })}
      </nav>

      <div className="px-3 py-4 border-t border-gray-200">
        <div className="px-3 py-2 mb-1">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-gray-900 truncate">{user?.display_name}</p>
            <span className={`text-xs font-medium px-1.5 py-0.5 rounded capitalize ${
              user?.role === 'admin' ? 'bg-green-100 text-green-700' :
              user?.role === 'manager' ? 'bg-blue-100 text-blue-700' :
              user?.role === 'field_agent' ? 'bg-orange-100 text-orange-700' :
              'bg-gray-100 text-gray-600'
            }`}>{user?.role?.replace('_', ' ')}</span>
          </div>
          <p className="text-xs text-gray-400 truncate">{user?.email}</p>
          <p className="text-xs text-gray-300 truncate mt-0.5">{user?.organization?.name}</p>
        </div>
        <NavLink
          to="/help"
          className={({ isActive }) =>
            `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              isActive ? "bg-green-50 text-green-700" : "text-gray-500 hover:bg-gray-50 hover:text-gray-900"
            }`
          }
        >
          <HelpCircle size={17} />
          Help
        </NavLink>
        {canInstall && (
          <button
            onClick={promptInstall}
            className="flex items-center gap-3 px-3 py-2 w-full rounded-lg text-sm text-green-600 hover:bg-green-50 transition-colors font-medium"
          >
            <Download size={17} />
            Install App
          </button>
        )}
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-3 py-2 w-full rounded-lg text-sm text-gray-500 hover:bg-gray-50 hover:text-gray-900 transition-colors"
        >
          <LogOut size={17} />
          Sign out
        </button>
      </div>
    </aside>
  );
}
