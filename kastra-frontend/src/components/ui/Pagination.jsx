import { ChevronLeft, ChevronRight } from "lucide-react";

export default function Pagination({ meta, onPageChange }) {
  if (!meta || meta.pages <= 1) return null;
  return (
    <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200">
      <p className="text-sm text-gray-600">
        Showing {(meta.page - 1) * meta.limit + 1}–{Math.min(meta.page * meta.limit, meta.total)} of {meta.total}
      </p>
      <div className="flex gap-1">
        <button
          className="btn-secondary px-2 py-1"
          disabled={meta.page === 1}
          onClick={() => onPageChange(meta.page - 1)}
        >
          <ChevronLeft size={16} />
        </button>
        <button
          className="btn-secondary px-2 py-1"
          disabled={meta.page === meta.pages}
          onClick={() => onPageChange(meta.page + 1)}
        >
          <ChevronRight size={16} />
        </button>
      </div>
    </div>
  );
}
