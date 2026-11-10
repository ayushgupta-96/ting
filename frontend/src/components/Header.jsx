import React from 'react';
import { ShoppingBag, User, Phone } from 'lucide-react';

export default function Header({ 
  user, 
  activeMobile, 
  sessions, 
  onSwitchSession, 
  cartCount, 
  onOpenCart 
}) {
  return (
    <header className="sticky top-0 z-40 bg-telegram-bg/95 backdrop-blur border-b border-gray-100 shadow-sm px-4 py-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 rounded-full bg-blue-500 text-white flex items-center justify-center font-bold text-sm shadow">
            T
          </div>
          <div>
            <h1 className="font-bold text-base leading-tight">Toing Store</h1>
            <div className="flex items-center text-xs text-gray-500 space-x-1">
              <Phone className="w-3 h-3 text-green-600" />
              <select 
                value={activeMobile || ''} 
                onChange={(e) => onSwitchSession(e.target.value)}
                className="bg-transparent border-none text-xs font-medium text-gray-700 focus:outline-none cursor-pointer"
              >
                {sessions && sessions.length > 0 ? (
                  sessions.map((s) => (
                    <option key={s.mobile} value={s.mobile}>
                      {s.mobile}
                    </option>
                  ))
                ) : (
                  <option value="">{activeMobile || 'No Account'}</option>
                )}
              </select>
            </div>
          </div>
        </div>

        <button
          onClick={onOpenCart}
          className="relative p-2.5 rounded-full bg-telegram-secondaryBg hover:bg-gray-200 transition-colors"
          aria-label="View Cart"
        >
          <ShoppingBag className="w-5 h-5 text-gray-800" />
          {cartCount > 0 && (
            <span className="absolute -top-1 -right-1 bg-red-500 text-white text-[10px] font-bold w-5 h-5 rounded-full flex items-center justify-center shadow">
              {cartCount}
            </span>
          )}
        </button>
      </div>
    </header>
  );
}
