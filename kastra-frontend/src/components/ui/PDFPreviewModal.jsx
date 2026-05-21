import { X, Printer, Download } from "lucide-react";

export default function PDFPreviewModal({ open, onClose, title, children }) {
  if (!open) return null;

  return (
    <>
      {/* Print-only CSS injected while modal is mounted */}
      <style>{`
        @media print {
          @page { margin: 0; size: A4 portrait; }
          body * { visibility: hidden !important; }
          #kastra-pdf-doc, #kastra-pdf-doc * {
            visibility: visible !important;
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
          }
          #kastra-pdf-doc {
            position: fixed !important;
            inset: 0 !important;
            width: 100% !important;
            z-index: 99999 !important;
            box-shadow: none !important;
            padding: 0 !important;
            margin: 0 !important;
          }
        }
      `}</style>

      <div className="fixed inset-0 z-50 flex flex-col" role="dialog" aria-modal="true" aria-label={title}>
        {/* Backdrop */}
        <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />

        {/* Modal shell */}
        <div className="relative flex flex-col w-full h-full max-w-3xl mx-auto my-4 md:my-8 bg-gray-100 rounded-xl shadow-2xl overflow-hidden">

          {/* Toolbar */}
          <div className="flex items-center justify-between px-5 py-3 bg-white border-b border-gray-200 shrink-0">
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 rounded-lg bg-green-50 flex items-center justify-center">
                <Download size={15} className="text-green-600" />
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-900">{title}</p>
                <p className="text-xs text-gray-400">Preview document before saving</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => window.print()}
                className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 transition-colors focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
              >
                <Printer size={15} />
                Print / Save PDF
              </button>
              <button
                onClick={onClose}
                className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                aria-label="Close"
              >
                <X size={18} />
              </button>
            </div>
          </div>

          {/* Document preview area — scrollable */}
          <div className="flex-1 overflow-y-auto py-6 px-4">
            <div
              id="kastra-pdf-doc"
              className="rounded-lg shadow-[0_2px_24px_rgba(0,0,0,0.12)] overflow-hidden"
            >
              {children}
            </div>
          </div>

          {/* Footer hint */}
          <div className="shrink-0 px-5 py-2.5 bg-white border-t border-gray-200 flex items-center justify-between">
            <p className="text-xs text-gray-400">
              Use <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-gray-600 font-mono text-[10px]">Ctrl+P</kbd> or click <strong>Print / Save PDF</strong> to download as PDF
            </p>
            <button onClick={onClose} className="text-xs text-gray-400 hover:text-gray-600 transition-colors">
              Close
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
