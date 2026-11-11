import React, { useState, useEffect } from 'react';
import WebApp from '@twa-dev/sdk';
import TopBar from './components/TopBar';
import BottomNav from './components/BottomNav';
import AccountsTab from './components/AccountsTab';
import AddressTab from './components/AddressTab';
import SearchTab from './components/SearchTab';
import CartTab from './components/CartTab';
import OrdersTab from './components/OrdersTab';
import SwitchAccountModal from './components/SwitchAccountModal';
import SelectLocationModal from './components/SelectLocationModal';
import ReplaceCartModal from './components/ReplaceCartModal';
import Toast from './components/Toast';
import { api, setActiveAccountHeader, getTelegramUserId } from './services/api';

export default function App() {
  // Telegram WebApp setup
  useEffect(() => {
    try {
      WebApp.ready();
      WebApp.expand();
      if (WebApp.headerColor) {
        WebApp.setHeaderColor('#FFFFFF');
      }
    } catch (e) {
      console.log('Running outside Telegram environment');
    }
  }, []);

  // Toast Notification State
  const [toast, setToast] = useState(null);

  const showToast = (type, message) => {
    setToast({ type, message });
    try {
      if (type === 'error' && WebApp?.HapticFeedback) {
        WebApp.HapticFeedback.notificationOccurred('error');
      } else if (type === 'success' && WebApp?.HapticFeedback) {
        WebApp.HapticFeedback.notificationOccurred('success');
      }
    } catch (e) {
      // ignore
    }
    setTimeout(() => {
      setToast((cur) => (cur?.message === message ? null : cur));
    }, 3500);
  };

  // Dark Mode State
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem('toing_dark_mode');
    if (saved !== null) return saved === 'true';
    return WebApp?.colorScheme === 'dark';
  });

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    localStorage.setItem('toing_dark_mode', String(darkMode));
  }, [darkMode]);

  // Telegram User Scoped Storage Keys
  const tgUserId = getTelegramUserId();
  const accountStorageKey = `activeAccount_${tgUserId}`;
  const cartStorageKey = `toing_cart_${tgUserId}`;
  const restaurantStorageKey = `toing_selected_restaurant_${tgUserId}`;
  const addressStorageKey = `toing_active_address_${tgUserId}`;
  const tabStorageKey = `toing_active_tab_${tgUserId}`;

  // Tab State: Persistent across reloads and external app switches
  const [activeTab, setActiveTab] = useState(() => {
    try {
      const savedTab = localStorage.getItem(`toing_active_tab_${getTelegramUserId()}`);
      if (savedTab && ['accounts', 'address', 'search', 'cart', 'orders'].includes(savedTab)) {
        return savedTab;
      }
    } catch (e) {}
    return 'accounts';
  });

  useEffect(() => {
    try {
      localStorage.setItem(tabStorageKey, activeTab);
    } catch (e) {}
  }, [activeTab, tabStorageKey]);

  // Global Auth State (Initialized from scoped localStorage if available)
  const [activeAccount, setActiveAccount] = useState(() => {
    try {
      const saved = localStorage.getItem(accountStorageKey);
      if (!saved) return null;
      try {
        return JSON.parse(saved);
      } catch (e) {
        return { mobile: saved, phone: `+91 ${saved}` };
      }
    } catch (e) {
      return null;
    }
  });

  // Active Selected Delivery Address (Global State for Cart & Search, scoped to Telegram user)
  const [activeAddress, setActiveAddress] = useState(() => {
    try {
      const saved = localStorage.getItem(addressStorageKey);
      return saved ? JSON.parse(saved) : null;
    } catch (e) {
      return null;
    }
  });

  // Active Selected Restaurant (Global State for Search and Cart, scoped to Telegram user)
  const [selectedRestaurant, setSelectedRestaurant] = useState(() => {
    try {
      const saved = localStorage.getItem(restaurantStorageKey);
      return saved ? JSON.parse(saved) : null;
    } catch (e) {
      return null;
    }
  });

  // Active Cart Items (Global state shared across Search and Cart, scoped to Telegram user)
  const [cartLines, setCartLines] = useState(() => {
    try {
      const saved = localStorage.getItem(cartStorageKey);
      return saved ? JSON.parse(saved) : [];
    } catch (e) {
      return [];
    }
  });

  // Persist cartLines to localStorage (Fast, zero network lag client-side synchronization)
  useEffect(() => {
    try {
      localStorage.setItem(cartStorageKey, JSON.stringify(cartLines));
    } catch (e) {}
  }, [cartLines, cartStorageKey]);

  // Persist selectedRestaurant to localStorage
  useEffect(() => {
    try {
      if (selectedRestaurant) {
        localStorage.setItem(restaurantStorageKey, JSON.stringify(selectedRestaurant));
      } else {
        localStorage.removeItem(restaurantStorageKey);
      }
    } catch (e) {}
  }, [selectedRestaurant, restaurantStorageKey]);

  // Persist activeAddress to localStorage
  useEffect(() => {
    try {
      if (activeAddress) {
        localStorage.setItem(addressStorageKey, JSON.stringify(activeAddress));
      } else {
        localStorage.removeItem(addressStorageKey);
      }
    } catch (e) {}
  }, [activeAddress, addressStorageKey]);

  // Accounts list (Fetched from real DB API, strictly zero dummy items)
  const [accounts, setAccounts] = useState([]);
  const [accountsLoading, setAccountsLoading] = useState(false);

  // Switch Account Modal State
  const [isSwitchModalOpen, setIsSwitchModalOpen] = useState(false);

  // Select Location Bottom Sheet Modal State (Screenshot 3)
  const [isLocationModalOpen, setIsLocationModalOpen] = useState(false);

  // Replace Cart Modal State (Enforcing Single Restaurant per Cart business rule)
  const [conflictItem, setConflictItem] = useState(null);

  // Sync API Client headers with activeAccount
  useEffect(() => {
    setActiveAccountHeader(activeAccount);
  }, [activeAccount]);

  // Fetch real saved accounts from backend strictly for this Telegram User
  const loadSavedAccounts = async () => {
    setAccountsLoading(true);
    try {
      const res = await api.getSavedAccounts();
      const serverAccounts = res?.accounts || [];
      setAccounts(serverAccounts);

      if (serverAccounts.length === 0) {
        // Fresh Start: Completely empty state for new user
        setActiveAccount(null);
        setActiveAddress(null);
        setSelectedRestaurant(null);
        setCartLines([]);
        localStorage.removeItem(accountStorageKey);
        localStorage.removeItem(cartStorageKey);
        localStorage.removeItem(restaurantStorageKey);
        localStorage.removeItem(addressStorageKey);
      } else {
        // Scoped restoration of active account for existing user
        const savedAccountRef = localStorage.getItem(accountStorageKey);
        let savedMobileOrId = '';
        if (savedAccountRef) {
          try {
            const parsed = JSON.parse(savedAccountRef);
            savedMobileOrId = parsed?.mobile || parsed?.id || '';
          } catch (e) {
            savedMobileOrId = savedAccountRef;
          }
        }
        const existing = serverAccounts.find(
          (a) => a.mobile === savedMobileOrId || String(a.id) === savedMobileOrId
        );
        const selected = existing || serverAccounts[0];
        setActiveAccount(selected);
        localStorage.setItem(accountStorageKey, JSON.stringify(selected));
      }
    } catch (err) {
      console.error('Failed to load accounts from API:', err);
      // Keep existing activeAccount from localStorage if network fails temporarily
    } finally {
      setAccountsLoading(false);
    }
  };

  useEffect(() => {
    loadSavedAccounts();
  }, []);

  // TAB ROUTING GUARD (AUTH PROTECTION)
  // If activeAccount is null, force active tab to 'accounts' and show alert
  useEffect(() => {
    if (!activeAccount && activeTab !== 'accounts') {
      setActiveTab('accounts');
      showToast('error', 'Please login to an account first.');
    }
  }, [activeAccount, activeTab]);

  const handleTabSelect = (tabId) => {
    if (!activeAccount && tabId !== 'accounts') {
      showToast('error', 'Please login to an account first.');
      setActiveTab('accounts');
      return;
    }

    if (tabId === 'search' && !activeAddress) {
      setIsLocationModalOpen(true);
      showToast('info', 'Please select a delivery address before searching.');
      setActiveTab('search');
      return;
    }

    setActiveTab(tabId);
  };

  // Login with JSON Handler
  const handleLoginJson = async (credentials) => {
    const res = await api.jsonLogin(credentials);
    if (res && res.success && res.account) {
      setActiveAccount(res.account);
      localStorage.setItem(accountStorageKey, JSON.stringify(res.account));
      await loadSavedAccounts();
      return res;
    }
    return res;
  };

  // Account Selection & Operations
  const handleSelectAccount = (acc) => {
    setActiveAccount(acc);
    localStorage.setItem(accountStorageKey, JSON.stringify(acc));
    showToast('success', `Active account: ${acc.name || acc.phone || acc.mobile}`);
  };

  const handleToggleStatus = async (accId) => {
    try {
      await api.toggleAccountStatus(accId);
      await loadSavedAccounts();
      if (activeAccount && (activeAccount.id === accId || activeAccount.mobile === accId)) {
        setActiveAccount((prev) => ({
          ...prev,
          status: prev.status === 'fresh' ? 'used' : 'fresh',
        }));
      }
    } catch (err) {
      showToast('error', 'Failed to toggle account status');
    }
  };

  const handleDeleteAccount = async (accId) => {
    try {
      await api.deleteAccount(accId);
      const res = await api.getSavedAccounts();
      const serverAccounts = res?.accounts || [];
      setAccounts(serverAccounts);

      if (activeAccount && (activeAccount.id === accId || activeAccount.mobile === accId)) {
        if (serverAccounts.length > 0) {
          const nextAcc = serverAccounts[0];
          setActiveAccount(nextAcc);
          localStorage.setItem(accountStorageKey, nextAcc.mobile || nextAcc.id);
        } else {
          setActiveAccount(null);
          setActiveAddress(null);
          setSelectedRestaurant(null);
          setCartLines([]);
          localStorage.removeItem(accountStorageKey);
          localStorage.removeItem(cartStorageKey);
          localStorage.removeItem(restaurantStorageKey);
          localStorage.removeItem(addressStorageKey);
        }
        showToast('error', 'Active account deleted.');
      } else {
        showToast('success', 'Account removed');
      }
    } catch (err) {
      showToast('error', 'Failed to delete account');
    }
  };

  const handleSendOtp = async (phone) => {
    return await api.sendOtp(phone);
  };

  const handleVerifyOtp = async (payload) => {
    const res = await api.verifyOtp(payload);
    if (res && res.success && res.account) {
      setActiveAccount(res.account);
      localStorage.setItem(accountStorageKey, JSON.stringify(res.account));
      await loadSavedAccounts();
      return res;
    }
    return res;
  };

  // Cart Operations (Strict Toing / Swiggy Food Ordering Business Rules)
  const handleAddToCart = (item) => {
    // Single Restaurant Validation
    if (cartLines.length > 0) {
      const existingRest = cartLines[0]?.restaurant;
      const newRest = item.restaurant;
      if (
        existingRest?.id &&
        newRest?.id &&
        String(existingRest.id) !== String(newRest.id)
      ) {
        // Conflicting restaurant detected: prompt user to replace cart
        setConflictItem(item);
        return;
      }
    }

    setCartLines((prev) => {
      const existing = prev.find((l) => l.id === item.id);
      if (existing) {
        return prev.map((l) =>
          l.id === item.id ? { ...l, quantity: l.quantity + 1 } : l
        );
      }
      return [...prev, { ...item, quantity: 1 }];
    });
    showToast('success', `Added ${item.name} to cart`);
  };

  const handleConfirmReplaceCart = () => {
    if (!conflictItem) return;
    const newRest = conflictItem.restaurant || null;
    setCartLines([{ ...conflictItem, quantity: 1 }]);
    setSelectedRestaurant(newRest);
    showToast('info', `Cart updated with dishes from ${newRest?.name || 'new restaurant'}`);
    setConflictItem(null);
  };

  const handleCancelReplaceCart = () => {
    setConflictItem(null);
  };

  const handleRemoveFromCart = (itemId) => {
    setCartLines((prev) =>
      prev
        .map((l) => (l.id === itemId ? { ...l, quantity: l.quantity - 1 } : l))
        .filter((l) => l.quantity > 0)
    );
  };

  const handleClearCart = () => {
    setCartLines([]);
    localStorage.removeItem(cartStorageKey);
    showToast('info', 'Cart cleared');
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] dark:bg-[#0B0F19] text-gray-900 dark:text-gray-100 flex flex-col font-sans transition-colors">
      {/* Toast Alert */}
      <Toast toast={toast} onClose={() => setToast(null)} />

      {/* 1. Global Shell: Top Bar */}
      <TopBar
        activeAccount={activeAccount}
        onOpenSwitchAccount={() => {
          if (!activeAccount && accounts.length === 0) {
            showToast('error', 'No saved accounts. Please login using < > JSON first.');
            return;
          }
          setIsSwitchModalOpen(true);
        }}
        darkMode={darkMode}
        onToggleDarkMode={() => setDarkMode((prev) => !prev)}
      />

      {/* 2. Main Content Container (Persistent Mounted Tab Screens) */}
      <main className="flex-1 max-w-md w-full mx-auto px-4 pt-3 pb-20">
        {/* Tab 1: Accounts */}
        <div style={{ display: activeTab === 'accounts' ? 'block' : 'none' }}>
          <AccountsTab
            accounts={accounts}
            activeAccount={activeAccount}
            onSelectAccount={handleSelectAccount}
            onDeleteAccount={handleDeleteAccount}
            onToggleStatus={handleToggleStatus}
            onSendOtp={handleSendOtp}
            onVerifyOtp={handleVerifyOtp}
            onLoginJson={handleLoginJson}
            onErrorToast={(msg) => showToast('error', msg)}
            onSuccessToast={(msg) => showToast('success', msg)}
            loading={accountsLoading}
          />
        </div>

        {/* Tab 2: Address */}
        <div style={{ display: activeTab === 'address' ? 'block' : 'none' }}>
          <AddressTab
            activeAccount={activeAccount}
            activeAddress={activeAddress}
            onSelectAddress={(addr) => {
              setActiveAddress(addr);
              showToast('success', `Selected: ${addr.name || 'Address'}`);
            }}
            onShowToast={showToast}
          />
        </div>

        {/* Tab 3: Search */}
        <div style={{ display: activeTab === 'search' ? 'block' : 'none' }}>
          <SearchTab
            activeAccount={activeAccount}
            activeAddress={activeAddress}
            onOpenAddressTab={() => setIsLocationModalOpen(true)}
            cartLines={cartLines}
            onAddToCart={handleAddToCart}
            onRemoveFromCart={handleRemoveFromCart}
            onGoToCart={() => setActiveTab('cart')}
            selectedRestaurant={selectedRestaurant}
            onSelectRestaurant={setSelectedRestaurant}
            onSetCartLines={setCartLines}
            onShowToast={showToast}
          />
        </div>

        {/* Tab 4: Cart */}
        <div style={{ display: activeTab === 'cart' ? 'block' : 'none' }}>
          <CartTab
            isActive={activeTab === 'cart'}
            activeAccount={activeAccount}
            activeAddress={activeAddress}
            onOpenAddressTab={() => setIsLocationModalOpen(true)}
            cartLines={cartLines}
            onAddToCart={handleAddToCart}
            onRemoveFromCart={handleRemoveFromCart}
            onClearCart={handleClearCart}
            onShowToast={showToast}
            onGoToOrders={() => setActiveTab('orders')}
            selectedRestaurant={selectedRestaurant}
            accounts={accounts}
            onSwitchAccount={handleSelectAccount}
            onGoToSearch={() => setActiveTab('search')}
          />
        </div>

        {/* Tab 5: Orders */}
        <div style={{ display: activeTab === 'orders' ? 'block' : 'none' }}>
          <OrdersTab
            activeAccount={activeAccount}
            onShowToast={showToast}
          />
        </div>
      </main>

      {/* 3. Global Shell: Bottom Navigation with Auth Interception & Live Cart Item Counter */}
      <BottomNav
        activeTab={activeTab}
        onSelectTab={handleTabSelect}
        cartCount={cartLines.reduce((acc, l) => acc + (l.quantity || 1), 0)}
      />

      {/* 4. Switch Account Bottom Sheet Modal */}
      <SwitchAccountModal
        isOpen={isSwitchModalOpen}
        onClose={() => setIsSwitchModalOpen(false)}
        accounts={accounts}
        activeAccount={activeAccount}
        onSelectAccount={handleSelectAccount}
        onToggleStatus={handleToggleStatus}
        onDeleteAccount={handleDeleteAccount}
      />

      {/* 5. Select Location Bottom Sheet Modal (Screenshot 3) */}
      <SelectLocationModal
        isOpen={isLocationModalOpen}
        onClose={() => setIsLocationModalOpen(false)}
        activeAccount={activeAccount}
        activeAddress={activeAddress}
        onSelectAddress={(addr) => {
          setActiveAddress(addr);
          showToast('success', `Delivery to: ${addr.name || 'Location'}`);
        }}
        onShowToast={showToast}
      />

      {/* 6. Replace Cart Confirmation Modal (Toing / Swiggy Single-Restaurant Business Rule) */}
      <ReplaceCartModal
        isOpen={!!conflictItem}
        onClose={handleCancelReplaceCart}
        onConfirm={handleConfirmReplaceCart}
        existingRestaurantName={cartLines[0]?.restaurant?.name || 'current restaurant'}
        newRestaurantName={conflictItem?.restaurant?.name || 'new restaurant'}
      />
    </div>
  );
}
