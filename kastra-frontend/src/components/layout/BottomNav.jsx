import { useState, useEffect } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import {
  Home, FileText, Receipt, Users, Settings,
  TrendingDown, RefreshCw, BarChart2, Package, MoreHorizontal, X, Kanban,
  FolderKanban, UserCog, LogOut, Truck, UserCheck, Wallet, ShieldCheck, Lock, Download,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { hasFeature, SIDEBAR_FEATURE, UNLOCK_PLAN, PLAN_LABELS } from "../../utils/planFeatures";
import { usePWAInstall } from "../../hooks/usePWAInstall";

const PRIMARY = [
  { to: "/dashboard", icon: Home, label: "Home" },
  { to: "/quotations", icon: FileText, label: "Quotes", roles: ["admin", "manager", "viewer"] },
  { to: "/quotations/pipeline", icon: Kanban, label: "Pipeline", roles: ["admin", "manager", "viewer"] },
  { to: "/invoices", icon: Receipt, label: "Invoices", roles: ["admin", "manager", "viewer"] },
  { to: "/clients", icon: Users, label: "Clients", roles: ["admin", "manager", "viewer"] },
];

const DRAWER_LINKS = [
  { to: "/projects", icon: FolderKanban, label: "Projects" },
  { to: "/suppliers", icon: Truck, label: "Suppliers", roles: ["admin", "manager"] },
  { to: "/employees", icon: UserCheck, label: "Employees", roles: ["admin", "manager"] },
  { to: "/payroll", icon: Wallet, label: "Payroll", roles: ["admin", "manager"] },
  { to: "/expenses", icon: TrendingDown, label: "Expenses", roles: ["admin", "manager"] },
  { to: "/recurring", icon: RefreshCw, label: "Recurring", roles: ["admin", "manager"] },
  { to: "/reports", icon: BarChart2, label: "Reports", roles: ["admin", "manager", "viewer"] },
  { to: "/products", icon: Package, label: "Products", roles: ["admin", "manager"] },
  { to: "/team", icon: UserCog, label: "Team", adminOnly: true },
  { to: "/audit-log", icon: ShieldCheck, label: "Audit Log", adminOnly: true },
  { to: "/settings", icon: Settings, label: "Settings", roles: ["admin", "manager"] },
];

const NAV_H = 56; // px — keep in sync with the nav bar height below

function canSee(link, role) {
  if (link.adminOnly) return role === 'admin';
  if (link.roles) return link.roles.includes(role);
  return true;
}

export default function BottomNav() {
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  useEffect(() => { setOpen(false); }, [location.pathname]);

  const role = user?.role;
  const visibleDrawer = DRAWER_LINKS.filter(l => canSee(l, role));
  const { canInstall, promptInstall } = usePWAInstall();
  const isMoreActive = visibleDrawer.some((l) => location.pathname.startsWith(l.to));

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <>
      {/* Backdrop — closes drawer on tap */}
      {open && (
        <div
          className="md:hidden fixed inset-0 z-40 bg-black/40"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Slide-up drawer — sits above the backdrop, below the nav bar */}
      <div
        className={`md:hidden fixed left-0 right-0 z-50 bg-white shadow-2xl rounded-t-2xl transition-transform duration-300 ease-out`}
        style={{
          bottom: NAV_H,
          transform: open ? "translateY(0)" : "translateY(110%)",
        }}
      >
        {/* Drawer header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100">
          <span className="text-sm font-semibold text-gray-700">More</span>
          <button
            onClick={() => setOpen(false)}
            className="p-1 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100"
          >
            <X size={17} />
          </button>
        </div>

        {/* Nav items — simple list, always readable on any screen width */}
        <div className="px-3 py-2">
          {visibleDrawer.map(({ to, icon: Icon, label }) => {
            const featureKey = SIDEBAR_FEATURE[to];
            const plan = role ? (user?.organization?.plan ?? "free") : "free";
            const locked = featureKey ? !hasFeature(plan, featureKey) : false;
            const requiredPlan = locked ? PLAN_LABELS[UNLOCK_PLAN[featureKey]] : null;
            return (
              <NavLink
                key={to}
                to={to}
                onClick={() => setOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-green-50 text-green-700"
                      : locked
                      ? "text-gray-400 active:bg-gray-50"
                      : "text-gray-600 active:bg-gray-100"
                  }`
                }
              >
                <Icon size={20} />
                <span className="flex-1">{label}</span>
                {locked && (
                  <span className="flex items-center gap-1 text-[10px] font-semibold text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded-full">
                    <Lock size={9} /> {requiredPlan}
                  </span>
                )}
              </NavLink>
            );
          })}
          
          {/* User info & logout */}
          <div className="mt-3 pt-3 border-t border-gray-100">
            <div className="px-4 py-2 mb-2">
              <p className="text-xs font-medium text-gray-900 truncate">{user?.display_name}</p>
              <p className="text-xs text-gray-500 truncate">{user?.email}</p>
            </div>
            {canInstall && (
              <button
                onClick={promptInstall}
                className="flex items-center gap-3 px-4 py-3 w-full rounded-xl text-sm font-medium text-green-600 active:bg-green-50 transition-colors"
              >
                <Download size={20} />
                Install App
              </button>
            )}
            <button
              onClick={handleLogout}
              className="flex items-center gap-3 px-4 py-3 w-full rounded-xl text-sm font-medium text-red-600 active:bg-red-50 transition-colors"
            >
              <LogOut size={20} />
              Sign out
            </button>
          </div>
        </div>
        <div className="h-3" />
      </div>

      {/* Bottom tab bar — always on top, above the drawer */}
      <nav
        className="md:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 flex"
        style={{ height: NAV_H, zIndex: 60 }}
      >
        {PRIMARY.filter(l => canSee(l, role)).map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/dashboard"}
            className={({ isActive }) =>
              `flex-1 flex flex-col items-center justify-center text-xs font-medium transition-colors ${
                isActive ? "text-green-600" : "text-gray-500"
              }`
            }
          >
            <Icon size={20} className="mb-0.5" />
            {label}
          </NavLink>
        ))}

        {/* More button */}
        <button
          onClick={() => setOpen((v) => !v)}
          className={`flex-1 flex flex-col items-center justify-center text-xs font-medium transition-colors ${
            isMoreActive || open ? "text-green-600" : "text-gray-500"
          }`}
        >
          <MoreHorizontal size={20} className="mb-0.5" />
          More
        </button>
      </nav>
    </>
  );
}
