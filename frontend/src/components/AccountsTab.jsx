import React, { useState } from 'react';
import { 
  UserPlus, 
  Code, 
  LogIn, 
  Bookmark, 
  Search, 
  ShoppingCart, 
  Recycle, 
  Clock, 
  Trash2, 
  User, 
  Check, 
  Clipboard,
  Loader2
} from 'lucide-react';

export default function AccountsTab({
  accounts = [],
  activeAccount = null,
  onSelectAccount,
  onDeleteAccount,
  onToggleStatus,
  onLoginJson,
  onErrorToast,
  onSuccessToast,
  loading = false,
}) {
  const [jsonInput, setJsonInput] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filter, setFilter] = useState('all'); // 'all' | 'fresh' | 'used'

  // Filter calculation with safe fallback to 'fresh'
  const filteredAccounts = (accounts || []).filter((acc) => {
    const nameMatch = (acc.name || '').toLowerCase().includes(searchQuery.toLowerCase());
    const phoneMatch = (acc.phone || acc.mobile || '').includes(searchQuery);
    const matchesSearch = nameMatch || phoneMatch;

    const accStatus = (acc.status || 'fresh').toLowerCase();
    if (filter === 'fresh') return matchesSearch && accStatus === 'fresh';
    if (filter === 'used') return matchesSearch && accStatus === 'used';
    return matchesSearch;
  });

  const freshCount = (accounts || []).filter(
    (a) => (a.status || 'fresh').toLowerCase() === 'fresh'
  ).length;
  const usedCount = (accounts || []).filter(
    (a) => (a.status || 'fresh').toLowerCase() === 'used'
  ).length;

  const handlePasteClipboard = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        setJsonInput(text);
        if (onSuccessToast) onSuccessToast('Pasted JSON from clipboard');
      }
    } catch (e) {
      if (onErrorToast) onErrorToast('Unable to read clipboard. Please paste manually.');
    }
  };

  const handleJsonSubmit = async (e) => {
    e.preventDefault();
    const raw = jsonInput.trim();
    if (!raw) {
      if (onErrorToast) onErrorToast('Please paste a JSON credential object');
      return;
    }

    let parsed;
    try {
      parsed = JSON.parse(raw);
    } catch (err) {
      if (onErrorToast) onErrorToast('Invalid JSON syntax. Please check formatting.');
      return;
    }

    if (!parsed || typeof parsed !== 'object') {
      if (onErrorToast) onErrorToast('JSON payload must be an object.');
      return;
    }

    // Required fields: mobile, token, tid, sid (deviceId & customerId are optional with smart defaults)
    const requiredFields = ['mobile', 'token', 'tid', 'sid'];
    const missing = requiredFields.filter((f) => !parsed[f] || String(parsed[f]).trim() === '');

    if (missing.length > 0) {
      if (onErrorToast) {
        onErrorToast(`Missing required fields: ${missing.join(', ')}`);
      }
      return;
    }

    const payload = {
      ...parsed,
      deviceId: parsed.deviceId || 'dev_default',
      customerId: parsed.customerId || 'cust_default',
    };

    setIsSubmitting(true);
    try {
      const res = await onLoginJson(payload);
      if (res && res.success) {
        setJsonInput('');
        if (onSuccessToast) onSuccessToast(`Account ${res.account?.name || 'added'} successfully`);
      } else {
        const msg = res?.detail || res?.error || 'Authentication failed';
        if (onErrorToast) onErrorToast(msg);
      }
    } catch (err) {
      const msg = err.response?.data?.detail || err.response?.data?.error || err.message || 'Login failed';
      if (onErrorToast) onErrorToast(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-4 pb-24">
      {/* 1. Add Account Card (JSON-Only Mode directly) */}
      <div className="bg-white dark:bg-[#1E293B] rounded-3xl p-4 shadow-card border border-gray-100 dark:border-gray-800 transition-colors space-y-3">
        {/* Card Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 rounded-xl bg-[#F3E8FF] dark:bg-purple-950/60 flex items-center justify-center text-[#7C3AED] dark:text-purple-300">
              <UserPlus className="w-4 h-4" />
            </div>
            <div>
              <h2 className="font-extrabold text-sm text-gray-900 dark:text-white">Add Account</h2>
              <p className="text-[10px] text-gray-400">Import session via JSON</p>
            </div>
          </div>

          <button
            type="button"
            onClick={handlePasteClipboard}
            className="flex items-center space-x-1 px-3 py-1 rounded-full bg-purple-50 dark:bg-purple-950/60 border border-purple-200 dark:border-purple-800/60 text-[#7C3AED] dark:text-purple-300 text-xs font-bold hover:bg-purple-100 transition-all active:scale-95"
            title="Paste from clipboard"
          >
            <Clipboard className="w-3.5 h-3.5" />
            <span>Paste</span>
          </button>
        </div>

        {/* JSON Credentials Form */}
        <form onSubmit={handleJsonSubmit} className="space-y-3">
          <div>
            <textarea
              rows={5}
              placeholder={`{\n  "mobile": "...",\n  "name": "...",\n  "token": "...",\n  "tid": "...",\n  "sid": "...",\n  "deviceId": "...",\n  "customerId": "..."\n}`}
              value={jsonInput}
              onChange={(e) => setJsonInput(e.target.value)}
              className="w-full border border-gray-200 dark:border-gray-700 rounded-2xl bg-gray-50/60 dark:bg-gray-800/60 p-3 text-xs font-mono text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 leading-relaxed shadow-inner"
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full bg-gradient-to-r from-[#9061F9] to-[#7E3AF2] hover:from-[#7E3AF2] hover:to-[#6C2BD9] disabled:opacity-60 text-white font-extrabold py-3 px-4 rounded-2xl shadow-lg shadow-purple-500/25 flex items-center justify-center space-x-2 transition-all active:scale-[0.99]"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Authenticating & Importing...</span>
              </>
            ) : (
              <>
                <LogIn className="w-4 h-4" />
                <span>Login with JSON</span>
              </>
            )}
          </button>
        </form>
      </div>

      {/* 2. Saved Accounts Header */}
      <div className="flex items-center space-x-2 px-1">
        <div className="w-5 h-5 rounded-lg bg-purple-100 dark:bg-purple-950 flex items-center justify-center text-[#7C3AED] dark:text-purple-400">
          <Bookmark className="w-3 h-3" />
        </div>
        <h3 className="font-extrabold text-xs text-gray-900 dark:text-white uppercase tracking-wider">
          Saved Accounts
        </h3>
        <span className="text-[10px] font-bold text-gray-400 dark:text-gray-500 bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded-full">
          {accounts.length}
        </span>
      </div>

      {/* 3. Search Bar */}
      <div className="relative">
        <Search className="w-4 h-4 absolute left-3.5 top-3 text-gray-400" />
        <input
          type="text"
          placeholder="Search Account by name or number..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full bg-white dark:bg-[#1E293B] border border-gray-200 dark:border-gray-800 rounded-2xl pl-10 pr-4 py-2.5 text-xs text-gray-900 dark:text-white placeholder-gray-400 shadow-sm focus:outline-none focus:border-purple-400 focus:ring-1 focus:ring-purple-400 transition-all"
        />
      </div>

      {/* 4. Filter Chips (All, Fresh, Used) & Delete Used Button */}
      <div className="flex items-center justify-between space-x-2">
        <div className="flex items-center space-x-2 overflow-x-auto no-scrollbar">
          <button
            type="button"
            onClick={() => setFilter('all')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all shadow-sm ${
              filter === 'all'
                ? 'bg-[#059669] text-white shadow-emerald-500/20'
                : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300'
            }`}
          >
            <ShoppingCart className="w-3.5 h-3.5" />
            <span>All</span>
            <span className="text-[10px] opacity-80">({accounts.length})</span>
          </button>

          <button
            type="button"
            onClick={() => setFilter('fresh')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all shadow-sm ${
              filter === 'fresh'
                ? 'bg-[#059669] text-white shadow-emerald-500/20'
                : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300'
            }`}
          >
            <Recycle className="w-3.5 h-3.5" />
            <span>Fresh</span>
            <span className="text-[10px] opacity-80">({freshCount})</span>
          </button>

          <button
            type="button"
            onClick={() => setFilter('used')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all shadow-sm ${
              filter === 'used'
                ? 'bg-[#059669] text-white shadow-emerald-500/20'
                : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300'
            }`}
          >
            <Clock className="w-3.5 h-3.5" />
            <span>Used</span>
            <span className="text-[10px] opacity-80">({usedCount})</span>
          </button>
        </div>

        <button
          type="button"
          onClick={() => {
            const usedAccs = accounts.filter(
              (a) => (a.status || 'fresh').toLowerCase() === 'used'
            );
            if (usedAccs.length === 0) {
              if (onErrorToast) onErrorToast('No used accounts to delete');
              return;
            }
            if (window.confirm(`Delete all ${usedAccs.length} account(s) marked as used?`)) {
              usedAccs.forEach((a) => onDeleteAccount(a.id || a.mobile));
            }
          }}
          className="p-2 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-100 dark:border-red-900/60 text-red-500 hover:bg-red-100 active:scale-95 transition-all flex-shrink-0"
          aria-label="Delete all used"
          title="Delete all used accounts"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      {/* 5. Account Cards List */}
      <div className="space-y-2.5">
        {loading ? (
          <div className="text-center py-12 flex flex-col items-center justify-center space-y-2 text-gray-400 text-xs">
            <Loader2 className="w-6 h-6 animate-spin text-purple-600" />
            <span>Loading accounts...</span>
          </div>
        ) : filteredAccounts.length === 0 ? (
          <div className="bg-white dark:bg-[#1E293B] rounded-2xl p-8 border border-dashed border-gray-200 dark:border-gray-800 text-center space-y-2">
            <p className="text-xs font-bold text-gray-500 dark:text-gray-400">
              No {filter !== 'all' ? `${filter} ` : ''}saved accounts found.
            </p>
            <p className="text-[11px] text-gray-400 dark:text-gray-500">
              Paste credentials in &lt; /&gt; JSON mode above to add an account.
            </p>
          </div>
        ) : (
          filteredAccounts.map((acc) => {
            const isSelected = activeAccount && (activeAccount.id === acc.id || activeAccount.mobile === acc.mobile);
            const isFresh = (acc.status || 'fresh').toLowerCase() === 'fresh';
            const phoneDisplay = acc.phone || (acc.mobile ? `+91 ${acc.mobile.replace(/^\+?91/, '')}` : '');
            const displayName = acc.name || `User ${(acc.mobile || '').slice(-4)}`;

            return (
              <div
                key={acc.id || acc.mobile}
                onClick={() => onSelectAccount(acc)}
                className={`bg-white dark:bg-[#1E293B] rounded-2xl p-3 border shadow-card flex items-center justify-between cursor-pointer transition-all active:scale-[0.99] ${
                  isSelected
                    ? 'border-purple-300 dark:border-purple-700 ring-2 ring-purple-500/20 shadow-md'
                    : 'border-gray-100 dark:border-gray-800 hover:border-gray-200'
                }`}
              >
                {/* Left: Avatar + Extracted Account Name + Mobile */}
                <div className="flex items-center space-x-3 min-w-0">
                  <div className="relative flex-shrink-0">
                    <div
                      className={`w-11 h-11 rounded-2xl flex items-center justify-center font-bold text-sm ${
                        isSelected
                          ? 'bg-[#EDE9FE] text-[#7C3AED] dark:bg-purple-950/80 dark:text-purple-300'
                          : isFresh
                          ? 'bg-[#ECFDF5] text-[#059669] dark:bg-emerald-950/80 dark:text-emerald-300'
                          : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300'
                      }`}
                    >
                      <User className="w-5 h-5" />
                    </div>

                    {/* Radio / Check Badge on Avatar */}
                    {isSelected ? (
                      <div className="w-4 h-4 rounded-full bg-[#10B981] text-white flex items-center justify-center absolute -top-1 -right-1 ring-2 ring-white dark:ring-gray-900 shadow-sm">
                        <Check className="w-2.5 h-2.5 stroke-[3]" />
                      </div>
                    ) : (
                      <div className="w-3.5 h-3.5 rounded-full border-2 border-gray-300 dark:border-gray-600 absolute -top-1 -right-1 bg-white dark:bg-gray-800" />
                    )}
                  </div>

                  <div className="min-w-0">
                    <h3 className="font-extrabold text-sm text-gray-900 dark:text-white truncate">
                      {displayName}
                    </h3>
                    <p className="text-xs text-gray-500 dark:text-gray-400 font-medium tracking-tight">
                      {phoneDisplay}
                    </p>
                  </div>
                </div>

                {/* Right: Working Fresh/Used Status Toggle Pill & Delete Button */}
                <div className="flex items-center space-x-2 flex-shrink-0" onClick={(e) => e.stopPropagation()}>
                  {isFresh ? (
                    <button
                      type="button"
                      onClick={() => onToggleStatus(acc.id || acc.mobile)}
                      className="flex items-center space-x-1.5 bg-[#ECFDF5] dark:bg-emerald-950/60 border border-[#A7F3D0] dark:border-emerald-800 text-[#059669] dark:text-emerald-400 text-[11px] font-black px-2.5 py-1 rounded-full hover:bg-emerald-100 active:scale-95 transition-all shadow-sm"
                      title="Status: Fresh (Click to mark as Used)"
                    >
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                      <span>FRESH</span>
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={() => onToggleStatus(acc.id || acc.mobile)}
                      className="flex items-center space-x-1.5 bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 text-[11px] font-black px-2.5 py-1 rounded-full hover:bg-gray-200 active:scale-95 transition-all shadow-sm"
                      title="Status: Used (Click to mark as Fresh)"
                    >
                      <Clock className="w-3 h-3 text-gray-400" />
                      <span>USED</span>
                    </button>
                  )}

                  <button
                    type="button"
                    onClick={() => onDeleteAccount(acc.id || acc.mobile)}
                    className="p-1.5 text-gray-400 hover:text-red-500 rounded-lg transition-colors active:scale-90"
                    aria-label="Delete account"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
