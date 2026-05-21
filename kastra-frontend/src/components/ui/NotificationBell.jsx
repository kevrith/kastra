import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Bell, CheckCheck, CreditCard, FileText, RefreshCw, AlertCircle,
} from "lucide-react";
import { getNotifications, markRead, markAllRead } from "../../api/notifications";

const TYPE_META = {
  payment_received:   { icon: CreditCard, color: "bg-green-100 text-green-600",   dot: "bg-green-500" },
  quotation_accepted: { icon: FileText,   color: "bg-blue-100 text-blue-600",     dot: "bg-blue-500"  },
  quotation_declined: { icon: FileText,   color: "bg-red-100 text-red-500",       dot: "bg-red-500"   },
  recurring_invoice:  { icon: RefreshCw,  color: "bg-purple-100 text-purple-600", dot: "bg-purple-500"},
};
const DEFAULT_META = { icon: Bell, color: "bg-gray-100 text-gray-500", dot: "bg-gray-400" };

function timeAgo(iso) {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60)    return "just now";
  if (diff < 3600)  return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export default function NotificationBell() {
  const [data, setData]   = useState(null);
  const [open, setOpen]   = useState(false);
  const ref               = useRef(null);
  const navigate          = useNavigate();

  const load = async () => {
    try {
      const { data: d } = await getNotifications();
      setData(d);
    } catch { /* ignore */ }
  };

  useEffect(() => {
    load();
    const id = setInterval(load, 30000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleClick = async (notif) => {
    if (!notif.read_at) { await markRead(notif.id); load(); }
    setOpen(false);
    if (notif.entity_id) {
      if (notif.type === "payment_received") navigate(`/invoices/${notif.entity_id}`);
      else navigate(`/quotations/${notif.entity_id}`);
    }
  };

  const handleMarkAll = async () => { await markAllRead(); load(); };

  const unread = data?.unread_count ?? 0;
  const items  = data?.items ?? [];

  return (
    <div ref={ref} className="relative">
      {/* Bell button */}
      <button
        onClick={() => setOpen((o) => !o)}
        className={`relative p-2 rounded-lg transition-colors ${
          open ? "bg-green-50 text-green-600" : "text-gray-400 hover:text-gray-600 hover:bg-gray-100"
        }`}
        aria-label="Notifications"
      >
        <Bell size={18} />
        {unread > 0 && (
          <span className="absolute top-1 right-1 h-4 w-4 flex items-center justify-center bg-red-500 text-white text-[9px] font-bold rounded-full leading-none">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>

      {/* Panel — opens left-0 so it extends into the main content area, not off-screen */}
      {open && (
        <div className="absolute left-0 top-full mt-2 w-96 bg-white rounded-2xl shadow-2xl border border-gray-100 z-[200] flex flex-col overflow-hidden">

          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3.5 border-b border-gray-100 shrink-0">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-gray-900">Notifications</h3>
              {unread > 0 && (
                <span className="inline-flex items-center justify-center h-5 px-1.5 rounded-full bg-red-100 text-red-600 text-[10px] font-bold">
                  {unread} new
                </span>
              )}
            </div>
            {unread > 0 && (
              <button
                onClick={handleMarkAll}
                className="flex items-center gap-1 text-xs text-green-600 hover:text-green-700 font-medium"
              >
                <CheckCheck size={13} />
                Mark all read
              </button>
            )}
          </div>

          {/* List */}
          <div className="overflow-y-auto" style={{ maxHeight: 400 }}>
            {items.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center px-6">
                <div className="h-12 w-12 rounded-full bg-gray-100 flex items-center justify-center mb-3">
                  <Bell size={20} className="text-gray-300" />
                </div>
                <p className="text-sm font-medium text-gray-500">All caught up</p>
                <p className="text-xs text-gray-400 mt-1">No notifications yet.</p>
              </div>
            ) : (
              items.map((n) => {
                const meta = TYPE_META[n.type] ?? DEFAULT_META;
                const Icon = meta.icon;
                return (
                  <button
                    key={n.id}
                    onClick={() => handleClick(n)}
                    className={`w-full text-left px-4 py-3.5 hover:bg-gray-50 transition-colors flex items-start gap-3 border-b border-gray-50 last:border-0 ${
                      !n.read_at ? "bg-green-50/40" : ""
                    }`}
                  >
                    {/* Icon */}
                    <div className={`mt-0.5 h-8 w-8 rounded-xl flex items-center justify-center shrink-0 ${meta.color}`}>
                      <Icon size={14} />
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <p className={`text-sm leading-snug truncate ${
                        !n.read_at ? "font-semibold text-gray-900" : "font-medium text-gray-700"
                      }`}>
                        {n.title}
                      </p>
                      <p className="text-xs text-gray-500 mt-0.5 line-clamp-2 leading-relaxed">
                        {n.body}
                      </p>
                      <p className="text-[10px] text-gray-400 mt-1.5 font-medium">
                        {timeAgo(n.created_at)}
                      </p>
                    </div>

                    {/* Unread dot */}
                    {!n.read_at && (
                      <div className={`h-2 w-2 rounded-full mt-1.5 shrink-0 ${meta.dot}`} />
                    )}
                  </button>
                );
              })
            )}
          </div>

          {/* Footer */}
          {items.length > 0 && (
            <div className="shrink-0 px-4 py-2.5 border-t border-gray-100 bg-gray-50/60">
              <p className="text-[11px] text-gray-400 text-center">
                Showing {items.length} notification{items.length !== 1 ? "s" : ""}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
