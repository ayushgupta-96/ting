import React from 'react';
import { UserCheck, ChevronDown } from 'lucide-react';

export default function TopBar({
  activeAccount,
  onOpenSwitchAccount,
}) {
  return (
    <header className="sticky top-0 z-40 bg-white/95 dark:bg-[#0F172A]/95 backdrop-blur-md border-b border-gray-100 dark:border-gray-800 px-4 py-2.5 transition-colors">
      <div className="flex items-center justify-between">
        {/* Left: Brand Logo + toing G New Distinctive Design */}
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 rounded-2xl bg-gradient-to-br from-[#7C3AED] via-[#8B5CF6] to-[#06B6D4] flex items-center justify-center text-white font-black text-base shadow-md shadow-purple-500/20">
            t
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="font-black text-lg tracking-tight text-gray-900 dark:text-white lowercase">
              toing
            </span>
            <span className="bg-gradient-to-r from-emerald-500 to-teal-500 text-white text-[11px] font-black px-2 py-0.5 rounded-lg shadow-sm tracking-wider uppercase">
              G
            </span>
          </div>
        </div>

        {/* Right: Active Account Selector Dropdown */}
        <button
          onClick={onOpenSwitchAccount}
          className="flex items-center space-x-1.5 bg-white dark:bg-gray-800 border border-purple-200 dark:border-purple-800/80 rounded-full px-3 py-1.5 text-xs font-bold text-gray-800 dark:text-gray-200 shadow-sm hover:border-purple-400 active:scale-95 transition-all"
        >
          <UserCheck className="w-3.5 h-3.5 text-[#7C3AED] dark:text-purple-400 flex-shrink-0" />
          <span className="tracking-tight text-xs">
            {activeAccount
              ? (activeAccount.phone || (activeAccount.mobile ? `+91 ${activeAccount.mobile}` : 'Select Account'))
              : 'Select Account'}
          </span>
          <ChevronDown className="w-3.5 h-3.5 text-gray-400 ml-0.5" />
        </button>
      </div>
    </header>
  );
}
