import React, { useState } from 'react';
import { ArrowLeft, Plus, Minus, Search } from 'lucide-react';

export default function MenuList({
  restaurant,
  items,
  loading,
  cartLines,
  onAddToCart,
  onRemoveFromCart,
  onBack,
}) {
  const [searchQuery, setSearchQuery] = useState('');

  const getQuantity = (itemId) => {
    const line = cartLines.find((l) => l.id === itemId);
    return line ? line.quantity : 0;
  };

  const filteredItems = (items || []).filter((item) =>
    item.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="pb-24">
      {/* Top Bar with Back Button */}
      <div className="sticky top-14 z-30 bg-white/95 backdrop-blur px-4 py-3 border-b border-gray-100 flex items-center space-x-3">
        <button
          onClick={onBack}
          className="p-2 rounded-full hover:bg-gray-100 text-gray-700 transition-colors"
          aria-label="Back"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="flex-1 min-w-0">
          <h2 className="font-bold text-gray-900 truncate text-base">{restaurant.name}</h2>
          <p className="text-xs text-gray-500 truncate">{restaurant.area || 'Menu'}</p>
        </div>
      </div>

      {/* Menu Item Search */}
      <div className="p-4">
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-3 text-gray-400" />
          <input
            type="text"
            placeholder="Search items..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-gray-50 border border-gray-200 rounded-xl pl-9 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20"
          />
        </div>
      </div>

      {loading ? (
        <div className="p-4 space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="animate-pulse bg-gray-100 rounded-2xl h-24 w-full" />
          ))}
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="text-center py-12 text-gray-500 text-sm">No items found matching your search.</div>
      ) : (
        <div className="px-4 space-y-3">
          {filteredItems.map((item) => {
            const qty = getQuantity(item.id);
            const price = (item.price || item.base_price || 0) / 100;

            return (
              <div
                key={item.id}
                className="flex items-center justify-between p-3 bg-white rounded-2xl border border-gray-100 shadow-sm"
              >
                <div className="flex-1 pr-3">
                  <div className="flex items-center space-x-2">
                    <span
                      className={`w-3 h-3 rounded-sm border flex items-center justify-center p-0.5 ${
                        item.veg ? 'border-green-600' : 'border-red-600'
                      }`}
                    >
                      <span
                        className={`w-1.5 h-1.5 rounded-full ${
                          item.veg ? 'bg-green-600' : 'bg-red-600'
                        }`}
                      />
                    </span>
                    <h4 className="font-bold text-sm text-gray-900">{item.name}</h4>
                  </div>
                  <p className="text-sm font-semibold text-gray-800 mt-1">₹{price.toFixed(2)}</p>
                  {item.description && (
                    <p className="text-xs text-gray-500 line-clamp-2 mt-0.5">{item.description}</p>
                  )}
                </div>

                {/* Add/Remove Button */}
                <div className="flex-shrink-0">
                  {qty === 0 ? (
                    <button
                      onClick={() => onAddToCart(item)}
                      className="px-4 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-600 font-bold text-sm rounded-xl border border-blue-200 transition-colors"
                    >
                      ADD
                    </button>
                  ) : (
                    <div className="flex items-center space-x-2 bg-blue-600 text-white rounded-xl px-2 py-1 shadow">
                      <button
                        onClick={() => onRemoveFromCart(item.id)}
                        className="p-1 hover:bg-blue-700 rounded transition-colors"
                      >
                        <Minus className="w-3.5 h-3.5" />
                      </button>
                      <span className="font-bold text-sm min-w-[16px] text-center">{qty}</span>
                      <button
                        onClick={() => onAddToCart(item)}
                        className="p-1 hover:bg-blue-700 rounded transition-colors"
                      >
                        <Plus className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
