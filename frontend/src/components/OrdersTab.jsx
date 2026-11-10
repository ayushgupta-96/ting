import React, { useState, useEffect } from 'react';
import { 
  ShoppingBag, 
  RefreshCw, 
  Receipt, 
  Clock, 
  ExternalLink, 
  Utensils, 
  Loader2, 
  Phone, 
  User, 
  CheckCircle2, 
  ChevronDown, 
  ChevronUp, 
  MapPin,
  Sparkles
} from 'lucide-react';
import { api } from '../services/api';

const getOrderStage = (statusStr) => {
  const s = (statusStr || '').toLowerCase();
  if (s.includes('delivered')) return 4;
  if (s.includes('out') || s.includes('picked') || s.includes('way') || s.includes('reach')) return 3;
  if (s.includes('prepar') || s.includes('cook') || s.includes('kitchen')) return 2;
  return 1; // 'received', 'placed', 'confirmed', 'processing'
};

const OrderStepper = ({ stage }) => {
  const steps = [
    { label: 'Placed', icon: '📦' },
    { label: 'Preparing', icon: '🍳' },
    { label: 'On Way', icon: '🛵' },
    { label: 'Delivered', icon: '🏠' },
  ];

  return (
    <div className="py-2.5 px-2">
      <div className="flex items-center justify-between relative">
        <div className="absolute top-3.5 left-4 right-4 h-1 bg-gray-200 dark:bg-gray-700 z-0" />
        <div
          className="absolute top-3.5 left-4 h-1 bg-[#059669] z-0 transition-all duration-500"
          style={{ width: `${Math.min(100, Math.max(0, (stage - 1) * 33.33))}%` }}
        />
        {steps.map((st, i) => {
          const stepNum = i + 1;
          const isDone = stepNum <= stage;
          const isCurrent = stepNum === stage;
          return (
            <div key={st.label} className="relative z-10 flex flex-col items-center">
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center text-xs transition-all shadow-sm ${
                  isDone
                    ? 'bg-[#059669] text-white ring-2 ring-emerald-200 dark:ring-emerald-900'
                    : 'bg-white dark:bg-gray-800 text-gray-400 border border-gray-200 dark:border-gray-700'
                } ${isCurrent && stage < 4 ? 'animate-bounce' : ''}`}
              >
                <span>{st.icon}</span>
              </div>
              <span
                className={`text-[10px] font-extrabold mt-1.5 ${
                  isDone ? 'text-[#059669] dark:text-emerald-400' : 'text-gray-400'
                }`}
              >
                {st.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default function OrdersTab({ activeAccount, onShowToast }) {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filterMode, setFilterMode] = useState('account'); // 'account' | 'recent'
  const [refreshingOrderId, setRefreshingOrderId] = useState(null);
  const [expandedOrders, setExpandedOrders] = useState({});

  const toggleExpand = (id) => {
    setExpandedOrders((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const fetchOrders = async () => {
    setLoading(true);
    try {
      if (filterMode === 'recent') {
        const res = await api.getRecentOrders(60, false);
        const list = res?.orders || [];
        setOrders(list.map((o) => ({
          id: String(o.order_id || o.id),
          order_id: String(o.order_id || o.id),
          restaurant_name: o.restaurant_name || o.restaurant || 'Toing Restaurant',
          area: o.address?.area || o.area || '',
          amount: o.order_total || o.amount || 0,
          status: o.order_status || o.status || 'Order Received!',
          items_text: o.items_text || '',
          tracking_link: o.tracking_link || '',
          created_at: o.order_time || o.created_at || null,
          de_name: o.de_name || null,
          de_phone: o.de_phone || null,
        })));
      } else {
        if (!activeAccount?.mobile) {
          setOrders([]);
          return;
        }
        const res = await api.getOrders(activeAccount.mobile);
        const list = res?.orders || [];
        setOrders(list.map((o) => ({
          id: String(o.order_id || o.id),
          order_id: String(o.order_id || o.id),
          restaurant_name: o.restaurant_name || o.restaurant || 'Toing Restaurant',
          area: o.area || '',
          amount: o.order_total || o.amount || 0,
          status: o.order_status || o.status || 'Order Received!',
          items_text: o.items_text || '',
          tracking_link: o.tracking_link || '',
          created_at: o.order_time || o.created_at || null,
          de_name: o.de_name || null,
          de_phone: o.de_phone || null,
        })));
      }
    } catch (err) {
      console.error('Failed to fetch orders:', err);
      setOrders([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrders();
  }, [filterMode, activeAccount?.mobile]);

  // Single Order Live Status Refresher (calling upstream order_detail endpoint)
  const handleRefreshSingleOrder = async (orderId) => {
    const mobile = activeAccount?.mobile || '';
    if (!mobile || !orderId) return;

    setRefreshingOrderId(orderId);
    try {
      const detail = await api.getOrderDetail(mobile, orderId);
      if (detail && (detail.status || detail.status_label)) {
        const newStatus = detail.status_label || detail.status;
        setOrders((prev) =>
          prev.map((ord) => {
            if (ord.order_id === orderId) {
              return {
                ...ord,
                status: newStatus,
                de_name: detail.de_name || ord.de_name,
                de_phone: detail.de_phone || ord.de_phone,
                tracking_link: detail.tracking_link || ord.tracking_link,
                restaurant_name: detail.restaurant || ord.restaurant_name,
              };
            }
            return ord;
          })
        );
        if (onShowToast) {
          onShowToast('success', `Live status: ${newStatus}`);
        }
      } else {
        if (onShowToast) onShowToast('info', 'Order status checked: No changes.');
      }
    } catch (e) {
      console.error('Failed to fetch order detail:', e);
      if (onShowToast) onShowToast('error', 'Unable to refresh live status.');
    } finally {
      setRefreshingOrderId(null);
    }
  };

  return (
    <div className="space-y-4 pb-24 animate-fade-in">
      {/* Top Filter Pills Card */}
      <div className="bg-white dark:bg-[#1E293B] rounded-3xl p-1.5 shadow-card border border-gray-100 dark:border-gray-800 flex items-center justify-between">
        <button
          type="button"
          onClick={() => setFilterMode('account')}
          className={`flex-1 flex items-center justify-center space-x-2 py-2.5 rounded-2xl text-xs font-bold transition-all ${
            filterMode === 'account'
              ? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm ring-1 ring-gray-200 dark:ring-gray-700'
              : 'text-gray-500 hover:text-gray-700 dark:text-gray-400'
          }`}
        >
          <Receipt className="w-4 h-4 text-[#7C3AED]" />
          <span>This Account</span>
        </button>

        <button
          type="button"
          onClick={() => setFilterMode('recent')}
          className={`flex-1 flex items-center justify-center space-x-2 py-2.5 rounded-2xl text-xs font-bold transition-all ${
            filterMode === 'recent'
              ? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm ring-1 ring-gray-200 dark:ring-gray-700'
              : 'text-gray-500 hover:text-gray-700 dark:text-gray-400'
          }`}
        >
          <Clock className="w-4 h-4 text-gray-400" />
          <span>Last 1 Hour</span>
        </button>
      </div>

      {/* Orders Body */}
      {loading ? (
        <div className="py-24 flex flex-col items-center justify-center space-y-3 text-gray-400 text-xs">
          <Loader2 className="w-8 h-8 animate-spin text-[#7C3AED]" />
          <span>Checking orders from Toing...</span>
        </div>
      ) : orders.length === 0 ? (
        /* Empty State */
        <div className="py-20 flex flex-col items-center justify-center text-center px-4">
          <div className="w-16 h-16 rounded-full bg-[#F3E8FF] dark:bg-purple-950/60 flex items-center justify-center text-[#7C3AED] dark:text-purple-400 mb-4 shadow-inner">
            <ShoppingBag className="w-7 h-7 stroke-[2.2]" />
          </div>

          <h2 className="text-base font-black text-gray-900 dark:text-white tracking-tight">
            No Orders Found
          </h2>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 max-w-xs">
            {filterMode === 'recent'
              ? 'No orders placed in the last hour.'
              : 'This account has no completed orders.'}
          </p>

          <button
            onClick={fetchOrders}
            className="mt-6 inline-flex items-center space-x-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 hover:border-purple-300 text-gray-800 dark:text-gray-200 px-4 py-2 rounded-2xl text-xs font-bold shadow-sm active:scale-95 transition-all"
          >
            <RefreshCw className="w-3.5 h-3.5 text-[#7C3AED]" />
            <span>Refresh</span>
          </button>
        </div>
      ) : (
        /* Real Orders List (Fully synchronized from Toing) */
        <div className="space-y-3.5">
          {orders.map((order) => {
            const isDelivered = (order.status || '').toLowerCase().includes('delivered');
            const stage = getOrderStage(order.status);
            const isRefreshing = refreshingOrderId === order.order_id;
            const isExpanded = expandedOrders[order.id] !== false; // Default expanded for clear visibility

            return (
              <div
                key={order.id}
                className="bg-white dark:bg-[#1E293B] rounded-3xl p-4 border border-gray-100 dark:border-gray-800 shadow-card space-y-3"
              >
                {/* Header: Restaurant + Status */}
                <div className="flex items-start justify-between space-x-2">
                  <div className="min-w-0">
                    <h3 className="font-extrabold text-sm text-gray-900 dark:text-white truncate">
                      {order.restaurant_name}
                    </h3>
                    {order.area && (
                      <p className="text-[11px] text-gray-400 truncate flex items-center space-x-1">
                        <MapPin className="w-3 h-3 text-red-500 inline mr-0.5 flex-shrink-0" />
                        <span>{order.area}</span>
                      </p>
                    )}
                  </div>
                  <div className="flex items-center space-x-1.5 flex-shrink-0">
                    <span
                      className={`text-[10px] font-black uppercase px-2.5 py-1 rounded-full border flex-shrink-0 ${
                        isDelivered
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300'
                          : 'bg-emerald-50 text-emerald-600 border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300'
                      }`}
                    >
                      {order.status}
                    </span>
                    <button
                      type="button"
                      onClick={() => toggleExpand(order.id)}
                      className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                    >
                      {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {/* Live 4-Step Tracking Stepper (Feature 5) */}
                <div className="bg-gray-50/70 dark:bg-gray-800/40 rounded-2xl p-2 border border-gray-100 dark:border-gray-800/60">
                  <OrderStepper stage={stage} />
                </div>

                {isExpanded && (
                  <div className="space-y-3 pt-1 animate-fade-in">
                    {/* Delivery Executive Details Card (if available) */}
                    {(order.de_name || order.de_phone) && (
                      <div className="bg-emerald-50/70 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800/80 rounded-2xl p-2.5 flex items-center justify-between">
                        <div className="flex items-center space-x-2.5 min-w-0">
                          <div className="w-8 h-8 rounded-xl bg-[#059669] text-white flex items-center justify-center flex-shrink-0 shadow-sm">
                            <User className="w-4 h-4" />
                          </div>
                          <div className="min-w-0">
                            <p className="text-[9px] font-black uppercase tracking-wider text-emerald-700 dark:text-emerald-300">
                              Delivery Partner
                            </p>
                            <h4 className="font-extrabold text-xs text-gray-900 dark:text-white truncate">
                              {order.de_name || 'Delivery Executive Assigned'}
                            </h4>
                          </div>
                        </div>
                        {order.de_phone && (
                          <a
                            href={`tel:${order.de_phone}`}
                            className="bg-[#059669] hover:bg-emerald-700 active:scale-95 text-white font-black text-xs px-3 py-1.5 rounded-xl shadow-sm flex items-center space-x-1.5 flex-shrink-0 ml-2"
                          >
                            <Phone className="w-3 h-3" />
                            <span>Call</span>
                          </a>
                        )}
                      </div>
                    )}

                    {/* Items Summary */}
                    {order.items_text && (
                      <div className="bg-gray-50 dark:bg-gray-800/60 rounded-2xl p-2.5 flex items-start space-x-2 text-xs text-gray-700 dark:text-gray-300">
                        <Utensils className="w-3.5 h-3.5 text-[#7C3AED] mt-0.5 flex-shrink-0" />
                        <span className="leading-snug">{order.items_text}</span>
                      </div>
                    )}
                  </div>
                )}

                {/* Footer: Order ID, Amount, Time & Action Buttons */}
                <div className="pt-2 border-t border-gray-100 dark:border-gray-800/80 flex items-center justify-between text-xs">
                  <div className="min-w-0">
                    <p className="font-bold text-gray-400 text-[11px]">
                      Order #{order.order_id}
                    </p>
                    {order.created_at && (
                      <p className="text-[10px] text-gray-400">
                        {order.created_at}
                      </p>
                    )}
                  </div>

                  <div className="flex items-center space-x-2">
                    <span className="font-black text-sm text-gray-900 dark:text-white mr-1">
                      ₹{order.amount}
                    </span>

                    {/* Refresh Status Button */}
                    <button
                      type="button"
                      onClick={() => handleRefreshSingleOrder(order.order_id)}
                      disabled={isRefreshing}
                      className="bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 text-gray-700 dark:text-gray-300 p-2 rounded-xl active:scale-95 transition-all flex items-center justify-center flex-shrink-0"
                      title="Refresh Live Status"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-[#7C3AED]' : ''}`} />
                    </button>

                    {/* Live Tracking Link */}
                    {order.tracking_link && (
                      <a
                        href={order.tracking_link}
                        target="_blank"
                        rel="noreferrer"
                        className="bg-purple-50 dark:bg-purple-950/80 text-[#7C3AED] dark:text-purple-300 font-extrabold text-[11px] px-3 py-1.5 rounded-xl hover:bg-purple-100 transition-colors inline-flex items-center space-x-1 flex-shrink-0"
                      >
                        <span>Track</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
