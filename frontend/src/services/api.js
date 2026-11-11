import axios from 'axios';
import WebApp from '@twa-dev/sdk';

const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1';

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

// Response interceptor for session expiration
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const isCatalogOrSearch = error.config?.url?.includes('/search') || error.config?.url?.includes('/catalog') || error.config?.url?.includes('/menu');
    if ((error.response?.status === 401 || error.response?.status === 403) && !isCatalogOrSearch) {
      const isCriticalAction = error.config?.url?.includes('/checkout') || error.config?.url?.includes('/order');
      if (isCriticalAction) {
        try {
          if (WebApp?.isVersionAtLeast && WebApp.isVersionAtLeast('6.2') && typeof WebApp.showAlert === 'function') {
            WebApp.showAlert('Session expired or unauthorized. Please login again.');
          }
        } catch (e) {}
      }
    }
    return Promise.reject(error);
  }
);

export const api = {
  // Auth & Accounts
  sendOtp: (mobile) => apiClient.post('/auth/send-otp', { mobile }),
  verifyOtp: (payload) => apiClient.post('/auth/verify-otp', payload),
  jsonLogin: (credentials) => apiClient.post('/auth/json-login', credentials),
  getSavedAccounts: () => apiClient.get('/auth/accounts'),
  toggleAccountStatus: (id) => apiClient.post('/auth/toggle-status', { id }),
  deleteAccount: (id) => apiClient.delete(`/auth/accounts/${id}`),

  validateWebapp: (initData) => apiClient.post('/auth/validate', { init_data: initData }),
  getWallet: () => apiClient.get('/auth/me'),
  getSessions: () => apiClient.get('/auth/sessions'),
  switchSession: (mobile) => apiClient.post('/auth/switch-session', { mobile }),
  getAddresses: (mobile, force = false) => apiClient.get('/addresses', { params: { mobile, force } }),
  addAddress: (payload) => apiClient.post('/addresses', payload),
  deleteAddress: (id) => apiClient.delete(`/addresses/${id}`),
  saveAddressLink: (link, mobile) => apiClient.post('/addresses/add_link', { link, mobile }),
  addAddressLink: (link, mobile) => apiClient.post('/addresses/add_link', { link, mobile }),
  reverseGeocode: (lat, lng, mobile) => apiClient.get('/location/reverse', { params: { lat, lng, mobile } }),

  // Orders & Checkout
  getOrders: (mobile) => apiClient.get('/orders', { params: { mobile } }),
  getBestCoupon: (payload) => apiClient.post('/checkout/best_coupon', payload),
  applyCoupon: (payload) => apiClient.post('/checkout/apply_coupon', payload),
  getPaymentOptions: (payload) => apiClient.post('/checkout/payment_options', payload),
  placeOrder: (payload) => apiClient.post('/checkout/place', payload),
  getPaymentStatus: (payload) => apiClient.post('/checkout/payment_status', payload),
  getOrderStatus: (payload) => apiClient.post('/checkout/order_status', payload),
  sendPaylog: (payload) => apiClient.post('/checkout/paylog', payload),
  getRecentOrders: (minutes = 60, live = false) => apiClient.get('/orders_recent', { params: { minutes, live } }),
  getOrderDetail: (mobile, orderId) => apiClient.get(`/order_detail/${mobile}/${orderId}`),

  // Catalog & Search
  search: (q, lat = 28.458901, lng = 77.497186, mobile = '') =>
    apiClient.get('/search', { params: { q, lat, lng, mobile } }),
  searchRestaurants: (q, lat = 28.458901, lng = 77.497186) =>
    apiClient.get('/search', { params: { q, lat, lng } }),
  getMenu: (restaurantId, query = '', metadata = '', lat = 28.458901, lng = 77.497186, mobile = '') =>
    apiClient.post('/menu', { restaurant_id: restaurantId, query, metadata, lat, lng, mobile }),
  getOutlets: (restaurantId, lat = 28.458901, lng = 77.497186, mobile = '') =>
    apiClient.post('/outlets', { restaurant_id: restaurantId, lat, lng, mobile }),
  searchMenuItems: (restaurantId, query, veg = false, lat = 28.458901, lng = 77.497186, mobile = '') =>
    apiClient.post('/menu-search', { restaurant_id: restaurantId, query, veg, lat, lng, mobile }),

  // Cart
  calculateCart: (payload) => apiClient.post('/cart/calculate', payload),
  addAddressToAccount: (payload) => apiClient.post('/cart/add_address_to_account', payload),
  getCartState: () => apiClient.get('/cart/state'),
  syncCartState: (cart, loc) => apiClient.put('/cart/state', { cart, loc }),
};

export default apiClient;
