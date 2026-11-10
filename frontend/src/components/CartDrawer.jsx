import React from 'react';
import { X, Tag, MapPin, ChevronRight, ShoppingBag } from 'lucide-react';

export default function CartDrawer({
  isOpen,
  onClose,
  cart,
  addresses,
  selectedAddress,
  onSelectAddress,
  coupon,
  onApplyBestCoupon,
  onProceedToCheckout,
  loading,
}) {
  if (!isOpen) return null;

  const lines = cart?.items || [];
  const totalItems = lines.reduce((acc, l) => acc + (l.quantity || 1), 0);
  const totalAmount = (cart?.amount || 0);

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div
        onClick={onClose}
        className="absolute inset-0 bg-black/40 backdrop-blur-sm transition-opacity"
      />

      {/* Drawer */}
      <div className="absolute inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-md bg-white shadow-2xl flex flex-col">
          {/* Header */}
          <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <ShoppingBag className="w-5 h-5 text-blue-600" />
              <h2 className="font-bold text-base text-gray-900">Your Cart ({totalItems})</h2>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded-full text-gray-400 hover:text-gray-600"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {lines.length === 0 ? (
              <div className="text-center py-16 text-gray-400">
                <ShoppingBag className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p className="font-semibold text-gray-600">Your cart is empty</p>
                <p className="text-xs">Add items from a restaurant to proceed.</p>
              </div>
            ) : (
              <>
                {/* Items List */}
                <div className="space-y-2">
                  <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider">Items</h3>
                  {lines.map((l) => (
                    <div
                      key={l.id}
                      className="flex items-center justify-between py-2 border-b border-gray-50 text-sm"
                    >
                      <div className="flex-1">
                        <span className="font-medium text-gray-800">{l.name}</span>
                        <span className="text-xs text-gray-400 ml-2">x{l.quantity}</span>
                      </div>
                      <span className="font-bold text-gray-900">
                        ₹{(((l.price || 0) * (l.quantity || 1)) / 100).toFixed(2)}
                      </span>
                    </div>
                  ))}
                </div>

                {/* Delivery Address Selector */}
                <div className="bg-gray-50 rounded-2xl p-3 border border-gray-100">
                  <div className="flex items-center space-x-2 text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">
                    <MapPin className="w-3.5 h-3.5 text-blue-600" />
                    <span>Delivery Address</span>
                  </div>
                  {addresses && addresses.length > 0 ? (
                    <select
                      value={selectedAddress?.id || ''}
                      onChange={(e) => {
                        const addr = addresses.find((a) => a.id === e.target.value);
                        onSelectAddress(addr);
                      }}
                      className="w-full bg-white border border-gray-200 rounded-xl p-2 text-xs font-medium text-gray-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    >
                      {addresses.map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.name || a.receiver_name} - {a.address}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <p className="text-xs text-gray-400">Default location active</p>
                  )}
                </div>

                {/* Coupon Box */}
                <div className="bg-blue-50/60 rounded-2xl p-3 border border-blue-100 flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Tag className="w-4 h-4 text-blue-600" />
                    <span className="text-xs font-bold text-blue-900">
                      {coupon ? `Coupon Applied: ${coupon.code}` : 'Apply Promo Coupon'}
                    </span>
                  </div>
                  {!coupon && (
                    <button
                      onClick={onApplyBestCoupon}
                      className="text-xs font-bold text-blue-600 bg-white px-2.5 py-1 rounded-lg border border-blue-200 shadow-sm hover:bg-blue-50"
                    >
                      Best Coupon
                    </button>
                  )}
                </div>
              </>
            )}
          </div>

          {/* Footer Checkout Bar */}
          {lines.length > 0 && (
            <div className="p-4 border-t border-gray-100 bg-gray-50 space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-500">Estimated Total:</span>
                <span className="text-lg font-bold text-gray-900">₹{totalAmount.toFixed(2)}</span>
              </div>
              <button
                disabled={loading}
                onClick={onProceedToCheckout}
                className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl shadow-lg transition-all flex items-center justify-center space-x-2 disabled:opacity-50"
              >
                <span>{loading ? 'Calculating...' : 'Proceed to Checkout'}</span>
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
