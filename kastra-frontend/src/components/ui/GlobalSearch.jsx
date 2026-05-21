import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, Users, Receipt, FileText } from "lucide-react";
import { globalSearch } from "../../api/search";

const TYPE_ICON = { client: Users, invoice: Receipt, quotation: FileText };
const TYPE_ROUTE = {
  client: (id) => `/clients/${id}`,
  invoice: (id) => `/invoices/${id}`,
  quotation: (id) => `/quotations/${id}`,
};
const TYPE_COLOR = { client: "text-blue-500", invoice: "text-red-500", quotation: "text-orange-500" };

export default function GlobalSearch() {
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const ref = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!q || q.trim().length < 2) {
      setResults([]);
      setOpen(false);
      return;
    }
    setLoading(true);
    const timer = setTimeout(async () => {
      try {
        const { data } = await globalSearch(q.trim());
        setResults(data);
        setOpen(true);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [q]);

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const go = (result) => {
    navigate(TYPE_ROUTE[result.type](result.id));
    setQ("");
    setOpen(false);
  };

  return (
    <div ref={ref} className="relative w-full max-w-xs">
      <div className="relative">
        <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onFocus={() => results.length > 0 && setOpen(true)}
          placeholder="Search clients, invoices…"
          className="w-full pl-8 pr-3 py-2 text-sm bg-gray-100 border border-transparent rounded-lg focus:bg-white focus:border-green-300 focus:ring-0 outline-none transition-colors"
        />
      </div>
      {open && results.length > 0 && (
        <ul className="absolute left-0 mt-1 w-full bg-white border border-gray-200 rounded-xl shadow-lg z-50 overflow-hidden text-sm">
          {results.map((r) => {
            const Icon = TYPE_ICON[r.type] ?? Search;
            return (
              <li key={`${r.type}-${r.id}`}>
                <button
                  onClick={() => go(r)}
                  className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-gray-50 text-left"
                >
                  <Icon size={14} className={TYPE_COLOR[r.type]} />
                  <div>
                    <p className="font-medium text-gray-900">{r.label}</p>
                    {r.sub && <p className="text-xs text-gray-400">{r.sub}</p>}
                  </div>
                  <span className="ml-auto text-xs text-gray-300 capitalize">{r.type}</span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
      {open && results.length === 0 && q.length >= 2 && !loading && (
        <div className="absolute left-0 mt-1 w-full bg-white border border-gray-200 rounded-xl shadow-lg z-50 px-3 py-3 text-sm text-gray-400 text-center">
          No results for "{q}"
        </div>
      )}
    </div>
  );
}
