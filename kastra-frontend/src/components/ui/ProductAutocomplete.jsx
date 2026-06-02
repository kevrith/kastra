import { useEffect, useRef, useState } from "react";
import { getProducts } from "../../api/products";

export default function ProductAutocomplete({ value, onChange, onSelect, placeholder, clientId }) {
  const [suggestions, setSuggestions] = useState([]);
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!value || value.length < 1) {
      setSuggestions([]);
      setOpen(false);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const { data } = await getProducts(value, clientId);
        setSuggestions(data);
        setOpen(data.length > 0);
      } catch {
        setSuggestions([]);
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [value, clientId]);

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const pick = (product) => {
    // Use client-specific price if available, otherwise fall back to default
    const price = product.client_price ?? product.unit_price;
    onSelect({ description: product.name, unit_price: price, cost_price: product.cost_price ?? 0 });
    setOpen(false);
    setSuggestions([]);
  };

  return (
    <div ref={ref} className="relative">
      <input
        className="input"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onFocus={() => suggestions.length > 0 && setOpen(true)}
        placeholder={placeholder ?? "Description"}
      />
      {open && (
        <ul className="absolute z-50 mt-1 w-full bg-white border border-gray-200 rounded-xl shadow-lg max-h-52 overflow-auto text-sm">
          {suggestions.map((p) => {
            const displayPrice = p.client_price ?? p.unit_price;
            const isClientPrice = p.client_price != null;
            return (
              <li
                key={p.id}
                onMouseDown={() => pick(p)}
                className="px-3 py-2 cursor-pointer hover:bg-green-50 flex items-center justify-between gap-2"
              >
                <span className="text-gray-800">{p.name}</span>
                <div className="text-right shrink-0">
                  <span className={`text-xs ${isClientPrice ? "text-green-600 font-medium" : "text-gray-400"}`}>
                    KSh {Number(displayPrice).toLocaleString("en-KE", { minimumFractionDigits: 2 })}
                  </span>
                  {isClientPrice && (
                    <div className="text-[10px] text-green-500 leading-none">agreed rate</div>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
