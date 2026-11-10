import React from 'react';
import { AlertCircle } from 'lucide-react';

export default function ReplaceCartModal({
  isOpen,
  onClose,
  onConfirm,
  existingRestaurantName = 'another restaurant',
  newRestaurantName = 'this restaurant',
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 backdrop-blur-sm animate-fade-in p-0 sm:p-4">
      <div className="absolute inset-0" onClick={onClose} />
      <div className="relative w-full max-w-sm bg-white dark:bg-[#1E293B] rounded-t-3xl sm:rounded-3xl p-6 shadow-2xl border border-gray-100 dark:border-gray-800 z-10 animate-slide-up space-y-4">
        {/* Drag handle for mobile */}
        <div className="w-10 h-1 bg-gray-200 dark:bg-gray-700 rounded-full mx-auto sm:hidden -mt-2 mb-2" />

        <div className="w-12 h-12 rounded-2xl bg-amber-50 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400 mx-auto flex items-center justify-center">
          <AlertCircle className="w-6 h-6" />
        </div>

        <div className="text-center space-y-1.5">
          <h3 className="font-black text-base text-gray-900 dark:text-white">
            Replace cart items?
          </h3>
          <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
            Your cart contains dishes from <span className="font-extrabold text-gray-900 dark:text-white">"{existingRestaurantName}"</span>. Do you want to discard your previous selection and start a new cart from <span className="font-extrabold text-[#7C3AED] dark:text-purple-400">"{newRestaurantName}"</span>?
          </p>
        </div>

        <div className="grid grid-cols-2 gap-3 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="w-full py-3 rounded-2xl border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 font-extrabold text-xs hover:bg-gray-50 dark:hover:bg-gray-800 active:scale-95 transition-all"
          >
            NO, KEEP CART
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="w-full py-3 rounded-2xl bg-gradient-to-r from-[#9061F9] to-[#7E3AF2] hover:from-[#7E3AF2] hover:to-[#6C2BD9] text-white font-extrabold text-xs shadow-lg shadow-purple-500/25 active:scale-95 transition-all"
          >
            YES, START AFRESH
          </button>
        </div>
      </div>
    </div>
  );
}
