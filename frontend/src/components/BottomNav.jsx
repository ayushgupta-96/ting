import React from 'react';
import { User, MapPin, Search, ShoppingCart, History } from 'lucide-react';

export default function BottomNav({ activeTab, onSelectTab, cartCount = 0 }) {
  const tabs = [
    { id: 'accounts', label: 'Accounts', icon: User },
    { id: 'address', label: 'Address', icon: MapPin },
    { id: 'search', label: 'Search', icon: Search },
    { id: 'cart', label: 'Cart', icon: ShoppingCart },
    { id: 'orders', label: 'Orders', icon: History },
  ];

  return (
    <nav className="fixed bottom-0 inset-x-0 z-40 bg-white/95 dark:bg-[#0F172A]/95 backdrop-blur-lg border-t border-gray-100 dark:border-gray-800 shadow-nav py-1 px-3 transition-colors">
      <div className="max-w-md mx-auto grid grid-cols-5 gap-1">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;

          return (
            <button
              key={tab.id}
              onClick={() => onSelectTab(tab.id)}
              className={`flex flex-col items-center justify-center py-1 transition-all active:scale-90 ${
                isActive
                  ? 'text-[#7C3AED] dark:text-purple-400 font-bold'
                  : 'text-gray-400 dark:text-gray-500 hover:text-gray-600 font-medium'
              }`}
            >
              <div className="relative">
                <Icon
                  className={`w-5 h-5 transition-transform ${
                    isActive ? 'scale-110 stroke-[2.5]' : 'stroke-[1.8]'
                  }`}
                />
                {tab.id === 'cart' && cartCount > 0 && (
                  <span className="absolute -top-1.5 -right-2.5 bg-[#059669] text-white text-[9px] font-black min-w-[16px] h-4 px-1 rounded-full flex items-center justify-center shadow-sm pointer-events-none">
                    {cartCount > 99 ? '99+' : cartCount}
                  </span>
                )}
              </div>
              <span className={`text-[10px] mt-0.5 tracking-tight ${isActive ? 'font-bold' : 'font-medium'}`}>
                {tab.label}
              </span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
