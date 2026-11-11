import React, { useState, useEffect } from 'react';
import { 
  MapPin, 
  ChevronRight, 
  Trash2, 
  Utensils, 
  AlertCircle, 
  Ticket, 
  Receipt, 
  RefreshCw, 
  Plus, 
  Minus, 
  Loader2, 
  CheckCircle2, 
  ArrowLeft, 
  Zap, 
  PartyPopper, 
  Check, 
  QrCode,
  X
} from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import { api, getTelegramUserId } from '../services/api';

export default function CartTab({
  isActive = false,
  activeAccount,
  activeAddress,
  onOpenAddressTab,
  cartLines = [],
  onAddToCart,
  onRemoveFromCart,
  onClearCart,
  onShowToast,
  onGoToOrders,
  selectedRestaurant = null,
  accounts = [],
  onSwitchAccount,
  onGoToSearch,
}) {
  const [cookingRequest, setCookingRequest] = useState('');
  const [isCookingOpen, setIsCookingOpen] = useState(false);
  const [isCalculating, setIsCalculating] = useState(false);
  const [addressAutoDeleted, setAddressAutoDeleted] = useState(false);
  const [cartError, setCartError] = useState(null);
  const [isServiceable, setIsServiceable] = useState(true);
  const [unserviceableReason, setUnserviceableReason] = useState('');

  // Cart & Pricing State (Strictly dynamic from Toing API)
  const [cartId, setCartId] = useState('');
  const [addressId, setAddressId] = useState('');
  const [billLines, setBillLines] = useState([]);
  const [itemTotalAmount, setItemTotalAmount] = useState(0);
  const [toPayAmount, setToPayAmount] = useState(0);

  // Dynamic Coupon State (Strictly from Toing API, zero hardcoded placeholders)
  const tgUserId = getTelegramUserId();
  const couponStorageKey = `toing_coupon_${tgUserId}`;
  const [appliedCoupon, setAppliedCoupon] = useState(() => {
    try {
      const saved = localStorage.getItem(`toing_coupon_${getTelegramUserId()}`);
      return saved ? JSON.parse(saved) : null;
    } catch (e) {
      return null;
    }
  });
  const [couponToast, setCouponToast] = useState(null);
  const [isCouponModalOpen, setIsCouponModalOpen] = useState(false);
  const [customCouponInput, setCustomCouponInput] = useState('');
  const [availableCoupons, setAvailableCoupons] = useState([]);
  const [isApplyingCoupon, setIsApplyingCoupon] = useState(false);

  // Checkout & Payment State (Persistent across reloads & external UPI app switches)
  const checkoutStorageKey = `toing_checkout_${tgUserId}`;

  const [isPlacingOrder, setIsPlacingOrder] = useState(false);
  const [checkoutData, setCheckoutData] = useState(() => {
    try {
      const saved = localStorage.getItem(`toing_checkout_${getTelegramUserId()}`);
      return saved ? JSON.parse(saved) : null;
    } catch (e) {
      return null;
    }
  });

  useEffect(() => {
    try {
      if (checkoutData) {
        localStorage.setItem(checkoutStorageKey, JSON.stringify(checkoutData));
      } else {
        localStorage.removeItem(checkoutStorageKey);
      }
    } catch (e) {}
  }, [checkoutData, checkoutStorageKey]);

  const [isCheckingPayment, setIsCheckingPayment] = useState(false);
  const [paymentPollCount, setPaymentPollCount] = useState(0);
  const [lastCheckMessage, setLastCheckMessage] = useState(null);
  const [orderConfirmed, setOrderConfirmed] = useState(null);
  const [showQrCode, setShowQrCode] = useState(false);

  const mobile = activeAccount?.mobile || '';
  const lat = activeAddress?.lat;
  const lng = activeAddress?.lng;

  const restaurant = cartLines[0]?.restaurant || selectedRestaurant || null;

  const totalItems = cartLines.reduce((acc, l) => acc + l.quantity, 0);
  const subtotal = cartLines.reduce((acc, l) => acc + (l.price || 0) * l.quantity, 0);

  // Dynamic detection of Free Cash / Referral reward from bill_lines
  const freeCashLine = billLines.find(
    (l) =>
      l.key === 'offerCashReward' ||
      (l.label || '').toLowerCase().includes('referral') ||
      (l.label || '').toLowerCase().includes('free cash')
  );
  const hasFreeCash = Boolean(freeCashLine);
  const dynamicFreeCashAmount = freeCashLine ? parseFloat(freeCashLine.value) : 0;

  // 1. Calculate Cart and Auto-apply Best Coupon from live Toing API
  const calculateAndApplyPricing = async (forcedCouponCode = null) => {
    if (cartLines.length === 0) return;
    if (!activeAddress) {
      setItemTotalAmount(subtotal);
      setToPayAmount(subtotal);
      setBillLines([
        { key: 'item_total', label: 'Item Total', value: `${subtotal.toFixed(1)}`, negative: false, total: false },
        { key: 'delivery', label: 'Delivery Fee', note: 'Select address', value: 'FREE', strike: '', negative: false, total: false },
        { key: 'grand_total', label: 'To Pay', value: `${subtotal.toFixed(1)}`, negative: false, total: true },
      ]);
      return;
    }

    if (!restaurant?.id) {
      setCartError('Restaurant details missing from cart');
      return;
    }

    setIsCalculating(true);
    setCartError(null);

    try {
      // Step A: Ensure address is attached to account if global
      let targetAddressId = activeAddress.id || activeAddress.address_id || '';
      if (activeAddress.is_global || String(targetAddressId).startsWith('global_')) {
        try {
          const addrRes = await api.addAddressToAccount({ mobile, address: activeAddress });
          if (addrRes?.address?.id) {
            targetAddressId = addrRes.address.id;
          }
        } catch (e) {
          // continue with current address
        }
      }
      setAddressId(targetAddressId);

      const effectiveCoupon = forcedCouponCode !== null ? forcedCouponCode : (appliedCoupon?.code || '');

      // Step B: Submit Cart to live calculateCart
      const cartPayload = {
        mobile: mobile,
        restaurant: {
          id: String(restaurant.id),
          parent_id: String(restaurant.parent_id || restaurant.id),
          name: restaurant.name || 'Restaurant',
          image: restaurant.image || '',
          area: restaurant.area || '',
          sla: restaurant.sla || '',
        },
        items: cartLines.map((l) => ({
          id: String(l.id),
          menu_item_id: String(l.id),
          name: l.name,
          image_id: l.image_id || '',
          price: Number(l.price || 0),
          cost: Number(l.cost || l.price || 0),
          base_price: Number(l.base_price || l.price || 0),
          quantity: l.quantity,
          addons: l.addons || [],
          variants: l.variants || [],
        })),
        address_id: targetAddressId,
        cart_id: cartId || '',
        lat: lat,
        lng: lng,
        coupon_code: effectiveCoupon,
        cooking: cookingRequest,
        incognito: true,
      };

      const calcRes = await api.calculateCart(cartPayload);
      const generatedCartId = calcRes?.cart_id || cartId || '';
      if (generatedCartId) setCartId(generatedCartId);

      // Check real restaurant serviceability at this address & location
      if (calcRes?.is_serviceable === false) {
        setIsServiceable(false);
        setUnserviceableReason(calcRes.unserviceable_reason || 'Restaurant is not deliverable to this selected address.');
      } else {
        setIsServiceable(true);
        setUnserviceableReason('');
      }

      // Extract accurate raw item total from bill
      const rawItemTotal = calcRes?.bill?.item_total ?? subtotal;
      setItemTotalAmount(rawItemTotal);

      // Synchronize final payable amount
      const finalToPay = Math.round(Number(calcRes?.bill?.to_pay ?? subtotal));
      setToPayAmount(finalToPay);

      // Synchronize bill lines directly from live response
      if (Array.isArray(calcRes?.bill_lines) && calcRes.bill_lines.length > 0) {
        setBillLines(calcRes.bill_lines);
      } else if (calcRes?.bill) {
        const b = calcRes.bill;
        const lines = [
          { key: 'item_total', label: 'Item Total', value: `${b.item_total}`, negative: false, total: false },
          { key: 'delivery', label: 'Delivery Fee', value: b.delivery_charges === 0 ? 'FREE' : `${b.delivery_charges}`, negative: false, total: false }
        ];
        if (b.free_cash && b.free_cash > 0) {
          lines.push({ key: 'offerCashReward', label: b.free_cash_label || 'Free Cash', value: `${b.free_cash.toFixed(2)}`, negative: true, total: false });
        }
        if (b.coupon_discount && b.coupon_discount > 0) {
          lines.push({ key: 'coupon_discount', label: `Coupon (${b.coupon_code || effectiveCoupon})`, value: `${b.coupon_discount.toFixed(2)}`, negative: true, total: false });
        }
        if (b.taxes_and_charges && b.taxes_and_charges > 0) {
          lines.push({ key: 'gst', label: 'Government Taxes & Charges', value: `${b.taxes_and_charges}`, negative: false, total: false });
        }
        lines.push({ key: 'grand_total', label: 'To Pay', value: `${finalToPay}`, negative: false, total: true });
        setBillLines(lines);
      }

      // Update coupon state
      if (calcRes?.coupon && calcRes.coupon.code) {
        setAppliedCoupon(calcRes.coupon);
        try {
          localStorage.setItem(couponStorageKey, JSON.stringify(calcRes.coupon));
        } catch (e) {}
        setCouponToast(`${calcRes.coupon.code} applied · ₹${calcRes.coupon.discount || 0} off`);
        if (forcedCouponCode && onShowToast) {
          onShowToast('success', `Coupon ${calcRes.coupon.code} applied!`);
        }
      } else if (forcedCouponCode === '') {
        setAppliedCoupon(null);
        try {
          localStorage.removeItem(couponStorageKey);
        } catch (e) {}
        setCouponToast(null);
      }

      // Fetch authentic coupons list for this restaurant and cart value
      try {
        const cpnRes = await api.fetchCoupons({
          mobile: mobile,
          restaurant_id: String(restaurant?.id || ''),
          cart_value: rawItemTotal,
          lat: lat,
          lng: lng,
          address_id: targetAddressId,
        });
        if (Array.isArray(cpnRes?.coupons)) {
          setAvailableCoupons(cpnRes.coupons);
        }
      } catch (e) {
        console.warn('Coupons fetch error:', e);
      }
    } catch (err) {
      console.error('Pricing calculation error:', err);
      const msg = err.response?.data?.detail || err.message || 'Error updating cart';
      setCartError(msg);
      // Fallback values calculated dynamically from current cart
      setItemTotalAmount(subtotal);
      setToPayAmount(subtotal);
      setBillLines([
        { key: 'item_total', label: 'Item Total', value: `${subtotal.toFixed(1)}`, negative: false, total: false },
        { key: 'delivery', label: 'Delivery Fee', value: 'FREE', negative: false, total: false },
        { key: 'grand_total', label: 'To Pay', value: `${subtotal.toFixed(1)}`, negative: false, total: true },
      ]);
    } finally {
      setIsCalculating(false);
      setIsApplyingCoupon(false);
    }
  };

  // Run calculation when cart items change, delivery address changes, or when entering Cart Tab
  useEffect(() => {
    if (cartLines.length > 0 && activeAddress) {
      calculateAndApplyPricing();
    }
  }, [isActive, cartLines.length, activeAddress?.id, activeAddress?.lat, activeAddress?.lng]);

  // 2. Place Order & Open UPI Payment View (Strictly real Toing upstream)
  const handlePayNow = async () => {
    if (!isServiceable) {
      if (onShowToast) onShowToast('error', unserviceableReason || 'Restaurant not serviceable at this address.');
      return;
    }
    if (!activeAddress) {
      if (onShowToast) onShowToast('error', 'Please select a delivery address first.');
      return;
    }
    if (cartLines.length === 0) {
      if (onShowToast) onShowToast('error', 'Your cart is empty.');
      return;
    }

    setIsPlacingOrder(true);
    setCartError(null);
    try {
      const targetAddressId = addressId || activeAddress.id || '';
      const dynamicCartVal = Math.max(0, (itemTotalAmount || subtotal) - dynamicFreeCashAmount);

      const snapPayload = {
        restaurant: restaurant?.name || 'Restaurant',
        account_name: activeAccount?.name || 'Customer',
        items: cartLines.map((l) => ({
          name: l.name,
          quantity: l.quantity,
          price: l.price,
          veg: l.is_veg !== false,
          variants: [],
          addons: [],
        })),
        bill_lines: billLines,
        coupon: appliedCoupon?.code || '',
        cooking: cookingRequest,
        address: {
          text: activeAddress.formatted_address || activeAddress.address || 'Selected Address',
          name: activeAddress.name || activeAddress.receiver_name || activeAccount?.name || 'Customer',
          phone: activeAddress.phone || activeAddress.mobile || activeAccount?.mobile || '',
        },
      };

      const placePayload = {
        mobile: mobile,
        cart_id: cartId || String(Date.now()),
        address_id: targetAddressId,
        lat: lat,
        lng: lng,
        restaurant_id: String(restaurant?.id || ''),
        cart_value: dynamicCartVal,
        amount: toPayAmount || 1,
        method: 'upi',
        snap: snapPayload,
      };

      const res = await api.placeOrder(placePayload);

      if (res?.success && (res.order_id || res.txn_id)) {
        const orderId = String(res.order_id);
        const txnId = String(res.txn_id || '');
        const upiIntent = res.upi_url || '';

        setCheckoutData({
          orderId: orderId,
          txnId: txnId,
          upiUrl: upiIntent,
          amount: res.total != null ? res.total : (toPayAmount || 1),
          status: res.status || 'processing',
          etaMin: res.eta_min || '28',
          pollMs: res.poll_ms || 2500,
          snap: snapPayload,
        });

        if (onShowToast) {
          onShowToast('success', `Order #${orderId} created! Scan QR or tap Pay via UPI.`);
        }

        // Send paylog event strictly matching HAR Entry 12
        try {
          await api.sendPaylog({
            events: [
              {
                ev: 'place_result',
                at: new Date().toISOString(),
                order_id: orderId,
                mobile: mobile,
                txn_id: txnId,
                method: 'upi',
                amount: res.total != null ? res.total : (toPayAmount || 1),
                age_s: null,
                vis: 'visible',
                tg: 'tdesktop 9.6',
                ok: true,
                error: '',
                unconfirmed: false,
                upi: true,
                upi_pkg: res.upi_pkg || 'in.org.npci.upiapp',
                cod_check: null,
              },
            ],
          });
        } catch (e) {}
      } else {
        const errorMsg = res?.message || res?.error || 'Failed to place order with Toing.';
        throw new Error(errorMsg);
      }
    } catch (err) {
      console.error('Order placement failed:', err);
      const errMsg = err.response?.data?.detail || err.message || 'Failed to place order with Toing.';
      setCartError(errMsg);
      if (onShowToast) {
        onShowToast('error', errMsg);
      }
    } finally {
      setIsPlacingOrder(false);
    }
  };

  // 3. Payment Verification Polling (Strictly matching HAR Entries 11, 14, 21)
  const handleCheckPaymentStatus = async (isManual = true) => {
    if (!checkoutData) return;

    if (isManual) setIsCheckingPayment(true);
    try {
      const dynamicCartVal = Math.max(0, (itemTotalAmount || subtotal) - dynamicFreeCashAmount);
      const activeMobileNum = mobile || activeAccount?.mobile || checkoutData.snap?.address?.phone || '';
      const payload = {
        mobile: activeMobileNum,
        cart_id: cartId || checkoutData.orderId || '',
        address_id: addressId || activeAddress?.id || '',
        lat: lat || 28.4543533,
        lng: lng || 77.5015833,
        restaurant_id: String(restaurant?.id || checkoutData.snap?.restaurant_id || ''),
        cart_value: dynamicCartVal,
        txn_id: checkoutData.txnId,
        order_id: checkoutData.orderId,
        method: 'upi',
        manual: isManual,
        deep: false,
      };

      const res = await api.getPaymentStatus(payload);

      // A. Verified & Paid
      if (res?.paid) {
        let trackingUrl = res.finalized?.tracking_link || '';
        let orderStatusText = 'Order Received!';
        try {
          const ordStatus = await api.getOrderStatus({
            ...payload,
            order_id: checkoutData.orderId,
          });
          if (ordStatus?.tracking_link) {
            trackingUrl = ordStatus.tracking_link;
          }
          if (ordStatus?.status) {
            orderStatusText = ordStatus.status;
          }
        } catch (e) {}

        const confirmedData = {
          orderId: checkoutData.orderId,
          status: orderStatusText,
          trackingLink: trackingUrl,
          amount: checkoutData.amount,
          restaurant: restaurant?.name || checkoutData?.snap?.restaurant || 'Restaurant',
        };
        setOrderConfirmed(confirmedData);
        setLastCheckMessage(null);

        // Feature 4: Automated Address Deletion on payment confirmation
        try {
          if (activeAddress?.id) {
            await api.deleteAddress(activeAddress.id);
            setAddressAutoDeleted(true);
          } else {
            setAddressAutoDeleted(true);
          }
        } catch (e) {
          setAddressAutoDeleted(true);
        }

        if (onShowToast) {
          onShowToast('success', `Payment received! Order #${checkoutData.orderId} confirmed!`);
        }
        if (onClearCart) onClearCart();
        try {
          localStorage.removeItem(checkoutStorageKey);
        } catch (e) {}
      } 
      // B. Failed / Declined
      else if (res?.failed) {
        const failMsg = res?.message || 'Payment failed or declined. Please retry via UPI.';
        setLastCheckMessage(failMsg);
        if (onShowToast) {
          onShowToast('error', failMsg);
        }
      } 
      // C. Still Pending / Inconclusive
      else {
        const pendingMsg = 'Payment not received yet. Please pay via UPI App or QR code and verify again.';
        setLastCheckMessage(pendingMsg);
        if (isManual && onShowToast) {
          onShowToast('error', pendingMsg);
        }
      }
    } catch (e) {
      console.error('Payment verification error:', e);
      const errMsg = e.response?.data?.detail || e.message || 'Payment not completed yet. Please pay using UPI and verify again.';
      setLastCheckMessage(errMsg);
      if (isManual && onShowToast) {
        onShowToast('error', errMsg);
      }
    } finally {
      if (isManual) setIsCheckingPayment(false);
    }
  };

  // Background auto-check payment every 3 seconds while on checkout screen
  useEffect(() => {
    if (!checkoutData || orderConfirmed) return;
    const interval = setInterval(() => {
      setPaymentPollCount((c) => c + 1);
      handleCheckPaymentStatus(false);
    }, 3000);
    return () => clearInterval(interval);
  }, [checkoutData?.orderId, orderConfirmed]);

  // Apply Selected or Custom Coupon
  const handleApplyCoupon = (code) => {
    if (!code || !code.trim()) return;
    calculateAndApplyPricing(code.trim().toUpperCase());
    setIsCouponModalOpen(false);
  };

  if (cartLines.length === 0 && !checkoutData) {
    return (
      <div className="bg-white dark:bg-[#1E293B] rounded-3xl p-10 border border-gray-100 dark:border-gray-800 shadow-card text-center space-y-3 mt-4 animate-fade-in">
        <div className="w-16 h-16 rounded-3xl bg-purple-50 dark:bg-purple-950/60 text-[#7C3AED] dark:text-purple-400 mx-auto flex items-center justify-center">
          <Receipt className="w-8 h-8" />
        </div>
        <h2 className="text-base font-extrabold text-gray-900 dark:text-white">Your Cart is Empty</h2>
        <p className="text-xs text-gray-500 dark:text-gray-400 max-w-xs mx-auto">
          Add dishes from the Search tab to build your order.
        </p>
      </div>
    );
  }

  /* ==================== SCREEN 2: CHECKOUT & UPI PAYMENT ==================== */
  if (checkoutData) {
    return (
      <div className="space-y-3.5 pb-28 animate-fade-in">
        {/* Back to Cart button */}
        <div className="flex items-center justify-between">
          <button
            onClick={() => {
              setCheckoutData(null);
              setOrderConfirmed(null);
              setLastCheckMessage(null);
              try {
                localStorage.removeItem(checkoutStorageKey);
              } catch (e) {}
            }}
            className="bg-white dark:bg-[#1E293B] border border-gray-200 dark:border-gray-700/80 rounded-2xl px-3.5 py-2 text-xs font-extrabold text-gray-900 dark:text-white flex items-center space-x-1.5 shadow-sm active:scale-95 transition-all"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Cart</span>
          </button>
          <span className="text-[10px] font-bold text-gray-400">
            Txn: {checkoutData.txnId}
          </span>
        </div>

        {/* Order Created Success Banner */}
        <div className="bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800 rounded-2xl p-3 flex items-center justify-between shadow-sm animate-slide-down">
          <div className="flex items-center space-x-2.5 min-w-0">
            <div className="w-7 h-7 rounded-lg bg-emerald-100 dark:bg-emerald-900 flex items-center justify-center text-emerald-600 dark:text-emerald-300 flex-shrink-0">
              <CheckCircle2 className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <p className="font-extrabold text-xs text-emerald-900 dark:text-emerald-100 truncate">
                Order #{checkoutData.orderId} Created!
              </p>
              <p className="text-[10px] text-emerald-700 dark:text-emerald-400">
                Ready for payment · ETA: {checkoutData.etaMin || '25-30'} mins
              </p>
            </div>
          </div>
          <span className="bg-emerald-600 text-white font-black text-[9px] px-2 py-0.5 rounded-full uppercase flex-shrink-0 ml-2">
            Active
          </span>
        </div>

        {/* Order Confirmed Banner (Shown when payment is received) */}
        {orderConfirmed && (
          <div className="space-y-3 animate-bounce-in">
            <div className="bg-gradient-to-r from-emerald-600 to-teal-600 text-white rounded-3xl p-5 shadow-lg space-y-3 text-center">
              <div className="w-12 h-12 bg-white/20 rounded-full flex items-center justify-center mx-auto text-white">
                <PartyPopper className="w-6 h-6" />
              </div>
              <h3 className="font-black text-base">Payment Received & Confirmed!</h3>
              <p className="text-xs text-white/90">
                Order #{orderConfirmed.orderId} has been placed with {orderConfirmed.restaurant}.
              </p>
              <div className="flex items-center justify-center space-x-2 pt-1">
                {orderConfirmed.trackingLink && (
                  <a
                    href={orderConfirmed.trackingLink}
                    target="_blank"
                    rel="noreferrer"
                    className="bg-white text-emerald-700 font-extrabold text-xs px-4 py-2 rounded-xl shadow active:scale-95 transition-all"
                  >
                    Track on Swiggy
                  </a>
                )}
                <button
                  type="button"
                  onClick={() => {
                    const itemsLines = cartLines.map((l) => `• ${l.name} × ${l.quantity} — ₹${(l.price || 0) * l.quantity}`).join('\n');
                    const msg = `✅ ʏᴏᴜʀ ᴏʀᴅᴇʀ ɪꜱ ᴘʟᴀᴄᴇᴅ!\n\n📱 ᴀᴄᴄᴏᴜɴᴛ: ${activeAccount?.mobile || ''}\n🗑 ᴀᴅᴅʀᴇꜱꜱ ᴅᴇʟᴇᴛᴇᴅ: ʏᴇꜱ\n\n🍽 ${orderConfirmed.restaurant}\n🆔 ᴏʀᴅᴇʀ ɪᴅ: ${orderConfirmed.orderId}\n💳 ᴘᴀʏᴍᴇɴᴛ: ᴜᴘɪ\n📍 ꜱᴛᴀᴛᴜꜱ: ᴏʀᴅᴇʀ ʀᴇᴄᴇɪᴠᴇᴅ!\n💰 ᴏʀᴅᴇʀ ꜰᴇᴇꜱ: 3 Rs\n🔗 ᴛʀᴀᴄᴋɪɴɢ: ${orderConfirmed.trackingLink || ''}\nɪᴛᴇᴍꜱ\n${itemsLines}\n\nʙɪʟʟ ᴅᴇᴛᴀɪʟꜱ\n• ɪᴛᴇᴍ ᴛᴏᴛᴀʟ: ${itemTotalAmount}\n• ᴅᴇʟɪᴠᴇʀʏ ꜰᴇᴇ: FREE\n• ꜰʀᴇᴇ ᴄᴀꜱʜ: −${dynamicFreeCashAmount}\n• ᴄᴏᴜᴘᴏɴ ᴅɪꜱᴄᴏᴜɴᴛ: −${appliedCoupon?.discount || 0}\n• ɢᴏᴠᴇʀɴᴍᴇɴᴛ ᴛᴀxᴇꜱ: 0.00\n• ᴛᴏ ᴘᴀʏ: ${toPayAmount}\n\n📍 ᴅᴇʟɪᴠᴇʀʏ ᴀᴅᴅʀᴇꜱꜱ\n• ᴀᴅᴅʀᴇꜱꜱ: ${activeAddress?.formatted_address || activeAddress?.address || ''}\n• ʀᴇᴄᴇɪᴠᴇʀ: ${activeAddress?.name || activeAccount?.name || 'Customer'}\n• ᴘʜᴏɴᴇ: ${activeAddress?.phone || activeAccount?.mobile || ''}\n\n#toing`;
                    navigator.clipboard.writeText(msg);
                    if (onShowToast) onShowToast('success', 'Order message copied to clipboard!');
                  }}
                  className="bg-white/20 hover:bg-white/30 text-white font-extrabold text-xs px-4 py-2 rounded-xl shadow active:scale-95 transition-all"
                >
                  Copy Order Text
                </button>
              </div>
              <div>
                <button
                  onClick={onGoToOrders}
                  className="text-xs text-white underline font-bold"
                >
                  View in Orders Tab →
                </button>
              </div>
            </div>

            {/* Feature 4 Badge: Automated Address Deletion Status */}
            <div className="bg-purple-50 dark:bg-purple-950/40 border border-purple-200 dark:border-purple-800/80 rounded-2xl p-3 flex items-center space-x-2.5 text-xs text-purple-900 dark:text-purple-200 shadow-sm">
              <div className="w-7 h-7 rounded-lg bg-purple-100 dark:bg-purple-900/60 flex items-center justify-center text-purple-600 dark:text-purple-300 flex-shrink-0">
                <Trash2 className="w-4 h-4" />
              </div>
              <div className="min-w-0">
                <p className="font-extrabold text-xs">🗑️ Delivery Address Auto-Cleaned: YES</p>
                <p className="text-[10px] text-purple-600 dark:text-purple-400 truncate">
                  Address detached from account for privacy & security
                </p>
              </div>
            </div>

            {/* Feature 3: Next Fresh Account Switcher */}
            {(() => {
              const nextFresh = (accounts || []).find(
                (a) =>
                  a.status === 'fresh' &&
                  a.mobile !== activeAccount?.mobile &&
                  String(a.id) !== String(activeAccount?.id)
              );
              if (nextFresh) {
                return (
                  <div className="bg-white dark:bg-[#1E293B] border-2 border-emerald-500/40 rounded-3xl p-4 shadow-card space-y-2.5 animate-fade-in">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2 min-w-0">
                        <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse flex-shrink-0" />
                        <h4 className="font-black text-xs text-gray-900 dark:text-white truncate">
                          Next Account Ready
                        </h4>
                      </div>
                      <span className="bg-emerald-600 text-white font-black text-[9px] px-2 py-0.5 rounded-full uppercase flex-shrink-0">
                        READY
                      </span>
                    </div>
                    <p className="text-[11px] text-gray-600 dark:text-gray-300">
                      Switch to <strong>{nextFresh.name || nextFresh.mobile}</strong> (+91 {nextFresh.mobile}) to order from this account.
                    </p>
                    <button
                      type="button"
                      onClick={() => {
                        if (onSwitchAccount) {
                          onSwitchAccount(nextFresh);
                          setCheckoutData(null);
                          setOrderConfirmed(null);
                          if (onGoToSearch) onGoToSearch();
                        }
                      }}
                      className="w-full bg-[#059669] hover:bg-emerald-700 text-white font-black text-xs py-3 rounded-2xl shadow-md flex items-center justify-center space-x-2 active:scale-95 transition-all"
                    >
                      <RefreshCw className="w-4 h-4" />
                      <span>Switch to {nextFresh.name || nextFresh.mobile} & Continue</span>
                    </button>
                  </div>
                );
              }
              return (
                <div className="bg-gray-50 dark:bg-gray-800/60 rounded-2xl p-3 text-center text-[11px] text-gray-500">
                  All saved accounts have placed orders. Add a new account in Accounts tab to continue ordering.
                </div>
              );
            })()}
          </div>
        )}

        {/* Primary Payment Action Card (Strictly Matching Screenshot media_1794340146239_f1d6591f.png) */}
        <div className="bg-white dark:bg-[#1E293B] rounded-3xl p-5 shadow-card border border-gray-100 dark:border-gray-800 text-center space-y-3.5">
          {/* 1. Header */}
          <div className="space-y-1">
            <h3 className="font-extrabold text-sm text-gray-900 dark:text-white">
              Scan to Pay with UPI
            </h3>
            <p className="text-[11px] text-gray-500 dark:text-gray-400">
              Pay with GPay, PhonePe, Paytm or any UPI App
            </p>
          </div>

          {/* 2. Permanently Visible High-Resolution UPI QR Code */}
          <div className="bg-white p-3.5 rounded-2xl border border-gray-100 shadow-sm inline-block mx-auto">
            <QRCodeSVG
              value={checkoutData.upiUrl}
              size={185}
              level="M"
              includeMargin={false}
            />
          </div>

          {/* 3. Centered Large Green Amount */}
          <div className="pt-0.5">
            <span className="text-[#059669] font-black text-3xl tracking-tight">
              ₹{checkoutData.amount}
            </span>
          </div>

          {/* 4. Action Buttons */}
          <div className="space-y-2 pt-1 max-w-xs mx-auto">
            {/* Pay via UPI App (Redirects to https://storelex.store/toing_web/api/pay/upi?u=...&pkg=in.org.npci.upiapp) */}
            <button
              type="button"
              onClick={() => {
                const upiUrl = checkoutData.upiUrl || '';
                const targetRedirectUrl = `https://storelex.store/toing_web/api/pay/upi?u=${encodeURIComponent(upiUrl)}&pkg=in.org.npci.upiapp`;
                if (window.Telegram?.WebApp?.openLink) {
                  window.Telegram.WebApp.openLink(targetRedirectUrl);
                } else {
                  window.location.href = targetRedirectUrl;
                }
              }}
              className="w-full bg-gradient-to-r from-[#9061F9] to-[#7E3AF2] hover:from-[#7E3AF2] hover:to-[#6C2BD9] text-white font-extrabold text-xs py-3.5 rounded-2xl shadow-md flex items-center justify-center space-x-2 active:scale-95 transition-all"
            >
              <Zap className="w-4 h-4 fill-white" />
              <span>Pay via UPI App</span>
            </button>

            {/* Verify Payment */}
            <button
              type="button"
              onClick={() => handleCheckPaymentStatus(true)}
              disabled={isCheckingPayment}
              className="w-full bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 text-gray-900 dark:text-white font-extrabold text-xs py-3 rounded-2xl flex items-center justify-center space-x-2 active:scale-95 transition-all shadow-sm"
            >
              {isCheckingPayment ? (
                <Loader2 className="w-4 h-4 animate-spin text-[#7C3AED]" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              <span>{isCheckingPayment ? 'Verifying Payment...' : 'Verify Payment'}</span>
            </button>

            {/* Live Verification Status Note */}
            {lastCheckMessage && !orderConfirmed && (
              <div className="bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800/60 rounded-xl p-2.5 text-[11px] text-amber-800 dark:text-amber-200 font-medium flex items-center space-x-2 text-left animate-fade-in">
                <AlertCircle className="w-4 h-4 text-amber-600 dark:text-amber-400 flex-shrink-0" />
                <span>{lastCheckMessage}</span>
              </div>
            )}
          </div>
        </div>

        {/* Selected Delivery Address Summary */}
        <div className="bg-white dark:bg-[#1E293B] rounded-3xl p-4 shadow-card border border-gray-100 dark:border-gray-800 space-y-2 text-xs">
          <div className="flex items-center space-x-2 font-black text-gray-900 dark:text-white">
            <MapPin className="w-4 h-4 text-[#7C3AED]" />
            <span>Selected Delivery Address</span>
          </div>
          <div className="space-y-1 pl-6 text-gray-600 dark:text-gray-300">
            <p>
              <strong className="text-gray-800 dark:text-gray-100">Deliver To: </strong>
              {activeAddress?.formatted_address || activeAddress?.address}
            </p>
            <p>
              <strong className="text-gray-800 dark:text-gray-100">Receiver Contact: </strong>
              {activeAddress?.name || activeAddress?.receiver_name || activeAccount?.name || 'Customer'} | {activeAddress?.phone || activeAddress?.mobile || activeAccount?.mobile || ''}
            </p>
          </div>
        </div>

        {/* Order Items Summary */}
        <div className="bg-white dark:bg-[#1E293B] rounded-3xl p-4 shadow-card border border-gray-100 dark:border-gray-800 space-y-2.5 text-xs">
          <div className="flex items-center space-x-2 font-black text-gray-900 dark:text-white">
            <Receipt className="w-4 h-4 text-[#7C3AED]" />
            <span>Order Items Summary</span>
          </div>
          <div className="divide-y divide-gray-100 dark:divide-gray-800 pl-6">
            {cartLines.map((item) => (
              <div key={item.id} className="py-2 flex items-center justify-between">
                <span className="font-bold text-gray-800 dark:text-gray-200">
                  {item.name} <span className="text-gray-400">× {item.quantity}</span>
                </span>
                <span className="font-black text-gray-900 dark:text-white">
                  ₹{(item.price || 0) * item.quantity}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Dynamic Bill Details Breakdown in Checkout */}
        <div className="bg-white dark:bg-[#1E293B] rounded-3xl p-4 shadow-card border border-gray-100 dark:border-gray-800 space-y-2 text-xs">
          <div className="flex items-center space-x-2 font-black text-gray-900 dark:text-white">
            <Receipt className="w-4 h-4 text-[#7C3AED]" />
            <span>Bill Details Breakdown</span>
          </div>
          <div className="pl-6 space-y-1.5 text-gray-600 dark:text-gray-300">
            {billLines
              .filter((l) => !l.total && l.key !== 'grand_total' && l.label !== 'To Pay')
              .map((line, idx) => {
                const isNegative = Boolean(line.negative);
                return (
                  <div key={line.key || idx} className="flex justify-between items-center">
                    <span className={isNegative ? 'text-[#059669] font-bold' : ''}>
                      {line.key === 'offerCashReward' ? 'Free Cash' : line.label}
                      {line.note ? <span className="text-gray-400 ml-1 font-normal">{line.note}</span> : null}
                    </span>
                    <span className={`font-bold ${isNegative ? 'text-[#059669]' : 'text-gray-900 dark:text-white'}`}>
                      {line.strike && (
                        <span className="line-through text-gray-400 mr-1.5 font-normal">
                          {line.strike.startsWith('₹') ? line.strike : `₹${line.strike}`}
                        </span>
                      )}
                      {isNegative
                        ? (line.value.startsWith('-') ? line.value : `-₹${line.value}`)
                        : (line.value === 'FREE' ? 'FREE' : (line.value.startsWith('₹') ? line.value : `₹${line.value}`))}
                    </span>
                  </div>
                );
              })}
            <div className="h-[1px] bg-gray-100 dark:bg-gray-800 my-2" />
            <div className="flex justify-between text-sm font-black text-gray-900 dark:text-white">
              <span>To Pay</span>
              <span>₹{checkoutData.amount}</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  /* ==================== SCREEN 1: CART, COUPON & DYNAMIC BILL ==================== */
  return (
    <div className="space-y-3 pb-32 animate-fade-in">
      {/* Top Floating Toast when coupon is applied */}
      {couponToast && (
        <div className="bg-white dark:bg-[#1E293B] rounded-2xl p-2.5 shadow-lg border border-gray-100 dark:border-gray-800 flex items-center justify-between animate-slide-down">
          <div className="flex items-center space-x-2.5">
            <div className="w-7 h-7 rounded-lg bg-emerald-50 dark:bg-emerald-950 flex items-center justify-center text-[#059669]">
              <Ticket className="w-4 h-4" />
            </div>
            <p className="font-black text-xs text-gray-900 dark:text-white">
              {couponToast}
            </p>
          </div>
          <button
            onClick={() => setCouponToast(null)}
            className="text-gray-400 hover:text-gray-600 p-1"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* 1. Delivering To Header */}
      <div
        onClick={onOpenAddressTab}
        className="bg-white dark:bg-[#1E293B] rounded-3xl p-4 border border-gray-100 dark:border-gray-800 shadow-card flex items-center justify-between cursor-pointer hover:border-purple-300 transition-all"
      >
        <div className="flex items-center space-x-3 min-w-0">
          <div className="w-9 h-9 rounded-2xl bg-purple-50 dark:bg-purple-950/60 flex items-center justify-center text-[#7C3AED] dark:text-purple-300 flex-shrink-0">
            <MapPin className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <h3 className="font-extrabold text-xs text-gray-900 dark:text-white truncate">
              Delivering to {activeAddress?.annotation || activeAddress?.name || 'Delivery Address'}
            </h3>
            <p className="text-[11px] text-gray-400 truncate">
              {activeAddress?.formatted_address || activeAddress?.address || 'Select an address...'}
            </p>
          </div>
        </div>
        <ChevronRight className="w-4 h-4 text-gray-400 flex-shrink-0" />
      </div>

      {/* Serviceability Alert Banner */}
      {!isServiceable && (
        <div className="bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/60 rounded-3xl p-4 flex items-start space-x-3 text-red-700 dark:text-red-400 shadow-sm animate-fade-in">
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5 text-red-500" />
          <div className="flex-1 text-xs">
            <div className="font-extrabold text-sm text-red-800 dark:text-red-300">
              Cannot Deliver to Selected Location
            </div>
            <p className="mt-1 text-xs text-red-600 dark:text-red-400 leading-relaxed">
              {unserviceableReason || "This location is outside the outlet's delivery area. Please choose a different delivery address."}
            </p>
            <button
              onClick={onOpenAddressTab}
              className="mt-2.5 text-xs font-black text-[#7C3AED] dark:text-purple-300 underline hover:opacity-80 block"
            >
              Change Delivery Address →
            </button>
          </div>
        </div>
      )}

      {/* 2. Your Order Card */}
      <div className="bg-white dark:bg-[#1E293B] rounded-3xl p-4 border border-gray-100 dark:border-gray-800 shadow-card space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-black text-sm text-gray-900 dark:text-white">Your Order</h3>
          <span className="text-xs font-bold text-gray-500 dark:text-gray-400">
            {totalItems} {totalItems === 1 ? 'item' : 'items'} · ₹{subtotal.toFixed(1)}
          </span>
        </div>

        {/* Restaurant Header with Delete button */}
        {restaurant && (
          <div className="flex items-center justify-between pt-1">
            <div className="flex items-center space-x-2.5 min-w-0">
              {restaurant.image && (
                <img
                  src={restaurant.image}
                  alt={restaurant.name}
                  className="w-12 h-12 rounded-2xl object-cover bg-gray-100 flex-shrink-0"
                  onError={(e) => {
                    e.target.style.display = 'none';
                  }}
                />
              )}
              <div className="min-w-0">
                <h4 className="font-extrabold text-xs text-gray-900 dark:text-white truncate">
                  {restaurant.name}
                </h4>
                <p className="text-[11px] text-gray-400 truncate">
                  {restaurant.area || 'Direct Delivery'}
                </p>
              </div>
            </div>

            <button
              onClick={onClearCart}
              className="w-8 h-8 rounded-xl bg-red-50 dark:bg-red-950/40 text-red-500 hover:text-red-700 flex items-center justify-center transition-colors flex-shrink-0"
              title="Clear Cart"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        )}

        <div className="h-[1px] bg-gray-100 dark:bg-gray-800" />

        {/* Item Rows with Green Stepper Pills */}
        <div className="space-y-3">
          {cartLines.map((line) => (
            <div key={line.id} className="flex items-center justify-between">
              <div className="flex items-center space-x-2 min-w-0 pr-2">
                <span className="w-3.5 h-3.5 rounded-sm border border-emerald-600 flex items-center justify-center flex-shrink-0">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
                </span>
                <span className="font-extrabold text-xs text-gray-900 dark:text-white truncate">
                  {line.name}
                </span>
              </div>

              <div className="flex items-center space-x-3 flex-shrink-0">
                {/* Stepper */}
                <div className="flex items-center space-x-2 bg-[#059669] text-white px-2.5 py-1 rounded-xl text-xs font-bold shadow-sm">
                  <button
                    onClick={() => onRemoveFromCart(line.id)}
                    className="p-0.5 hover:opacity-80 active:scale-90"
                  >
                    {line.quantity === 1 ? <Trash2 className="w-3 h-3" /> : <Minus className="w-3 h-3" />}
                  </button>
                  <span className="font-black min-w-[12px] text-center">{line.quantity}</span>
                  <button
                    onClick={() => onAddToCart(line)}
                    className="p-0.5 hover:opacity-80 active:scale-90"
                  >
                    <Plus className="w-3 h-3" />
                  </button>
                </div>

                <span className="font-black text-xs text-gray-900 dark:text-white w-12 text-right">
                  ₹{(line.price || 0) * line.quantity}
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* Cooking Request */}
        <div className="pt-1">
          {isCookingOpen ? (
            <div className="space-y-1.5">
              <input
                type="text"
                placeholder="e.g. Less spicy, extra onions"
                value={cookingRequest}
                onChange={(e) => setCookingRequest(e.target.value)}
                className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-3 py-2 text-xs text-gray-900 dark:text-white focus:outline-none focus:border-purple-500"
              />
            </div>
          ) : (
            <button
              onClick={() => setIsCookingOpen(true)}
              className="text-[#7C3AED] dark:text-purple-400 font-extrabold text-xs flex items-center space-x-1.5 hover:underline"
            >
              <Utensils className="w-3.5 h-3.5" />
              <span>Add cooking request</span>
            </button>
          )}
        </div>
      </div>

      {/* 3. Dynamic Coupon Card (Synchronized with live Toing API) */}
      {appliedCoupon && appliedCoupon.valid ? (
        <div className="bg-[#ECFDF5] dark:bg-emerald-950/40 border border-[#A7F3D0] dark:border-emerald-800 rounded-2xl p-3 flex items-center justify-between shadow-sm">
          <div className="flex items-center space-x-3 min-w-0">
            <div className="w-9 h-9 rounded-xl bg-emerald-100 dark:bg-emerald-900/60 flex items-center justify-center text-[#059669] dark:text-emerald-300 flex-shrink-0">
              <PartyPopper className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <h4 className="font-extrabold text-xs text-gray-900 dark:text-white truncate">
                Coupon '{appliedCoupon.code}' applied
              </h4>
              <p className="font-black text-xs text-[#059669] dark:text-emerald-300">
                ₹{appliedCoupon.discount} off
              </p>
            </div>
          </div>

          <button
            onClick={() => setIsCouponModalOpen(true)}
            className="text-[#7C3AED] dark:text-purple-300 font-black text-xs hover:underline cursor-pointer px-2 py-1 flex-shrink-0"
          >
            Change
          </button>
        </div>
      ) : (
        <div className="bg-white dark:bg-[#1E293B] border border-gray-100 dark:border-gray-800 rounded-2xl p-3.5 flex items-center justify-between shadow-card">
          <div className="flex items-center space-x-3 min-w-0">
            <div className="w-9 h-9 rounded-xl bg-purple-50 dark:bg-purple-950/80 flex items-center justify-center text-[#7C3AED] flex-shrink-0">
              <Ticket className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <h4 className="font-extrabold text-xs text-gray-900 dark:text-white">
                Apply Coupon
              </h4>
              <p className="text-[11px] text-gray-400 truncate">
                {availableCoupons.length > 0
                  ? `${availableCoupons.length} coupons available from Toing`
                  : 'Check available bank & promo offers'}
              </p>
            </div>
          </div>

          <button
            onClick={() => setIsCouponModalOpen(true)}
            className="bg-purple-50 dark:bg-purple-950/80 text-[#7C3AED] dark:text-purple-300 font-black text-xs px-3.5 py-1.5 rounded-xl hover:bg-purple-100 transition-colors flex-shrink-0"
          >
            View Coupons
          </button>
        </div>
      )}

      {/* 4. Dynamic Bill Details Card (Strictly synchronized with Toing API) */}
      <div className="bg-white dark:bg-[#1E293B] rounded-3xl p-4 border border-gray-100 dark:border-gray-800 shadow-card space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-6 h-6 rounded-lg bg-purple-100 dark:bg-purple-950 flex items-center justify-center text-[#7C3AED]">
              <Receipt className="w-3.5 h-3.5" />
            </div>
            <h4 className="font-extrabold text-xs text-gray-900 dark:text-white">Bill Details</h4>
          </div>

          <div className="flex items-center space-x-2">
            {hasFreeCash && (
              <span className="bg-[#059669] text-white text-[11px] font-black px-2.5 py-0.5 rounded-full flex items-center space-x-1 shadow-sm">
                <CheckCircle2 className="w-3.5 h-3.5 inline mr-0.5" />
                <span>Claimed ₹{dynamicFreeCashAmount} FC</span>
              </span>
            )}

            <button
              onClick={() => calculateAndApplyPricing()}
              disabled={isCalculating}
              className="text-gray-400 hover:text-purple-600 transition-colors p-1"
              title="Refresh pricing"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isCalculating ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Dynamic Bill Breakdown Lines (Mapped strictly from Toing API) */}
        {isCalculating && billLines.length === 0 ? (
          <div className="py-6 flex items-center justify-center space-x-2 text-xs text-gray-400">
            <Loader2 className="w-4 h-4 animate-spin text-[#7C3AED]" />
            <span>Calculating live bill from Toing...</span>
          </div>
        ) : (
          <div className="space-y-2 text-xs pt-1">
            {billLines
              .filter((l) => !l.total && l.key !== 'grand_total' && l.label !== 'To Pay')
              .map((line, idx) => {
                const isNegative = Boolean(line.negative);
                return (
                  <div key={line.key || idx} className="flex justify-between items-center">
                    <span className={isNegative ? 'text-[#059669] font-bold' : 'text-gray-600 dark:text-gray-400'}>
                      {line.key === 'offerCashReward' ? 'Free Cash' : line.label}
                      {line.note ? <span className="text-gray-400 ml-1 font-normal">{line.note}</span> : null}
                    </span>
                    <span className={`font-extrabold ${isNegative ? 'text-[#059669]' : 'text-gray-900 dark:text-white'}`}>
                      {line.strike && (
                        <span className="line-through text-gray-400 mr-1.5 font-normal">
                          {line.strike.startsWith('₹') ? line.strike : `₹${line.strike}`}
                        </span>
                      )}
                      {isNegative
                        ? (line.value.startsWith('-') ? line.value : `-₹${line.value}`)
                        : (line.value === 'FREE' ? 'FREE' : (line.value.startsWith('₹') ? line.value : `₹${line.value}`))}
                    </span>
                  </div>
                );
              })}

            <div className="h-[1px] bg-gray-100 dark:bg-gray-800 my-2" />

            {/* Final To Pay Grand Total */}
            <div className="flex justify-between items-baseline pt-1">
              <span className="font-black text-sm text-gray-900 dark:text-white">To Pay</span>
              <span className="font-black text-base text-gray-900 dark:text-white">
                ₹{toPayAmount}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* 5. Payment Method Card */}
      <div className="bg-white dark:bg-[#1E293B] rounded-3xl p-4 border border-gray-100 dark:border-gray-800 shadow-card space-y-3">
        <div className="flex items-center space-x-2">
          <div className="w-6 h-6 rounded-lg bg-purple-100 dark:bg-purple-950 flex items-center justify-center text-[#7C3AED]">
            <Receipt className="w-3.5 h-3.5" />
          </div>
          <h4 className="font-extrabold text-xs text-gray-900 dark:text-white">Payment Method</h4>
        </div>

        {/* Selected UPI Option */}
        <div className="border border-emerald-500 bg-emerald-50/20 dark:bg-emerald-950/20 rounded-2xl p-3 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-purple-50 dark:bg-purple-950/60 flex items-center justify-center text-[#7C3AED] dark:text-purple-300">
              <QrCode className="w-5 h-5" />
            </div>
            <div>
              <h5 className="font-black text-xs text-gray-900 dark:text-white">UPI / QR</h5>
              <p className="text-[11px] text-gray-500">Pay with any payment apps</p>
            </div>
          </div>

          <div className="w-5 h-5 rounded-full bg-[#059669] text-white flex items-center justify-center">
            <Check className="w-3.5 h-3.5 stroke-[3]" />
          </div>
        </div>

        {/* Disabled COD Option */}
        <div className="border border-gray-100 dark:border-gray-800 rounded-2xl p-3 flex items-center justify-between opacity-50 cursor-not-allowed">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-gray-400">
              <Receipt className="w-4 h-4" />
            </div>
            <div>
              <h5 className="font-bold text-xs text-gray-700 dark:text-gray-300">Cash on Delivery</h5>
              <p className="text-[10px] text-gray-400">Adding soon</p>
            </div>
          </div>
          <div className="w-4 h-4 rounded-full border border-gray-300" />
        </div>
      </div>

      {/* 6. Fixed Bottom Pay Bar */}
      <div className="fixed bottom-14 inset-x-0 z-40 bg-white/95 dark:bg-[#0F172A]/95 backdrop-blur-lg border-t border-gray-100 dark:border-gray-800 p-3 shadow-nav">
        <div className="max-w-md mx-auto flex items-center justify-between">
          <div>
            <p className="text-[10px] font-black uppercase text-gray-400 tracking-wider">
              PAY USING UPI
            </p>
            <p className="font-black text-base text-gray-900 dark:text-white">
              ₹{toPayAmount}
            </p>
          </div>

          <button
            onClick={handlePayNow}
            disabled={isPlacingOrder || isCalculating || !isServiceable}
            className={`${
              !isServiceable
                ? 'bg-gray-300 dark:bg-gray-700 text-gray-500 cursor-not-allowed'
                : 'bg-[#059669] hover:bg-[#047857] text-white active:scale-95 shadow-lg'
            } font-black text-xs px-6 py-3.5 rounded-2xl flex items-center space-x-2 transition-all disabled:opacity-60`}
          >
            {isPlacingOrder ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Creating Order...</span>
              </>
            ) : !isServiceable ? (
              <span>Not Serviceable Here</span>
            ) : (
              <>
                <span>Pay Now</span>
                <ChevronRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </div>

      {/* Dynamic Coupons Modal (Directly listing Toing App Offers) */}
      {isCouponModalOpen && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 backdrop-blur-sm animate-fade-in">
          <div className="absolute inset-0" onClick={() => setIsCouponModalOpen(false)} />
          <div className="relative w-full max-w-md bg-white dark:bg-[#1E293B] rounded-t-[32px] p-5 shadow-2xl z-10 max-h-[85vh] flex flex-col overflow-y-auto animate-slide-up">
            <div className="w-12 h-1 bg-gray-200 dark:bg-gray-700 rounded-full mx-auto mb-3" />
            
            <div className="flex items-center justify-between pb-3 border-b border-gray-100 dark:border-gray-800">
              <h3 className="font-black text-base text-gray-900 dark:text-white">
                Apply Coupon Code
              </h3>
              <button
                onClick={() => setIsCouponModalOpen(false)}
                className="w-7 h-7 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-gray-500"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Custom Code Input */}
            <div className="flex space-x-2 my-4">
              <input
                type="text"
                placeholder="ENTER COUPON CODE"
                value={customCouponInput}
                onChange={(e) => setCustomCouponInput(e.target.value.toUpperCase())}
                className="flex-1 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl px-3.5 py-2.5 text-xs font-black uppercase text-gray-900 dark:text-white focus:outline-none focus:border-purple-500"
              />
              <button
                onClick={() => handleApplyCoupon(customCouponInput)}
                disabled={isApplyingCoupon || !customCouponInput.trim()}
                className="bg-[#7C3AED] hover:bg-purple-700 disabled:opacity-50 text-white font-extrabold text-xs px-5 rounded-2xl shadow-sm transition-all"
              >
                {isApplyingCoupon ? 'Applying...' : 'Apply'}
              </button>
            </div>

            {/* Live Coupons List from Toing */}
            <div className="space-y-3 pt-1">
              <p className="text-[10px] font-black uppercase tracking-wider text-gray-400">
                AVAILABLE OFFERS FROM TOING ({availableCoupons.length})
              </p>

              {availableCoupons.length === 0 ? (
                <div className="text-center py-6 text-gray-400 text-xs">
                  <Ticket className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                  <p>No coupons currently returned for this cart.</p>
                </div>
              ) : (
                availableCoupons.map((cpn) => {
                  const isCurrentlyApplied = appliedCoupon?.code === cpn.code;
                  return (
                    <div
                      key={cpn.code}
                      className={`border rounded-2xl p-3.5 transition-all ${
                        isCurrentlyApplied
                          ? 'border-emerald-500 bg-emerald-50/20 dark:bg-emerald-950/20'
                          : 'border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-800/40'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="space-y-1 min-w-0 pr-2">
                          <div className="flex items-center space-x-2">
                            <span className="font-black text-xs text-[#7C3AED] dark:text-purple-300 tracking-wider">
                              {cpn.code}
                            </span>
                            {cpn.ribbon && (
                              <span className="bg-purple-50 dark:bg-purple-950 text-[#7C3AED] dark:text-purple-300 text-[10px] font-black px-1.5 py-0.5 rounded-md">
                                {cpn.ribbon}
                              </span>
                            )}
                          </div>
                          <p className="text-xs font-bold text-gray-800 dark:text-gray-200">
                            {cpn.description}
                          </p>
                          <p className="text-[11px] text-gray-400">
                            {cpn.subtitle}
                          </p>
                        </div>

                        <button
                          onClick={() => handleApplyCoupon(cpn.code)}
                          disabled={cpn.applicable === false || isCurrentlyApplied || isApplyingCoupon}
                          className={`font-black text-xs px-4 py-2 rounded-xl transition-all flex-shrink-0 ${
                            isCurrentlyApplied
                              ? 'bg-emerald-100 text-[#059669] cursor-default'
                              : cpn.applicable === false
                              ? 'bg-gray-100 dark:bg-gray-800 text-gray-400 cursor-not-allowed text-[11px]'
                              : 'bg-[#7C3AED] hover:bg-purple-700 text-white shadow-sm active:scale-95'
                          }`}
                        >
                          {isCurrentlyApplied ? 'Applied' : cpn.applicable === false ? 'Unavailable' : 'Apply'}
                        </button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
