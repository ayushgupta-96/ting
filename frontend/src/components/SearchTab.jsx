import React, { useState, useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { 
  Search, 
  MapPin, 
  ChevronDown, 
  ChevronRight, 
  ArrowLeft, 
  Plus, 
  Minus, 
  ShoppingBag, 
  Loader2, 
  X, 
  Store, 
  Clock, 
  Star, 
  ChevronUp,
  Zap,
  Sparkles
} from 'lucide-react';
import { api } from '../services/api';

const POPULAR_RESTAURANTS = [
  "Domino's",
  "KFC",
  "McDonald's",
  "Pizza Hut",
  "Burger King",
  "Subway",
  "Wow! Momo",
  "Haldiram",
];

export default function SearchTab({
  activeAccount,
  activeAddress,
  onOpenAddressTab,
  cartLines = [],
  onAddToCart,
  onRemoveFromCart,
  onGoToCart,
  selectedRestaurant = null,
  onSelectRestaurant,
  onSetCartLines,
  onShowToast,
}) {
  const [searchInput, setSearchInput] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [internalRestaurant, setInternalRestaurant] = useState(null);

  const activeRest = selectedRestaurant !== null && selectedRestaurant !== undefined ? selectedRestaurant : internalRestaurant;
  const setRestaurant = (rest) => {
    if (onSelectRestaurant) {
      onSelectRestaurant(rest);
    }
    setInternalRestaurant(rest);
  };
  
  // Restaurant Search Filter
  const [restaurantFilter, setRestaurantFilter] = useState('all'); // 'all' | 'under99' | 'under149' | 'open' | 'veg'

  // Menu View Filters
  const [isVegOnly, setIsVegOnly] = useState(false);
  const [budgetFilter, setBudgetFilter] = useState('all'); // 'all' | 'under99' | 'under149'
  const [dishSearchQuery, setDishSearchQuery] = useState('');
  const [isDishSearchActive, setIsDishSearchActive] = useState(false);
  const [openCategories, setOpenCategories] = useState({});
  const [activeCategoryFilter, setActiveCategoryFilter] = useState(null);

  const categoryRefs = useRef({});

  // 400ms search input debounce
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedQuery(searchInput.trim());
    }, 400);
    return () => clearTimeout(handler);
  }, [searchInput]);

  const lat = activeAddress?.lat;
  const lng = activeAddress?.lng;
  const mobile = activeAccount?.mobile || '';

  // 1. Restaurant Search Query (Maps strictly to GET /api/search/restaurants)
  const {
    data: searchData,
    isLoading: searchLoading,
  } = useQuery({
    queryKey: ['search', debouncedQuery, lat, lng, mobile],
    queryFn: () => api.search(debouncedQuery, lat, lng, mobile),
    enabled: !!debouncedQuery && !activeRest && !!lat && !!lng,
    staleTime: 1000 * 60 * 2,
  });

  const restaurants = searchData?.restaurants || [];
  const openCount = restaurants.filter(
    (r) => r.availability?.opened === true || r.availability?.text?.toLowerCase().includes('open')
  ).length;

  // 2. Menu Query (Maps strictly to POST /api/search/menu)
  const {
    data: menuData,
    isLoading: menuLoading,
  } = useQuery({
    queryKey: ['menu', activeRest?.id, lat, lng, mobile],
    queryFn: () =>
      api.getMenu(
        activeRest.id,
        activeRest.name || '',
        activeRest.metadata || '',
        lat,
        lng,
        mobile
      ),
    enabled: !!activeRest?.id,
    staleTime: 1000 * 60 * 5,
  });

  const categories = menuData?.categories || [];
  const restaurantInfo = menuData?.restaurant || activeRest || {};

  // Auto-open all categories when menu loads
  useEffect(() => {
    if (categories.length > 0) {
      const initialOpen = {};
      categories.forEach((cat) => {
        initialOpen[cat.name] = true;
      });
      setOpenCategories(initialOpen);
    }
  }, [menuData]);

  const toggleCategory = (catName) => {
    setOpenCategories((prev) => ({
      ...prev,
      [catName]: !prev[catName],
    }));
  };

  const scrollToCategory = (catName) => {
    setActiveCategoryFilter(catName);
    setOpenCategories((prev) => ({ ...prev, [catName]: true }));
    const el = categoryRefs.current[catName];
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  const cartTotalItems = cartLines.reduce((acc, l) => acc + l.quantity, 0);
  const cartTotalPrice = cartLines.reduce((acc, l) => acc + (l.price || 0) * l.quantity, 0);

  // 1-Click Smart Cart Builder (Free Cash Maximizer)
  const handleAutoBuildSmartCart = () => {
    if (!categories || categories.length === 0) {
      if (onShowToast) onShowToast('info', 'No menu items available to build cart.');
      return;
    }

    const allDishes = [];
    categories.forEach((cat) => {
      (cat.items || []).forEach((item) => {
        const raw = item.price || item.base_price || 0;
        const p = raw > 1000 ? Math.round(raw / 100) : raw;
        if (p > 0 && item.in_stock !== false) {
          allDishes.push({
            ...item,
            normalizedPrice: p,
          });
        }
      });
    });

    if (allDishes.length === 0) {
      if (onShowToast) onShowToast('error', 'No priced dishes found.');
      return;
    }

    // 1. Look for single item in target sweet spot (₹95 - ₹115)
    let bestSelection = null;
    const singleIdeal = allDishes.find((d) => d.normalizedPrice >= 95 && d.normalizedPrice <= 115);
    if (singleIdeal) {
      bestSelection = [{ dish: singleIdeal, qty: 1 }];
    }

    // 2. Look for 2 items summing to ₹95 - ₹115
    if (!bestSelection) {
      for (let i = 0; i < allDishes.length; i++) {
        for (let j = i + 1; j < allDishes.length; j++) {
          const sum = allDishes[i].normalizedPrice + allDishes[j].normalizedPrice;
          if (sum >= 95 && sum <= 115) {
            bestSelection = [
              { dish: allDishes[i], qty: 1 },
              { dish: allDishes[j], qty: 1 },
            ];
            break;
          }
        }
        if (bestSelection) break;
      }
    }

    // 3. Look for 1 item with quantity 2
    if (!bestSelection) {
      const doubleCandidate = allDishes.find((d) => d.normalizedPrice * 2 >= 95 && d.normalizedPrice * 2 <= 120);
      if (doubleCandidate) {
        bestSelection = [{ dish: doubleCandidate, qty: 2 }];
      }
    }

    // 4. Fallback: closest combination to ₹100
    if (!bestSelection) {
      let closestDiff = 9999;
      allDishes.forEach((d) => {
        const diff = Math.abs(d.normalizedPrice - 100);
        if (diff < closestDiff) {
          closestDiff = diff;
          bestSelection = [{ dish: d, qty: 1 }];
        }
      });
    }

    if (bestSelection && bestSelection.length > 0) {
      const newCartLines = bestSelection.map(({ dish, qty }) => ({
        id: String(dish.id),
        name: dish.name,
        price: dish.normalizedPrice,
        base_price: dish.normalizedPrice,
        image: dish.image,
        image_id: dish.image_id,
        is_veg: dish.is_veg,
        quantity: qty,
        restaurant: {
          id: String(activeRest?.id || ''),
          name: activeRest?.name || '',
          area: activeRest?.area || '',
          image: activeRest?.image || activeRest?.cover || '',
          sla: activeRest?.sla || '',
        },
      }));

      const totalVal = newCartLines.reduce((acc, l) => acc + l.price * l.quantity, 0);
      const estPayable = Math.max(1, totalVal - 100);

      if (onSetCartLines) {
        onSetCartLines(newCartLines);
      } else {
        newCartLines.forEach((l) => onAddToCart(l));
      }

      if (onShowToast) {
        onShowToast('success', `✨ Smart ₹1 Cart built! Total: ₹${totalVal} (Est. to pay ~₹${estPayable})`);
      }
    }
  };

  // Filter restaurants by restaurantFilter chip
  let filteredRestaurants = restaurants;
  if (restaurantFilter === 'veg') {
    filteredRestaurants = filteredRestaurants.filter((r) =>
      (r.cuisines || []).some?.((c) => c.toLowerCase().includes('veg')) ||
      (typeof r.cuisines === 'string' && r.cuisines.toLowerCase().includes('veg'))
    );
  } else if (restaurantFilter === 'open') {
    filteredRestaurants = filteredRestaurants.filter((r) =>
      r.availability?.opened === true || r.availability?.text?.toLowerCase().includes('open')
    );
  } else if (restaurantFilter === 'under99') {
    const matched = filteredRestaurants.filter((r) =>
      (r.name || '').toLowerCase().includes('99') ||
      (r.cuisines || []).some?.((c) => c.toLowerCase().includes('snack') || c.toLowerCase().includes('fast food'))
    );
    if (matched.length > 0) filteredRestaurants = matched;
  }

  // Filter menu items by Veg toggle, dish search, and budgetFilter
  const filteredCategories = categories
    .map((cat) => {
      let items = cat.items || [];
      if (isVegOnly) {
        items = items.filter((it) => it.is_veg === true);
      }
      if (budgetFilter === 'under99') {
        items = items.filter((it) => {
          const raw = it.price || it.base_price || 0;
          const p = raw > 1000 ? Math.round(raw / 100) : raw;
          return p <= 99;
        });
      } else if (budgetFilter === 'under149') {
        items = items.filter((it) => {
          const raw = it.price || it.base_price || 0;
          const p = raw > 1000 ? Math.round(raw / 100) : raw;
          return p <= 149;
        });
      }
      if (dishSearchQuery.trim()) {
        const query = dishSearchQuery.toLowerCase();
        items = items.filter(
          (it) =>
            it.name?.toLowerCase().includes(query) ||
            it.description?.toLowerCase().includes(query)
        );
      }
      return { ...cat, items };
    })
    .filter((cat) => cat.items.length > 0);

  return (
    <div className="space-y-3.5 pb-28 animate-fade-in">
      {/* 1. Top "Deliver To" Header (Matching Screenshot 2 & 3) */}
      <div
        onClick={onOpenAddressTab}
        className="bg-white dark:bg-[#1E293B] rounded-3xl p-3.5 shadow-card border border-gray-100 dark:border-gray-800 flex items-center justify-between cursor-pointer hover:border-purple-300 transition-all"
      >
        <div className="flex items-center space-x-3 min-w-0">
          <div className="w-10 h-10 rounded-2xl bg-purple-50 dark:bg-purple-950/60 flex items-center justify-center text-[#7C3AED] dark:text-purple-300 flex-shrink-0">
            <MapPin className="w-5 h-5" />
          </div>
          <div className="min-w-0">
            <p className="text-[10px] font-black uppercase tracking-wider text-gray-400 dark:text-gray-500">
              Deliver To
            </p>
            <h3 className="font-extrabold text-xs text-gray-900 dark:text-white truncate">
              {activeAddress
                ? activeAddress.annotation || activeAddress.name || 'Saved Address'
                : 'Select your location'}
            </h3>
            <p className="text-[11px] text-gray-400 truncate">
              {activeAddress
                ? activeAddress.formatted_address || activeAddress.address || 'Location'
                : 'Tap to choose where to deliver'}
            </p>
          </div>
        </div>

        <ChevronDown className="w-4 h-4 text-gray-400 flex-shrink-0" />
      </div>

      {!activeRest ? (
        /* ==================== RESTAURANT SEARCH MODE ==================== */
        <div className="space-y-3">
          {/* Prominent Address Requirement Alert if no address selected */}
          {!activeAddress && (
            <div
              onClick={onOpenAddressTab}
              className="bg-purple-50 dark:bg-purple-950/40 border border-purple-200 dark:border-purple-800 rounded-2xl p-3.5 flex items-center justify-between cursor-pointer shadow-sm hover:border-purple-400 active:scale-[0.99] transition-all animate-fade-in"
            >
              <div className="flex items-center space-x-2.5 min-w-0">
                <div className="w-8 h-8 rounded-xl bg-[#7C3AED] text-white flex items-center justify-center flex-shrink-0 shadow-sm">
                  <MapPin className="w-4 h-4" />
                </div>
                <div className="min-w-0">
                  <h4 className="font-extrabold text-xs text-gray-900 dark:text-white truncate">
                    Select delivery address first
                  </h4>
                  <p className="text-[11px] text-gray-500 dark:text-gray-400 truncate">
                    Required to show open restaurants near your location
                  </p>
                </div>
              </div>
              <button
                type="button"
                className="bg-[#7C3AED] hover:bg-purple-700 text-white font-black text-xs px-3 py-1.5 rounded-xl flex-shrink-0 shadow-sm"
              >
                Select
              </button>
            </div>
          )}

            {/* Search Bar (Matching Screenshot 2 & 3) */}
            <div className="relative">
              <Search
                className={`w-4 h-4 absolute left-3.5 top-3.5 transition-colors ${
                  searchInput ? 'text-[#7C3AED]' : 'text-gray-400'
                }`}
              />
              <input
                type="text"
                placeholder={activeAddress ? "Search for restaurants..." : "Select delivery address to search..."}
                value={searchInput}
                onFocus={() => {
                  if (!activeAddress) {
                    onOpenAddressTab();
                  }
                }}
                onClick={() => {
                  if (!activeAddress) {
                    onOpenAddressTab();
                  }
                }}
                onChange={(e) => {
                  if (!activeAddress) {
                    onOpenAddressTab();
                    return;
                  }
                  setSearchInput(e.target.value);
                }}
                className={`w-full bg-white dark:bg-[#1E293B] border rounded-2xl pl-10 pr-10 py-3 text-xs text-gray-900 dark:text-white placeholder-gray-400 shadow-sm transition-all focus:outline-none ${
                  searchInput
                    ? 'border-purple-400 ring-2 ring-purple-100 dark:ring-purple-950/60'
                    : 'border-gray-200 dark:border-gray-800 focus:border-purple-300'
                }`}
              />
              {searchInput && (
                <button
                  onClick={() => setSearchInput('')}
                  className="absolute right-3.5 top-3 w-5 h-5 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-gray-400 hover:text-gray-600"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            {/* Quick Filter Chips (Budget & Status) */}
            <div className="flex items-center space-x-2 overflow-x-auto no-scrollbar py-0.5">
              {[
                { id: 'all', label: 'All' },
                { id: 'under99', label: 'Under ₹99' },
                { id: 'open', label: 'Open Now' },
                { id: 'veg', label: 'Pure Veg' },
              ].map((f) => (
                <button
                  key={f.id}
                  type="button"
                  onClick={() => {
                    setRestaurantFilter(f.id);
                    if (f.id === 'under99' && !searchInput) {
                      setSearchInput('99');
                    }
                  }}
                  className={`px-3 py-1.5 rounded-full text-xs font-extrabold transition-all flex-shrink-0 ${
                    restaurantFilter === f.id
                      ? 'bg-purple-600 text-white shadow-sm'
                      : 'bg-white dark:bg-[#1E293B] border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:border-purple-300'
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>

          {/* A. Empty Query: "Search Restaurants" + Popular Pills (Screenshot 2) */}
          {!searchInput.trim() && (
            <div className="py-6 text-center animate-fade-in">
              <div className="w-16 h-16 rounded-full bg-purple-100 dark:bg-purple-950/80 flex items-center justify-center text-[#7C3AED] dark:text-purple-400 mx-auto">
                <Store className="w-8 h-8" />
              </div>
              <h3 className="font-black text-base text-gray-900 dark:text-white mt-3.5">
                Search Restaurants
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 max-w-xs mx-auto mt-1 leading-relaxed">
                Type a restaurant name to see its menu and add dishes to your cart
              </p>

              {/* Popular Restaurants Section */}
              <div className="mt-8">
                <p className="text-[10px] font-black uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-3 text-center">
                  POPULAR RESTAURANTS
                </p>
                <div className="flex flex-wrap justify-center gap-2 max-w-sm mx-auto">
                  {POPULAR_RESTAURANTS.map((brand) => (
                    <button
                      key={brand}
                      onClick={() => {
                        if (!activeAddress) {
                          onOpenAddressTab();
                          return;
                        }
                        setSearchInput(brand);
                      }}
                      className="bg-white dark:bg-[#1E293B] border border-gray-200 dark:border-gray-700/80 hover:border-purple-300 dark:hover:border-purple-500 text-gray-800 dark:text-gray-200 font-extrabold text-xs px-3.5 py-1.5 rounded-full shadow-sm active:scale-95 transition-all"
                    >
                      {brand}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* B. Loading Spinner */}
          {searchInput.trim() && searchLoading && (
            <div className="py-20 flex flex-col items-center justify-center space-y-2 text-gray-400 text-xs">
              <Loader2 className="w-6 h-6 animate-spin text-[#7C3AED]" />
              <span>Searching restaurants near your location...</span>
            </div>
          )}

          {/* C. Results List (Screenshot 3) */}
          {searchInput.trim() && !searchLoading && restaurants.length > 0 && (
            <div className="space-y-3 animate-fade-in">
              {/* Results subheader: count & open status */}
              <div className="flex items-center justify-between px-1">
                <span className="font-extrabold text-xs text-gray-900 dark:text-white">
                  {restaurants.length} {restaurants.length === 1 ? 'restaurant' : 'restaurants'}
                </span>
                {openCount > 0 && (
                  <span className="bg-emerald-50 dark:bg-emerald-950/60 text-[#059669] dark:text-emerald-300 font-extrabold text-[11px] px-2.5 py-0.5 rounded-full flex items-center space-x-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#059669]" />
                    <span>{openCount} open now</span>
                  </span>
                )}
              </div>

              {/* Restaurant Cards */}
              <div className="space-y-2.5">
                {filteredRestaurants.map((rest) => {
                  const ratingVal = rest.rating || '4.1';
                  const slaText = rest.sla || '30-35 mins';
                  const areaText = rest.area || rest.city || 'Greater Noida';
                  const distText = rest.distance || '4.2 km';
                  const cuisinesText = Array.isArray(rest.cuisines)
                    ? rest.cuisines.join(', ')
                    : rest.cuisines || 'Snacks, Fast Food';

                  return (
                    <div
                      key={rest.id}
                      onClick={() => {
                        setRestaurant(rest);
                        setDishSearchQuery('');
                        setIsVegOnly(false);
                        setIsDishSearchActive(false);
                      }}
                      className="bg-white dark:bg-[#1E293B] rounded-2xl p-3 border border-gray-100 dark:border-gray-800 shadow-card flex items-center justify-between cursor-pointer hover:border-purple-300 active:scale-[0.99] transition-all group"
                    >
                      <div className="flex items-center space-x-3 min-w-0">
                        <img
                          src={
                            rest.image ||
                            'https://images.unsplash.com/photo-1513104890138-7c749659a591?w=160'
                          }
                          alt={rest.name}
                          className="w-16 h-16 rounded-2xl object-cover bg-gray-100 dark:bg-gray-800 flex-shrink-0"
                          onError={(e) => {
                            e.target.src =
                              'https://images.unsplash.com/photo-1513104890138-7c749659a591?w=160';
                          }}
                        />

                        <div className="min-w-0 space-y-0.5">
                          <h4 className="font-extrabold text-xs text-gray-900 dark:text-white truncate group-hover:text-purple-600 transition-colors">
                            {rest.name}
                          </h4>

                          {/* Rating & SLA row */}
                          <div className="flex items-center space-x-2 text-[11px]">
                            <span className="bg-[#059669] text-white text-[10px] font-black px-1.5 py-0.5 rounded-md flex items-center space-x-0.5">
                              <Star className="w-2.5 h-2.5 fill-white" />
                              <span>{ratingVal}</span>
                            </span>
                            <span className="text-gray-600 dark:text-gray-300 font-bold flex items-center space-x-1">
                              <Clock className="w-3 h-3 text-gray-400" />
                              <span>{slaText}</span>
                            </span>
                          </div>

                          {/* Cuisines */}
                          <p className="text-[11px] text-gray-400 dark:text-gray-500 truncate">
                            {cuisinesText}
                          </p>

                          {/* Area & Distance */}
                          <p className="text-[11px] text-gray-500 dark:text-gray-400 flex items-center space-x-1 truncate">
                            <MapPin className="w-3 h-3 text-red-500 flex-shrink-0" />
                            <span>{areaText}</span>
                            <span>•</span>
                            <span>{distText}</span>
                          </p>
                        </div>
                      </div>

                      <div className="w-7 h-7 rounded-full bg-gray-50 dark:bg-gray-800 flex items-center justify-center text-gray-400 group-hover:text-purple-600 group-hover:bg-purple-50 transition-colors flex-shrink-0 ml-2">
                        <ChevronRight className="w-4 h-4" />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* D. No Results Empty State */}
          {searchInput.trim() && !searchLoading && restaurants.length === 0 && (
            <div className="bg-white dark:bg-[#1E293B] rounded-2xl p-8 border border-dashed border-gray-200 dark:border-gray-800 text-center space-y-2">
              <p className="text-xs font-bold text-gray-500 dark:text-gray-400">
                No restaurants found matching "{debouncedQuery}"
              </p>
              <p className="text-[11px] text-gray-400 dark:text-gray-500">
                Try searching for a different dish or brand like Domino's, KFC, or Burger King.
              </p>
            </div>
          )}
        </div>
      ) : (
        /* ==================== RESTAURANT MENU VIEW (Screenshots 4 & 5) ==================== */
        <div className="space-y-4 animate-fade-in">
          {/* 1. Header with Back button, Title, and Veg Switch */}
          <div className="flex items-center justify-between pb-1">
            <div className="flex items-center space-x-2.5 min-w-0">
              <button
                onClick={() => {
                  setRestaurant(null);
                  setIsDishSearchActive(false);
                  setDishSearchQuery('');
                }}
                className="w-8 h-8 rounded-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 flex items-center justify-center text-gray-700 dark:text-gray-200 hover:bg-gray-100 shadow-sm transition-all"
              >
                <ArrowLeft className="w-4 h-4" />
              </button>
              <h3 className="font-extrabold text-sm text-gray-900 dark:text-white truncate">
                {activeRest.name}
              </h3>
            </div>

            {/* Veg Only Toggle Switch (Screenshot 4) */}
            <div className="flex items-center space-x-1.5 flex-shrink-0 pl-2">
              <span className={`text-xs font-black ${isVegOnly ? 'text-emerald-600' : 'text-gray-500'}`}>
                Veg
              </span>
              <button
                type="button"
                onClick={() => setIsVegOnly((prev) => !prev)}
                className={`w-9 h-5 rounded-full p-0.5 transition-colors duration-200 ease-in-out focus:outline-none ${
                  isVegOnly ? 'bg-emerald-600' : 'bg-gray-300 dark:bg-gray-700'
                }`}
              >
                <div
                  className={`w-4 h-4 rounded-full bg-white shadow-md transform transition-transform duration-200 ease-in-out ${
                    isVegOnly ? 'translate-x-4' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>
          </div>

          {/* 2. Restaurant Hero Banner Card (Screenshot 4) */}
          <div className="relative rounded-3xl overflow-hidden shadow-card border border-gray-100 dark:border-gray-800">
            <div className="h-44 w-full relative">
              <img
                src={
                  restaurantInfo.cover ||
                  restaurantInfo.image ||
                  activeRest.image ||
                  'https://images.unsplash.com/photo-1513104890138-7c749659a591?w=800'
                }
                alt={activeRest.name}
                className="w-full h-full object-cover"
                onError={(e) => {
                  e.target.src =
                    'https://images.unsplash.com/photo-1513104890138-7c749659a591?w=800';
                }}
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/30 to-transparent" />

              {/* Title & Rating overlay */}
              <div className="absolute bottom-3 left-4 right-4 flex items-end justify-between">
                <h2 className="text-white font-black text-lg drop-shadow truncate pr-2">
                  {activeRest.name}
                </h2>
                <div className="bg-[#059669] text-white text-xs font-black px-2 py-0.5 rounded-lg flex items-center space-x-1 shadow-md flex-shrink-0">
                  <Star className="w-3 h-3 fill-white" />
                  <span>{activeRest.rating || '4.1'}</span>
                </div>
              </div>
            </div>

            {/* Overlapping Outlet Card */}
            <div className="bg-white dark:bg-[#1E293B] p-3 flex items-center justify-between border-t border-gray-100 dark:border-gray-800">
              <div className="flex items-center space-x-2.5 min-w-0">
                <div className="w-8 h-8 rounded-xl bg-purple-50 dark:bg-purple-950/60 flex items-center justify-center text-[#7C3AED] dark:text-purple-300 flex-shrink-0">
                  <Store className="w-4 h-4" />
                </div>
                <div className="min-w-0">
                  <p className="text-[9px] font-black uppercase tracking-wider text-gray-400 dark:text-gray-500">
                    OUTLET
                  </p>
                  <h4 className="font-extrabold text-xs text-gray-900 dark:text-white truncate">
                    {activeRest.area || 'Greater Noida'}, Noida 1
                  </h4>
                </div>
              </div>

              <div className="h-6 w-[1px] bg-gray-200 dark:bg-gray-700 mx-2" />

              <div className="text-right flex-shrink-0">
                <p className="text-[10px] font-black text-gray-400">
                  {activeRest.distance || '4.2 KM'}
                </p>
                <p className="text-xs font-black text-gray-900 dark:text-white">
                  {activeRest.sla || '30-35 mins'}
                </p>
              </div>
            </div>
          </div>

          {/* 2B. 1-Click Smart Cart Builder (Free Cash Maximizer) */}
          <div className="bg-gradient-to-r from-purple-700 via-indigo-700 to-[#7C3AED] text-white rounded-3xl p-3.5 shadow-card border border-purple-400/30 space-y-2 relative overflow-hidden">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2.5 min-w-0">
                <div className="w-9 h-9 rounded-2xl bg-white/20 flex items-center justify-center text-amber-300 flex-shrink-0 shadow-inner">
                  <Zap className="w-5 h-5 fill-amber-300" />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center space-x-1.5">
                    <h4 className="font-black text-xs text-white truncate">⚡ Free Cash Maximizer</h4>
                    <span className="bg-amber-400 text-gray-950 font-black text-[9px] px-1.5 py-0.2 rounded-full uppercase flex-shrink-0">
                      PAY ₹1
                    </span>
                  </div>
                  <p className="text-[10px] text-purple-200 truncate">
                    Auto-builds ~₹100 cart using Free Cash + BHIMNEW
                  </p>
                </div>
              </div>

              <button
                type="button"
                onClick={handleAutoBuildSmartCart}
                className="bg-amber-400 hover:bg-amber-300 active:scale-95 text-gray-950 font-black text-xs px-3 py-2 rounded-xl shadow-md transition-all flex items-center space-x-1 flex-shrink-0 ml-2"
              >
                <Sparkles className="w-3.5 h-3.5 fill-gray-950" />
                <span>Auto-Build</span>
              </button>
            </div>
          </div>

          {/* 2C. Budget Filter Chips */}
          <div className="flex items-center space-x-2 overflow-x-auto no-scrollbar py-0.5">
            <button
              type="button"
              onClick={() => setBudgetFilter('all')}
              className={`px-3 py-1.5 rounded-full text-xs font-extrabold transition-all flex-shrink-0 ${
                budgetFilter === 'all'
                  ? 'bg-purple-600 text-white shadow-sm'
                  : 'bg-white dark:bg-[#1E293B] border border-gray-200 dark:border-gray-800 text-gray-700 dark:text-gray-300'
              }`}
            >
              All Items
            </button>
            <button
              type="button"
              onClick={() => setBudgetFilter('under99')}
              className={`px-3 py-1.5 rounded-full text-xs font-extrabold transition-all flex-shrink-0 flex items-center space-x-1 ${
                budgetFilter === 'under99'
                  ? 'bg-emerald-600 text-white shadow-sm ring-2 ring-emerald-400/30'
                  : 'bg-white dark:bg-[#1E293B] border border-emerald-300 dark:border-emerald-800/80 text-emerald-700 dark:text-emerald-400'
              }`}
            >
              <span>Under ₹99</span>
              <span className="bg-amber-300 text-gray-950 text-[9px] px-1 rounded font-black">PAY ₹1</span>
            </button>
            <button
              type="button"
              onClick={() => setBudgetFilter('under149')}
              className={`px-3 py-1.5 rounded-full text-xs font-extrabold transition-all flex-shrink-0 ${
                budgetFilter === 'under149'
                  ? 'bg-purple-600 text-white shadow-sm'
                  : 'bg-white dark:bg-[#1E293B] border border-gray-200 dark:border-gray-800 text-gray-700 dark:text-gray-300'
              }`}
            >
              Under ₹149
            </button>
          </div>

          {/* 3. Search Dishes in this Restaurant Input (Screenshot 4) */}
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3.5 top-3.5 text-orange-500" />
            <input
              type="text"
              placeholder="Search dishes in this restaurant"
              value={dishSearchQuery}
              onFocus={() => setIsDishSearchActive(true)}
              onClick={() => setIsDishSearchActive(true)}
              onChange={(e) => {
                setDishSearchQuery(e.target.value);
                if (!isDishSearchActive) setIsDishSearchActive(true);
              }}
              className="w-full bg-white dark:bg-[#1E293B] border border-orange-200 dark:border-orange-950/60 focus:border-orange-500 focus:ring-1 focus:ring-orange-400 rounded-2xl pl-10 pr-12 py-3 text-xs text-gray-900 dark:text-white placeholder-gray-400 shadow-sm transition-all"
            />
            {dishSearchQuery ? (
              <button
                onClick={() => setDishSearchQuery('')}
                className="absolute right-3.5 top-3 w-5 h-5 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-gray-400 hover:text-gray-600"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            ) : isDishSearchActive ? (
              <button
                type="button"
                onClick={() => setIsDishSearchActive(false)}
                className="absolute right-3.5 top-3 text-[10px] font-black uppercase text-purple-600 dark:text-purple-400 hover:underline"
              >
                Hide
              </button>
            ) : null}
          </div>

          {/* 4. "EXPLORE THIS MENU" Categories Chips (Only appear when user clicks on search dishes) */}
          {(isDishSearchActive || dishSearchQuery.trim().length > 0) && categories.length > 0 && (
            <div className="bg-white dark:bg-[#1E293B] rounded-3xl p-4 shadow-card border border-gray-100 dark:border-gray-800 space-y-2.5 animate-in fade-in slide-in-from-top-1 duration-200">
              <div className="flex items-center justify-between">
                <p className="text-[10px] font-black uppercase tracking-wider text-gray-400 dark:text-gray-500">
                  EXPLORE THIS MENU
                </p>
                <button
                  type="button"
                  onClick={() => setIsDishSearchActive(false)}
                  className="text-[10px] font-bold text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  Hide
                </button>
              </div>
              <div className="flex flex-wrap gap-2">
                {categories.map((cat) => {
                  const isActive = activeCategoryFilter === cat.name;
                  const count = cat.items?.length || 0;
                  return (
                    <button
                      key={cat.name}
                      onClick={() => scrollToCategory(cat.name)}
                      className={`px-3 py-1.5 rounded-full text-xs font-bold transition-all active:scale-95 flex items-center space-x-1.5 border ${
                        isActive
                          ? 'bg-purple-50 dark:bg-purple-950/80 border-purple-400 text-[#7C3AED] dark:text-purple-300'
                          : 'bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-800 dark:text-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <span>{cat.name}</span>
                      <span className="text-[10px] font-black text-gray-400 dark:text-gray-500">
                        {count}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* 5. Menu Categories Accordions & Dish Cards */}
          {menuLoading ? (
            <div className="py-20 flex flex-col items-center justify-center space-y-2 text-gray-400 text-xs">
              <Loader2 className="w-6 h-6 animate-spin text-[#7C3AED]" />
              <span>Fetching delicious menu items...</span>
            </div>
          ) : filteredCategories.length === 0 ? (
            <div className="bg-white dark:bg-[#1E293B] rounded-2xl p-8 border border-dashed border-gray-200 dark:border-gray-800 text-center space-y-2">
              <p className="text-xs font-bold text-gray-500 dark:text-gray-400">
                No items match your filters.
              </p>
              <p className="text-[11px] text-gray-400">
                Try disabling the Veg toggle or clearing your dish search.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredCategories.map((category) => {
                const isOpen = openCategories[category.name] !== false;

                return (
                  <div
                    key={category.name}
                    ref={(el) => (categoryRefs.current[category.name] = el)}
                    className="bg-white dark:bg-[#1E293B] rounded-3xl border border-gray-100 dark:border-gray-800 shadow-card overflow-hidden"
                  >
                    {/* Category Header Accordion Button */}
                    <button
                      onClick={() => toggleCategory(category.name)}
                      className="w-full p-4 flex items-center justify-between text-left hover:bg-gray-50 dark:hover:bg-gray-800/40 transition-colors"
                    >
                      <div className="flex items-center space-x-2">
                        <h4 className="font-black text-sm text-gray-900 dark:text-white">
                          {category.name}
                        </h4>
                        <span className="text-xs font-bold text-gray-400 dark:text-gray-500">
                          {category.items.length}
                        </span>
                      </div>
                      {isOpen ? (
                        <ChevronUp className="w-4 h-4 text-gray-400" />
                      ) : (
                        <ChevronDown className="w-4 h-4 text-gray-400" />
                      )}
                    </button>

                    {/* Dish Cards inside Accordion */}
                    {isOpen && (
                      <div className="divide-y divide-gray-100 dark:divide-gray-800 border-t border-gray-100 dark:border-gray-800">
                        {category.items.map((item) => {
                          const line = cartLines.find((l) => String(l.id) === String(item.id));
                          const quantity = line?.quantity || 0;
                          
                          // Handle price in paise vs rupees
                          const rawPrice = item.price || item.base_price || 0;
                          const price = rawPrice > 1000 ? Math.round(rawPrice / 100) : rawPrice;

                          return (
                            <div
                              key={item.id}
                              className="p-4 flex items-start justify-between space-x-3 transition-colors hover:bg-gray-50/50 dark:hover:bg-gray-800/20"
                            >
                              {/* Left: Veg/Non-Veg, Title, Price, Description */}
                              <div className="flex-1 min-w-0 pr-2 space-y-1">
                                {/* Veg Indicator (Green Square with Circle) */}
                                <div className="flex items-center space-x-1.5">
                                  {item.is_veg ? (
                                    <div className="w-3.5 h-3.5 rounded-sm border border-emerald-600 flex items-center justify-center">
                                      <div className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
                                    </div>
                                  ) : (
                                    <div className="w-3.5 h-3.5 rounded-sm border border-red-600 flex items-center justify-center">
                                      <div className="w-0 h-0 border-l-[3px] border-l-transparent border-r-[3px] border-r-transparent border-b-[6px] border-b-red-600" />
                                    </div>
                                  )}
                                </div>

                                <h5 className="font-extrabold text-xs text-gray-900 dark:text-white leading-snug">
                                  {item.name}
                                </h5>

                                <div className="flex items-center space-x-1.5">
                                  <p className="font-black text-xs text-gray-900 dark:text-white">
                                    ₹{price}
                                  </p>
                                  {price <= 99 && (
                                    <span className="bg-emerald-100 dark:bg-emerald-950/70 text-emerald-700 dark:text-emerald-300 font-black text-[9px] px-1.5 py-0.5 rounded-md inline-flex items-center space-x-0.5">
                                      <Sparkles className="w-2.5 h-2.5 text-emerald-600 dark:text-emerald-400" />
                                      <span>PAY ₹1</span>
                                    </span>
                                  )}
                                </div>

                                {item.description && (
                                  <p className="text-[11px] text-gray-500 dark:text-gray-400 line-clamp-2 leading-relaxed">
                                    {item.description}
                                  </p>
                                )}
                              </div>

                              {/* Right: Food Image with Floating ADD button */}
                              <div className="relative flex-shrink-0 w-22 h-22 flex flex-col items-center">
                                {item.image ? (
                                  <img
                                    src={item.image}
                                    alt={item.name}
                                    className="w-20 h-20 rounded-2xl object-cover bg-gray-100 dark:bg-gray-800 shadow-sm"
                                    onError={(e) => {
                                      e.target.style.display = 'none';
                                    }}
                                  />
                                ) : (
                                  <div className="w-20 h-20 rounded-2xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-gray-400">
                                    <Store className="w-6 h-6" />
                                  </div>
                                )}

                                {/* Floating ADD button / Stepper */}
                                <div className="absolute -bottom-2">
                                  {quantity === 0 ? (
                                    <button
                                      onClick={() =>
                                        onAddToCart({
                                          id: String(item.id),
                                          name: item.name,
                                          price: price,
                                          base_price: price,
                                          image: item.image,
                                          image_id: item.image_id,
                                          is_veg: item.is_veg,
                                          restaurant: {
                                            id: String(activeRest?.id || ''),
                                            name: activeRest?.name || '',
                                            area: activeRest?.area || '',
                                            image: activeRest?.image || activeRest?.cover || '',
                                            sla: activeRest?.sla || '',
                                          },
                                        })
                                      }
                                      className="bg-white hover:bg-emerald-50 text-[#059669] font-black text-xs px-4 py-1 rounded-xl border border-gray-200 dark:border-gray-700 shadow-md active:scale-95 transition-all"
                                    >
                                      ADD
                                    </button>
                                  ) : (
                                    <div className="flex items-center space-x-2 bg-[#059669] text-white px-2 py-1 rounded-xl text-xs font-bold shadow-md">
                                      <button
                                        onClick={() => onRemoveFromCart(String(item.id))}
                                        className="p-0.5 hover:opacity-80 active:scale-90"
                                      >
                                        <Minus className="w-3 h-3" />
                                      </button>
                                      <span className="font-black text-xs min-w-[14px] text-center">
                                        {quantity}
                                      </span>
                                      <button
                                        onClick={() =>
                                          onAddToCart({
                                            id: String(item.id),
                                            name: item.name,
                                            price: price,
                                            base_price: price,
                                            image: item.image,
                                            image_id: item.image_id,
                                            is_veg: item.is_veg,
                                            restaurant: {
                                              id: String(activeRest.id),
                                              name: activeRest.name,
                                              area: activeRest.area,
                                              image: activeRest.image || activeRest.cover,
                                              sla: activeRest.sla,
                                            },
                                          })
                                        }
                                        className="p-0.5 hover:opacity-80 active:scale-90"
                                      >
                                        <Plus className="w-3 h-3" />
                                      </button>
                                    </div>
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
              })}
            </div>
          )}
        </div>
      )}

      {/* 6. Floating Green Sticky Cart Bar (Screenshot 5 / reference 4) */}
      {cartTotalItems > 0 && (
        <div className="fixed bottom-16 inset-x-4 max-w-md mx-auto z-40 animate-slide-up">
          <div
            onClick={onGoToCart}
            className="bg-[#059669] hover:bg-[#047857] text-white p-3 rounded-2xl shadow-xl flex items-center justify-between cursor-pointer active:scale-[0.99] transition-all"
          >
            <div className="flex items-center space-x-2.5 min-w-0">
              <div className="w-8 h-8 rounded-xl bg-white/20 flex items-center justify-center flex-shrink-0">
                <ShoppingBag className="w-4 h-4 text-white" />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-bold truncate">
                  {cartTotalItems} {cartTotalItems === 1 ? 'item' : 'items'} ·{' '}
                  {cartLines[0]?.restaurant?.name || activeRest?.name || 'Restaurant'}
                </p>
                <p className="text-xs font-black">₹{cartTotalPrice}</p>
              </div>
            </div>

            <button className="bg-white/20 hover:bg-white/30 text-white font-extrabold text-xs px-3.5 py-1.5 rounded-xl flex items-center space-x-1 flex-shrink-0">
              <span>View Cart</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
