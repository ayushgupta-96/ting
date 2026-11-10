import React from 'react';
import { AlertCircle, CheckCircle2, X } from 'lucide-react';

export default function Toast({ toast, onClose }) {
  if (!toast) return null;

  const isError = toast.type === 'error';

  return (
    <div className="fixed top-4 inset-x-4 z-50 flex justify-center pointer-events-none animate-slide-up">
      <div
        className={`pointer-events-auto max-w-sm w-full rounded-2xl p-3.5 shadow-2xl flex items-center justify-between border ${
          isError
            ? 'bg-red-500 text-white border-red-600 shadow-red-500/25'
            : 'bg-emerald-600 text-white border-emerald-700 shadow-emerald-600/25'
        }`}
      >
        <div className="flex items-center space-x-2.5 min-w-0">
          {isError ? (
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
          ) : (
            <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
          )}
          <p className="text-xs font-bold leading-tight truncate">{toast.message}</p>
        </div>

        <button
          onClick={onClose}
          className="ml-2 p-1 rounded-lg hover:bg-white/20 transition-colors flex-shrink-0"
          aria-label="Close notification"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
