import React, { useState } from 'react';
import { 
  Users, 
  X, 
  Search, 
  ShoppingCart, 
  Recycle, 
  Clock, 
  User, 
  Check, 
  Trash2 
} from 'lucide-react';

export default function SwitchAccountModal({
  isOpen,
  onClose,
  accounts = [],
  activeAccount = null,
  onSelectAccount,
  onToggleStatus,
  onDeleteAccount,
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [filter, setFilter] = useState('all'); // 'all' | 'fresh' | 'used'

  if (!isOpen) return null;

  const filteredAccounts = (accounts || []).filter((acc) => {
    const nameMatch = (acc.name || '').toLowerCase().includes(searchQuery.toLowerCase());
    const phoneMatch = (acc.phone || acc.mobile || '').includes(searchQuery);
    const matchesSearch = nameMatch || phoneMatch;

    const accStatus = (acc.status || 'fresh').toLowerCase();
    if (filter === 'fresh') return matchesSearch && accStatus === 'fresh';
    if (filter === 'used') return matchesSearch && accStatus === 'used';
    return matchesSearch;
  });

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 backdrop-blur-sm animate-fade-in">
      {/* Backdrop click to close */}
      <div className="absolute inset-0" onClick={onClose} />

      {/* Modal Sheet Container */}
      <div 
        className="relative w-full max-w-md bg-white dark:bg-[#1E293B] rounded-t-[28px] p-4 shadow-2xl border-t border-gray-100 dark:border-gray-800 z-10 max-h-[85vh] flex flex-col transition-colors animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Drag Handle */}
        <div className="w-12 h-1 bg-gray-300 dark:bg-gray-600 rounded-full mx-auto mb-3" />

        {/* Modal Header */}
        <div className="flex items-center justify-between pb-3 border-b border-gray-100 dark:border-gray-800/60">
          <div className="flex items-center space-x-2">
            <div className="w-7 h-7 rounded-lg bg-purple-100 dark:bg-purple-950/80 flex items-center justify-center text-[#7C3AED] dark:text-purple-300">
              <Users className="w-4 h-4" />
            </div>
            <h2 className="font-extrabold text-base text-gray-900 dark:text-white">
              Switch Account
            </h2>
          </div>

          <button
            onClick={onClose}
            className="w-7 h-7 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-white flex items-center justify-center transition-colors"
            aria-label="Close modal"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Search Bar */}
        <div className="relative mt-3">
          <Search className="w-4 h-4 absolute left-3.5 top-3 text-gray-400" />
          <input
            type="text"
            placeholder="Search account..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-gray-50 dark:bg-gray-800/70 border border-gray-200 dark:border-gray-700/80 rounded-2xl pl-10 pr-4 py-2.5 text-xs text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:border-purple-400 focus:ring-1 focus:ring-purple-400 transition-all"
          />
        </div>

        {/* Filter Chips */}
        <div className="flex items-center space-x-2 my-3 overflow-x-auto no-scrollbar">
          <button
            onClick={() => setFilter('all')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all shadow-sm ${
              filter === 'all'
                ? 'bg-[#059669] text-white'
                : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300'
            }`}
          >
            <ShoppingCart className="w-3.5 h-3.5" />
            <span>All</span>
          </button>

          <button
            onClick={() => setFilter('fresh')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all shadow-sm ${
              filter === 'fresh'
                ? 'bg-[#059669] text-white'
                : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300'
            }`}
          >
            <Recycle className="w-3.5 h-3.5 text-emerald-600" />
            <span>Fresh</span>
          </button>

          <button
            onClick={() => setFilter('used')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all shadow-sm ${
              filter === 'used'
                ? 'bg-[#059669] text-white'
                : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300'
            }`}
          >
            <Clock className="w-3.5 h-3.5 text-blue-500" />
            <span>Used</span>
          </button>
        </div>

        {/* Accounts List */}
        <div className="overflow-y-auto space-y-2.5 pr-0.5 pb-2 max-h-[55vh]">
          {filteredAccounts.length === 0 ? (
            <div className="text-center py-8 text-gray-400 text-xs">
              No saved accounts found.
            </div>
          ) : (
            filteredAccounts.map((acc) => {
              const isSelected = activeAccount && (activeAccount.id === acc.id || activeAccount.mobile === acc.mobile);
              const isFresh = acc.status === 'fresh';
              const phoneDisplay = acc.phone || (acc.mobile ? `+91 ${acc.mobile.replace(/^\+?91/, '')}` : '');

              return (
                <div
                  key={acc.id || acc.mobile}
                  onClick={() => {
                    onSelectAccount(acc);
                    onClose();
                  }}
                  className={`bg-white dark:bg-[#1E293B] rounded-2xl p-3 border shadow-card flex items-center justify-between cursor-pointer transition-all active:scale-[0.99] ${
                    isSelected
                      ? 'border-purple-300 dark:border-purple-700 bg-purple-50/20 dark:bg-purple-950/20 ring-1 ring-purple-400/30'
                      : 'border-gray-100 dark:border-gray-800 hover:border-gray-200'
                  }`}
                >
                  {/* Left: Avatar + Details */}
                  <div className="flex items-center space-x-3 min-w-0">
                    <div className="relative flex-shrink-0">
                      <div
                        className={`w-11 h-11 rounded-2xl flex items-center justify-center font-bold text-sm ${
                          isSelected
                            ? 'bg-[#EDE9FE] text-[#7C3AED] dark:bg-purple-950/80 dark:text-purple-300'
                            : isFresh
                            ? 'bg-[#ECFDF5] text-[#059669] dark:bg-emerald-950/80 dark:text-emerald-300'
                            : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300'
                        }`}
                      >
                        <User className="w-5 h-5" />
                      </div>

                      {/* Radio / Check Badge on Avatar */}
                      {isSelected ? (
                        <div className="w-4 h-4 rounded-full bg-[#10B981] text-white flex items-center justify-center absolute -top-1 -right-1 ring-2 ring-white dark:ring-gray-900 shadow-sm">
                          <Check className="w-2.5 h-2.5 stroke-[3]" />
                        </div>
                      ) : (
                        <div className="w-3.5 h-3.5 rounded-full border-2 border-gray-300 dark:border-gray-600 absolute -top-1 -right-1 bg-white dark:bg-gray-800" />
                      )}
                    </div>

                    <div className="min-w-0">
                      <h3 className="font-extrabold text-sm text-gray-900 dark:text-white truncate">
                        {acc.name || `User ${(acc.mobile || '').slice(-4)}`}
                      </h3>
                      <p className="text-xs text-gray-500 dark:text-gray-400 font-medium tracking-tight">
                        {phoneDisplay}
                      </p>
                    </div>
                  </div>

                  {/* Right: Status Pill & Delete Button */}
                  <div className="flex items-center space-x-2 flex-shrink-0" onClick={(e) => e.stopPropagation()}>
                    {isFresh ? (
                      <button
                        onClick={() => onToggleStatus && onToggleStatus(acc.id || acc.mobile)}
                        className="flex items-center space-x-1.5 bg-[#ECFDF5] dark:bg-emerald-950/60 border border-[#A7F3D0] dark:border-emerald-800 text-[#059669] dark:text-emerald-400 text-[11px] font-black px-2.5 py-1 rounded-full hover:bg-emerald-100 transition-colors"
                        title="Status: Fresh (Click to toggle)"
                      >
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                        <span>FRESH</span>
                      </button>
                    ) : (
                      <button
                        onClick={() => onToggleStatus && onToggleStatus(acc.id || acc.mobile)}
                        className="flex items-center space-x-1.5 bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 text-[11px] font-black px-2.5 py-1 rounded-full hover:bg-gray-200 transition-colors"
                        title="Status: Used (Click to toggle)"
                      >
                        <Clock className="w-3 h-3 text-gray-400" />
                        <span>USED</span>
                      </button>
                    )}

                    <button
                      onClick={() => onDeleteAccount && onDeleteAccount(acc.id || acc.mobile)}
                      className="p-1.5 text-gray-400 hover:text-red-500 rounded-lg transition-colors"
                      aria-label="Delete account"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
