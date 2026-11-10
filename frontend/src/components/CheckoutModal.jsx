import React, { useState } from 'react';
import { X, CheckCircle, CreditCard, Banknote, QrCode } from 'lucide-react';

export default function CheckoutModal({
  isOpen,
  onClose,
  cartData,
  paymentOptions,
  onConfirmOrder,
  placing,
  orderResult,
}) {
  const [method, setMethod] = useState('cod');

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        onClick={!placing ? onClose : undefined}
        className="fixed inset-0 bg-black/50 backdrop-blur-sm transition-opacity"
      />

      {/* Modal Card */}
      <div className="relative bg-white rounded-3xl max-w-sm w-full p-5 shadow-2xl border border-gray-100 z-10">
        <div className="flex items-center justify-between pb-3 border-b border-gray-100">
          <h3 className="font-bold text-gray-900 text-lg">
            {orderResult ? 'Order Status' : 'Checkout & Payment'}
          </h3>
          {!placing && !orderResult && (
            <button
              onClick={onClose}
              className="p-1 rounded-full text-gray-400 hover:text-gray-600"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {orderResult ? (
          <div className="text-center py-6 space-y-3">
            <CheckCircle className="w-16 h-16 text-green-500 mx-auto" />
            <h4 className="font-bold text-lg text-gray-900">Order Placed Successfully!</h4>
            <p className="text-xs text-gray-500">
              Order ID: <span className="font-mono font-bold text-gray-800">#{orderResult.order_id}</span>
            </p>
            {orderResult.method === 'upi' && orderResult.upi_url && (
              <div className="bg-gray-50 p-4 rounded-2xl border border-gray-100 mt-3 space-y-2">
                <QrCode className="w-8 h-8 text-blue-600 mx-auto" />
                <p className="text-xs font-semibold text-gray-700">Scan or Tap to pay with UPI</p>
                <a
                  href={orderResult.upi_url}
                  className="inline-block px-4 py-2 bg-blue-600 text-white rounded-xl text-xs font-bold"
                >
                  Open UPI App
                </a>
              </div>
            )}
            <button
              onClick={onClose}
              className="w-full mt-4 py-2.5 bg-gray-100 hover:bg-gray-200 text-gray-800 font-bold text-sm rounded-xl"
            >
              Back to Store
            </button>
          </div>
        ) : (
          <div className="py-4 space-y-4">
            {/* Price breakdown */}
            <div className="bg-gray-50 p-3 rounded-2xl space-y-1.5 text-xs text-gray-600">
              <div className="flex justify-between">
                <span>Items Subtotal:</span>
                <span className="font-medium text-gray-900">₹{(cartData?.bill?.item_total || 0).toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span>Delivery & Platform Fee:</span>
                <span className="font-medium text-gray-900">₹{(cartData?.bill?.delivery || 0).toFixed(2)}</span>
              </div>
              {cartData?.bill?.discount > 0 && (
                <div className="flex justify-between text-green-600 font-medium">
                  <span>Coupon Discount:</span>
                  <span>-₹{cartData.bill.discount.toFixed(2)}</span>
                </div>
              )}
              <div className="border-t border-gray-200 pt-1.5 flex justify-between font-bold text-sm text-gray-900">
                <span>Total Amount:</span>
                <span className="text-blue-600">₹{(cartData?.bill?.to_pay || cartData?.amount || 0).toFixed(2)}</span>
              </div>
            </div>

            {/* Payment Method Selector */}
            <div className="space-y-2">
              <span className="text-xs font-bold text-gray-400 uppercase tracking-wider">
                Select Payment Mode
              </span>

              <div
                onClick={() => setMethod('cod')}
                className={`p-3 rounded-2xl border flex items-center justify-between cursor-pointer transition-all ${
                  method === 'cod'
                    ? 'border-blue-600 bg-blue-50/50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <Banknote className="w-5 h-5 text-gray-700" />
                  <div>
                    <h5 className="font-bold text-sm text-gray-900">Cash on Delivery</h5>
                    <p className="text-xs text-gray-500">Pay when your order arrives</p>
                  </div>
                </div>
                <input
                  type="radio"
                  name="pay_method"
                  checked={method === 'cod'}
                  onChange={() => setMethod('cod')}
                  className="accent-blue-600"
                />
              </div>

              <div
                onClick={() => setMethod('upi')}
                className={`p-3 rounded-2xl border flex items-center justify-between cursor-pointer transition-all ${
                  method === 'upi'
                    ? 'border-blue-600 bg-blue-50/50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <CreditCard className="w-5 h-5 text-gray-700" />
                  <div>
                    <h5 className="font-bold text-sm text-gray-900">UPI Instant Payment</h5>
                    <p className="text-xs text-gray-500">Pay via GPay, PhonePe, Paytm</p>
                  </div>
                </div>
                <input
                  type="radio"
                  name="pay_method"
                  checked={method === 'upi'}
                  onChange={() => setMethod('upi')}
                  className="accent-blue-600"
                />
              </div>
            </div>

            {/* Place Order CTA */}
            <button
              disabled={placing}
              onClick={() => onConfirmOrder(method)}
              className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-2xl shadow-lg transition-all flex items-center justify-center space-x-2 disabled:opacity-50"
            >
              <span>{placing ? 'Placing Order...' : 'Confirm & Place Order'}</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
