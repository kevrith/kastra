import { useState, useEffect } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import {
  Home, FileText, Receipt, Users, Settings,
  TrendingDown, RefreshCw, BarChart2, Package, MoreHorizontal, X, Kanban,
  FolderKanban, UserCog, LogOut,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";

const PRIMARY = [
  { to: "/dashboard", icon: Home, label: "Home" },
  { to: "/quotations", icon: FileText, label: "Quotes" },
  { to: "/quotations/pipeline", icon: Kanban, label: "Pipeline" },
  { to: "/invoices", icon: Receipt, label: "Invoices" },
  { to: "/clients", icon: Users, label: "Clients" },
];

const DRAWER_LINKS = [
  { to: "/projects", icon: FolderKanban, label: "Projects" },
  { to: "/expenses", icon: TrendingDown, label: "Expenses" },
  { to: "/recurring", icon: RefreshCw, label: "Recurring" },
  { to: "/reports", icon: BarChart2, label: "Reports" },
  { to: "/products", icon: Package, label: "Products" },
  { to: "/team", icon: UserCog, label: "Team", adminOnly: true },
  { to: "/settings", icon: Settings, label: "Settings" },
];

const NAV_H = 56; // px — keep in sync with the nav bar height below

export default function BottomNav() {
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  useEffect(() => { setOpen(false); }, [location.pathname]);

  const isMoreActive = DRAWER_LINKS.some((l) => location.pathname.startsWith(l.to));

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
          {DRAWER_LINKS
            .filter(link => !link.adminOnly || user?.role === 'admin')
            .map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-green-50 text-green-700"
                    : "text-gray-600 active:bg-gray-100"
                }`
              }
            >
              <Icon size={20} />
              {label}
            </NavLink>
          ))}
          
          {/* User info & logout */}
          <div className="mt-3 pt-3 border-t border-gray-100">
            <div className="px-4 py-2 mb-2">
              <p className="text-xs font-medium text-gray-900 truncate">{user?.display_name}</p>
              <p className="text-xs text-gray-500 truncate">{user?.email}</p>
            </div>
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
        {PRIMARY.map(({ to, icon: Icon, label }) => (
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
