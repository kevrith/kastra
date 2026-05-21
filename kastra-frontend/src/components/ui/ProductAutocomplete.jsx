import { useEffect, useRef, useState } from "react";
import { getProducts } from "../../api/products";

/**
 * A description input that shows a product dropdown when the user types.
 * When a product is selected, it calls onSelect({ description, unit_price }).
 */
export default function ProductAutocomplete({ value, onChange, onSelect, placeholder }) {
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
        const { data } = await getProducts(value);
        setSuggestions(data);
        setOpen(data.length > 0);
      } catch {
        setSuggestions([]);
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [value]);

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const pick = (product) => {
    onSelect({ description: product.name, unit_price: product.unit_price });
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
          {suggestions.map((p) => (
            <li
              key={p.id}
              onMouseDown={() => pick(p)}
              className="px-3 py-2 cursor-pointer hover:bg-green-50 flex items-center justify-between gap-2"
            >
              <span className="text-gray-800">{p.name}</span>
              <span className="text-xs text-gray-400 shrink-0">KSh {Number(p.unit_price).toLocaleString("en-KE", { minimumFractionDigits: 2 })}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
