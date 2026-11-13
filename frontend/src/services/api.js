import axios from 'axios';
import WebApp from '@twa-dev/sdk';

const API_BASE = import.meta.env.VITE_API_BASE || '/api';

const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

let currentActiveAccount = null;

export const setActiveAccountHeader = (account) => {
  currentActiveAccount = account;
};

// Extracts or generates the Telegram User ID
export const getTelegramUserId = () => {
  try {
    const user = WebApp?.initDataUnsafe?.user;
    if (user?.id) {
      return String(user.id);
    }
  } catch (e) {}

  // Outside Telegram (development / browser testing fallback)
  let devId = localStorage.getItem('toing_dev_telegram_id');
  if (!devId || devId.startsWith('dev_user_')) {
    devId = '987654321';
    localStorage.setItem('toing_dev_telegram_id', devId);
  }
  return devId;
};

// Request interceptor to attach Telegram WebApp initData, Telegram User ID, and Active Account headers
apiClient.interceptors.request.use((config) => {
  const initData = WebApp?.initData || '';
  const tgUserId = getTelegramUserId();

  if (initData) {
    config.headers['X-Telegram-Init-Data'] = initData;
    // Standard Telegram Mini App authorization header
    config.headers['Authorization'] = `tma ${initData}`;
  }
  config.headers['X-Telegram-Id'] = tgUserId;

  if (!config.headers['x-user-key']) {
    config.headers['x-user-key'] = 'TNG-EMJ9-SATT-NVHL';
  }

  // Inject session headers from the real activeAccount
  if (currentActiveAccount) {
    if (currentActiveAccount.tid) {
      config.headers['Authorization'] = currentActiveAccount.tid.startsWith('Bearer ')
        ? currentActiveAccount.tid
        : `Bearer ${currentActiveAccount.tid}`;
    }
    if (currentActiveAccount.token) {
      config.headers['x-auth-token'] = currentActiveAccount.token;
    }
    if (currentActiveAccount.sid) {
      config.headers['x-session-id'] = currentActiveAccount.sid;
    }
    if (currentActiveAccount.mobile) {
      config.headers['X-Active-Mobile'] = currentActiveAccount.mobile;
    }
    if (currentActiveAccount.access_key) {
      config.headers['x-user-key'] = currentActiveAccount.access_key;
    }
  }

  return config;
});

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    return Promise.reject(error);
  }
);

export const api = {
  // Auth & Accounts
  jsonLogin: (credentials) => apiClient.post('/login/json', credentials),
  getSavedAccounts: async () => {
    try {
      const res = await apiClient.get('/sessions');
      if (res && res.sessions) {
        return {
          success: true,
          count: res.sessions.length,
          accounts: res.sessions.map((s, idx) => ({
            id: s.mobile || String(idx),
            mobile: s.mobile,
            phone: `+91 ${s.mobile}`,
            name: s.name && s.name.trim() ? s.name.trim() : `User ${s.mobile ? s.mobile.slice(-4) : idx}`,
            status: s.is_expired ? 'used' : (s.status || 'fresh'),
            is_expired: !!s.is_expired,
            tid: s.tid || '',
            token: s.token || '',
            sid: s.sid || '',
            deviceId: s.deviceId || s.android_id || '',
            customerId: s.customerId || s.user_id || ''
          }))
        };
      }
      return res;
    } catch (e) {
      return apiClient.get('/auth/accounts');
    }
  },
  toggleAccountStatus: (id) => apiClient.post('/auth/toggle-status', { id }),
  deleteAccount: (id) => apiClient.delete(`/auth/accounts/${id}`),

  validateWebapp: (initData) => apiClient.post('/auth/validate_webapp', { init_data: initData }),
  getWallet: () => apiClient.get('/me'),
  getSessions: () => apiClient.get('/sessions'),
  switchSession: (mobile) => apiClient.post('/auth/switch-session', { mobile }),
  getAddresses: async (mobile, force = false) => {
    if (mobile) {
      return apiClient.get(`/addresses/${mobile}`, { params: { force } });
    }
    return apiClient.get('/addresses', { params: { force } });
  },
  addAddress: (payload) => apiClient.post('/addresses/add', payload),
  deleteAddress: (id, mobile) => apiClient.post('/addresses/delete', { id, mobile }),
  saveAddressLink: (link, mobile) => apiClient.post('/addresses/add_link', { link, mobile }),
  addAddressLink: (link, mobile) => apiClient.post('/addresses/add_link', { link, mobile }),
  reverseGeocode: (lat, lng, mobile) => apiClient.get('/location/reverse', { params: { lat, lng, mobile } }),

  // Orders & Checkout
  getOrders: (mobile) => apiClient.get('/orders_recent', { params: { mobile } }),
  getBestCoupon: (payload) => apiClient.post('/checkout/best_coupon', payload),
  fetchCoupons: (payload) => apiClient.post('/checkout/coupons', payload),
  applyCoupon: (payload) => apiClient.post('/checkout/apply_coupon', payload),
  getPaymentOptions: (payload) => apiClient.post('/checkout/payment_options', payload),
  placeOrder: (payload) => apiClient.post('/checkout/place', payload),
  getPaymentStatus: (payload) => apiClient.post('/checkout/payment_status', payload),
  getOrderStatus: (payload) => apiClient.post('/checkout/order_status', payload),
  sendPaylog: (payload) => apiClient.post('/paylog', payload),
  getRecentOrders: (minutes = 60, live = false) => apiClient.get('/orders_recent', { params: { minutes, live } }),
  getOrderDetail: (mobile, orderId) => apiClient.get(`/order_detail/${mobile}/${orderId}`),

  // Catalog & Search
  search: (q, lat = 28.4543533, lng = 77.5015833, mobile = '') =>
    apiClient.get('/search/restaurants', { params: { q, lat, lng, mobile } }),
  searchRestaurants: (q, lat = 28.4543533, lng = 77.5015833) =>
    apiClient.get('/search/restaurants', { params: { q, lat, lng } }),
  getMenu: (restaurantId, query = '', metadata = '', lat = 28.4543533, lng = 77.5015833, mobile = '') =>
    apiClient.post('/search/menu', { restaurant_id: restaurantId, query, metadata, lat, lng, mobile }),
  getOutlets: (restaurantId, lat = 28.4543533, lng = 77.5015833, mobile = '') =>
    apiClient.post('/search/outlets', { restaurant_id: restaurantId, lat, lng, mobile }),
  searchMenuItems: (restaurantId, query, veg = false, lat = 28.4543533, lng = 77.5015833, mobile = '') =>
    apiClient.post('/search/menu_search', { restaurant_id: restaurantId, query, veg, lat, lng, mobile }),

  // Cart
  calculateCart: (payload) => apiClient.post('/search/cart', payload),
  addAddressToAccount: (payload) => apiClient.post('/cart/add_address_to_account', payload),
  getCartState: () => apiClient.get('/cart/state'),
  syncCartState: (cart, loc) => apiClient.put('/cart/state', { cart, loc }),
};

export default apiClient;
