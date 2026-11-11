import React, { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  Link2, 
  MapPin, 
  RefreshCw, 
  Trash2, 
  Home, 
  Briefcase,
  Users, 
  Compass,
  Loader2, 
  X, 
  Plus, 
  Crosshair,
  ExternalLink,
  Search,
  Check
} from 'lucide-react';
import WebApp from '@twa-dev/sdk';
import { api } from '../services/api';

export default function AddressTab({
  activeAccount,
  activeAddress,
  onSelectAddress,
  onShowToast,
}) {
  const queryClient = useQueryClient();
  const mobile = activeAccount?.mobile || '';

  // Link Import State
  const [isLinkCardOpen, setIsLinkCardOpen] = useState(false);
  const [addressLinkInput, setAddressLinkInput] = useState('');
  const [isSavingLink, setIsSavingLink] = useState(false);

  // Manual Map Modal State
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isLocating, setIsLocating] = useState(false);

  // Location search state
  const [placeSearchInput, setPlaceSearchInput] = useState('');
  const [placeSearchResults, setPlaceSearchResults] = useState([]);
  const [isSearchingPlaces, setIsSearchingPlaces] = useState(false);

  // Form Fields initialized dynamically
  const [lat, setLat] = useState(() => activeAddress?.lat || 28.4535279);
  const [lng, setLng] = useState(() => activeAddress?.lng || 77.4987012);
  const [house, setHouse] = useState('');
  const [area, setArea] = useState(() => activeAddress?.area || 'Judge Society');
  const [landmark, setLandmark] = useState('');
  const [annotation, setAnnotation] = useState('Home'); // 'Home' | 'Work' | 'Friends & Family' | 'Other'
  const [receiverName, setReceiverName] = useState(() => activeAccount?.name || 'Prince');
  const [receiverPhone, setReceiverPhone] = useState(() => activeAccount?.mobile || '');
  const [city, setCity] = useState(() => activeAddress?.city || 'Greater Noida');
  const [stateName, setStateName] = useState(() => activeAddress?.state || 'Uttar Pradesh');
  const [postalCode, setPostalCode] = useState(() => activeAddress?.postal_code || '201315');

  const mapInstanceRef = useRef(null);
  const markerRef = useRef(null);
  const searchTimeoutRef = useRef(null);

  // Sync active account details into form when changed
  useEffect(() => {
    if (activeAccount?.name && !receiverName) {
      setReceiverName(activeAccount.name);
    }
    if (activeAccount?.mobile && !receiverPhone) {
      setReceiverPhone(activeAccount.mobile);
    }
  }, [activeAccount]);

  // 1. Fetch Saved Addresses Query
  const {
    data: addressData,
    isLoading,
    isRefetching,
    refetch,
  } = useQuery({
    queryKey: ['addresses', mobile],
    queryFn: () => api.getAddresses(mobile),
    enabled: !!mobile,
    staleTime: 1000 * 60 * 2,
  });

  const globalAddrs = (addressData?.global_addresses || []).map((a) => ({
    ...a,
    is_account_address: false,
  }));
  const accountAddrs = (addressData?.account_addresses || []).map((a) => ({
    ...a,
    is_account_address: true,
  }));
  let allAddresses = [...accountAddrs, ...globalAddrs];
  if (allAddresses.length === 0 && Array.isArray(addressData?.addresses)) {
    allAddresses = addressData.addresses.map((a) => ({
      ...a,
      is_account_address: a.is_global === false || a.is_account_address === true,
    }));
  }

  // 2. Leaflet Map Lifecycle in Modal
  useEffect(() => {
    if (!isAddModalOpen) return;

    const timer = setTimeout(() => {
      const container = document.getElementById('leaflet-map-canvas');
      if (window.L && container) {
        if (mapInstanceRef.current) {
          try {
            mapInstanceRef.current.remove();
          } catch (e) {}
          mapInstanceRef.current = null;
        }

        const map = window.L.map('leaflet-map-canvas', {
          zoomControl: true,
          attributionControl: false,
        }).setView([lat, lng], 16);

        window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          maxZoom: 19,
        }).addTo(map);

        const marker = window.L.marker([lat, lng], { draggable: true }).addTo(map);
        markerRef.current = marker;

        // On marker drag
        marker.on('dragend', async (e) => {
          const pos = e.target.getLatLng();
          setLat(pos.lat);
          setLng(pos.lng);
          try {
            const rev = await api.reverseGeocode(pos.lat, pos.lng, mobile);
            const areaVal = rev?.location?.locality || rev?.area || rev?.location?.display_name || '';
            const cityVal = rev?.location?.city || rev?.city || '';
            const stateVal = rev?.location?.state || rev?.state || '';
            const postVal = rev?.location?.postal_code || rev?.postal_code || '';
            if (areaVal) setArea(areaVal);
            if (cityVal) setCity(cityVal);
            if (stateVal) setStateName(stateVal);
            if (postVal) setPostalCode(postVal);
          } catch (err) {}
        });

        // On map click
        map.on('click', async (e) => {
          const pos = e.latlng;
          setLat(pos.lat);
          setLng(pos.lng);
          if (markerRef.current) {
            markerRef.current.setLatLng(pos);
          }
          try {
            const rev = await api.reverseGeocode(pos.lat, pos.lng, mobile);
            const areaVal = rev?.location?.locality || rev?.area || rev?.location?.display_name || '';
            const cityVal = rev?.location?.city || rev?.city || '';
            const stateVal = rev?.location?.state || rev?.state || '';
            const postVal = rev?.location?.postal_code || rev?.postal_code || '';
            if (areaVal) setArea(areaVal);
            if (cityVal) setCity(cityVal);
            if (stateVal) setStateName(stateVal);
            if (postVal) setPostalCode(postVal);
          } catch (err) {}
        });

        mapInstanceRef.current = map;
      }
    }, 250);

    return () => {
      clearTimeout(timer);
      if (mapInstanceRef.current) {
        try {
          mapInstanceRef.current.remove();
        } catch (e) {}
        mapInstanceRef.current = null;
      }
    };
  }, [isAddModalOpen]);

  // 3. Search places debounced
  const handlePlaceSearchChange = (val) => {
    setPlaceSearchInput(val);
    if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current);

    if (!val || val.trim().length < 2) {
      setPlaceSearchResults([]);
      setIsSearchingPlaces(false);
      return;
    }

    setIsSearchingPlaces(true);
    searchTimeoutRef.current = setTimeout(async () => {
      try {
        const res = await api.searchLocations(val.trim());
        setPlaceSearchResults(res?.results || []);
      } catch (err) {
        setPlaceSearchResults([]);
      } finally {
        setIsSearchingPlaces(false);
      }
    }, 350);
  };

  const handleSelectSearchResult = (place) => {
    setLat(place.lat);
    setLng(place.lng);
    if (place.area || place.name) setArea(place.area || place.name);
    if (place.city) setCity(place.city);
    if (place.state) setStateName(place.state);
    if (place.postal_code) setPostalCode(place.postal_code);

    if (mapInstanceRef.current) {
      mapInstanceRef.current.flyTo([place.lat, place.lng], 16);
      if (markerRef.current) {
        markerRef.current.setLatLng([place.lat, place.lng]);
      }
    }

    setPlaceSearchResults([]);
    setPlaceSearchInput('');
  };

  // 4. Live Geolocation Trigger
  const handleGetLiveLocation = () => {
    setIsLocating(true);

    const onLocationSuccess = async (posLat, posLng) => {
      setLat(posLat);
      setLng(posLng);

      if (mapInstanceRef.current) {
        mapInstanceRef.current.setView([posLat, posLng], 17);
        if (markerRef.current) {
          markerRef.current.setLatLng([posLat, posLng]);
        }
      }

      try {
        const rev = await api.reverseGeocode(posLat, posLng, mobile);
        const areaVal = rev?.location?.locality || rev?.area || rev?.location?.display_name || '';
        const cityVal = rev?.location?.city || rev?.city || '';
        const stateVal = rev?.location?.state || rev?.state || '';
        const postVal = rev?.location?.postal_code || rev?.postal_code || '';
        if (areaVal) setArea(areaVal);
        if (cityVal) setCity(cityVal);
        if (stateVal) setStateName(stateVal);
        if (postVal) setPostalCode(postVal);
      } catch (e) {}

      setIsLocating(false);
      if (onShowToast) onShowToast('success', `GPS coordinates locked: ${posLat.toFixed(5)}, ${posLng.toFixed(5)}`);
    };

    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => onLocationSuccess(pos.coords.latitude, pos.coords.longitude),
        (err) => {
          setIsLocating(false);
          if (onShowToast) onShowToast('error', `Location error: ${err.message}`);
        },
        { enableHighAccuracy: true, timeout: 10000 }
      );
    } else {
      setIsLocating(false);
      if (onShowToast) onShowToast('error', 'Geolocation not available');
    }
  };

  // 5. Save Link Mutation
  const handleSaveLink = async (e) => {
    e.preventDefault();
    const link = addressLinkInput.trim();
    if (!link) {
      if (onShowToast) onShowToast('error', 'Please paste a valid address link');
      return;
    }

    setIsSavingLink(true);
    try {
      const res = await api.saveAddressLink(link, mobile);
      setAddressLinkInput('');
      setIsLinkCardOpen(false);
      queryClient.invalidateQueries({ queryKey: ['addresses', mobile] });
      if (res?.address) {
        onSelectAddress(res.address);
      }
      if (onShowToast) {
        onShowToast('success', res?.message || 'Address imported successfully!');
      }
    } catch (err) {
      const msg = err.response?.data?.detail || err.response?.data?.error || err.message || 'Failed to import address link';
      if (onShowToast) onShowToast('error', msg);
    } finally {
      setIsSavingLink(false);
    }
  };

  // 6. Add Address Mutation
  const addAddressMutation = useMutation({
    mutationFn: async (payload) => {
      return await api.addAddress(payload);
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['addresses', mobile] });
      setIsAddModalOpen(false);
      if (onShowToast) onShowToast('success', 'Address saved successfully!');
      if (data?.address) {
        onSelectAddress(data.address);
      }
      setHouse('');
    },
    onError: (err) => {
      const msg = err.response?.data?.detail || err.response?.data?.error || err.message || 'Failed to add address';
      if (onShowToast) onShowToast('error', msg);
    },
  });

  // 7. Delete Address Mutation
  const deleteAddressMutation = useMutation({
    mutationFn: async (id) => {
      return await api.deleteAddress(id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['addresses', mobile] });
      if (onShowToast) onShowToast('success', 'Address deleted successfully');
    },
    onError: (err) => {
      const msg = err.response?.data?.detail || err.message || 'Failed to delete address';
      if (onShowToast) onShowToast('error', msg);
    },
  });

  const handleAddSubmit = (e) => {
    e.preventDefault();
    if (!house.trim() || !area.trim() || !receiverPhone.trim()) {
      if (onShowToast) onShowToast('error', 'Please fill in flat/house, area, and receiver phone.');
      return;
    }

    const fullAddrParts = [house.trim(), area.trim(), landmark.trim(), city, stateName, postalCode].filter(Boolean);
    const fullAddress = fullAddrParts.join(', ');

    const payload = {
      mobile: mobile,
      house: house.trim(),
      flat_no: house.trim(),
      area: area.trim(),
      locality: area.trim(),
      landmark: landmark.trim(),
      annotation: annotation.toUpperCase(),
      tag: annotation.toUpperCase(),
      lat: parseFloat(lat),
      lng: parseFloat(lng),
      name: receiverName.trim() || activeAccount?.name || 'User',
      receiver_name: receiverName.trim() || activeAccount?.name || 'User',
      receiver_mobile: receiverPhone.trim(),
      phone: receiverPhone.trim(),
      instructions: '',
      formatted_address: fullAddress,
      address: fullAddress,
      city: city || 'Greater Noida',
      state: stateName || 'Uttar Pradesh',
      postal_code: postalCode || '',
    };

    addAddressMutation.mutate(payload);
  };

  const tagOptions = [
    { label: 'Home', icon: Home },
    { label: 'Work', icon: Briefcase },
    { label: 'Friends & Family', icon: Users },
    { label: 'Other', icon: MapPin },
  ];

  return (
    <div className="space-y-4 pb-24 animate-fade-in">
      {/* 1. Add by Address Link Card */}
      <div className="bg-white dark:bg-[#1E293B] rounded-3xl p-4 shadow-card border border-gray-100 dark:border-gray-800 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-2xl bg-purple-50 dark:bg-purple-950/60 flex items-center justify-center text-[#7C3AED] dark:text-purple-300">
              <Link2 className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-extrabold text-sm text-gray-900 dark:text-white">
                Add by Address Link
              </h3>
              <p className="text-[11px] text-gray-500 dark:text-gray-400">
                Paste Swiggy deep link to auto-fill
              </p>
            </div>
          </div>
          <button
            onClick={() => setIsLinkCardOpen((prev) => !prev)}
            className="bg-[#F3E8FF] dark:bg-purple-950/80 hover:bg-purple-200 text-[#7C3AED] dark:text-purple-300 font-extrabold text-xs px-3.5 py-1.5 rounded-xl transition-all active:scale-95 flex-shrink-0"
          >
            {isLinkCardOpen ? 'Close' : 'Add +'}
          </button>
        </div>

        {isLinkCardOpen && (
          <form onSubmit={handleSaveLink} className="space-y-2 pt-2 border-t border-gray-100 dark:border-gray-800">
            <input
              type="url"
              placeholder="e.g. https://swiggy.onelink.me/JgkQ/..."
              value={addressLinkInput}
              onChange={(e) => setAddressLinkInput(e.target.value)}
              className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-3 py-2 text-xs text-gray-900 dark:text-white focus:outline-none focus:border-purple-500 font-mono"
              required
            />
            <button
              type="submit"
              disabled={isSavingLink}
              className="w-full bg-[#7C3AED] hover:bg-purple-700 text-white font-extrabold text-xs py-2.5 rounded-xl shadow-sm flex items-center justify-center space-x-1.5 transition-all active:scale-[0.99]"
            >
              {isSavingLink ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Saving Link...</span>
                </>
              ) : (
                <>
                  <ExternalLink className="w-3.5 h-3.5" />
                  <span>Extract Address / Save Link</span>
                </>
              )}
            </button>
          </form>
        )}
      </div>

      {/* 2. Add Manually on Map Card (GPS & Map Pinning) */}
      <div className="bg-white dark:bg-[#1E293B] rounded-3xl p-4 shadow-card border border-gray-100 dark:border-gray-800 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-2xl bg-[#ECFDF5] dark:bg-emerald-950/60 flex items-center justify-center text-[#059669] dark:text-emerald-300">
            <MapPin className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-extrabold text-sm text-gray-900 dark:text-white">
              Add Manually on Map
            </h3>
            <p className="text-[11px] text-gray-500 dark:text-gray-400">
              Interactive map, search & pinpoint
            </p>
          </div>
        </div>
        <button
          onClick={() => {
            setIsAddModalOpen(true);
            handleGetLiveLocation();
          }}
          className="bg-[#D1FAE5] dark:bg-emerald-950/80 hover:bg-emerald-200 text-[#059669] dark:text-emerald-300 font-extrabold text-xs px-3.5 py-1.5 rounded-xl transition-all active:scale-95 flex-shrink-0"
        >
          Add +
        </button>
      </div>

      {/* 3. Saved Addresses Header with Refresh */}
      <div className="flex items-center justify-between px-1 pt-1">
        <div className="flex items-center space-x-2">
          <div className="w-5 h-5 rounded bg-purple-100 dark:bg-purple-950 flex items-center justify-center text-[#7C3AED] dark:text-purple-400">
            <MapPin className="w-3.5 h-3.5" />
          </div>
          <span className="font-extrabold text-sm text-gray-900 dark:text-white">
            Saved Addresses
          </span>
          <span className="text-xs text-gray-400 font-bold">({allAddresses.length})</span>
        </div>

        <button
          onClick={() => refetch()}
          disabled={isRefetching}
          className="flex items-center space-x-1 text-xs font-bold text-[#7C3AED] dark:text-purple-400 hover:text-purple-700 active:scale-95 transition-all"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefetching ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* 4. Address Cards List */}
      {isLoading ? (
        <div className="py-20 flex flex-col items-center justify-center space-y-2 text-gray-400 text-xs">
          <Loader2 className="w-6 h-6 animate-spin text-[#7C3AED]" />
          <span>Loading delivery addresses...</span>
        </div>
      ) : allAddresses.length === 0 ? (
        <div className="bg-white dark:bg-[#1E293B] rounded-2xl p-8 border border-dashed border-gray-200 dark:border-gray-800 text-center space-y-2">
          <p className="text-xs font-bold text-gray-500 dark:text-gray-400">
            No saved addresses found for this account.
          </p>
          <p className="text-[11px] text-gray-400 dark:text-gray-500">
            Add an address via Map or Link to start ordering.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {allAddresses.map((addr, idx) => {
            const isSelected = activeAddress?.id === addr.id || (activeAddress?.lat === addr.lat && activeAddress?.lng === addr.lng);
            const tag = (addr.annotation || addr.tag || 'HOME').toUpperCase();
            const isHome = tag.includes('HOME');
            const isWork = tag.includes('WORK');
            const isFamily = tag.includes('FRIENDS') || tag.includes('FAMILY');

            return (
              <div
                key={addr.id || `${addr.lat}-${addr.lng}-${idx}`}
                onClick={() => onSelectAddress(addr)}
                className={`bg-white dark:bg-[#1E293B] rounded-2xl p-4 border shadow-card cursor-pointer transition-all active:scale-[0.99] space-y-2 ${
                  isSelected
                    ? 'border-[#7C3AED] dark:border-purple-500 ring-2 ring-purple-500/20'
                    : 'border-gray-100 dark:border-gray-800 hover:border-gray-200'
                }`}
              >
                {/* Tags row */}
                <div className="flex items-center space-x-1.5 flex-wrap gap-y-1">
                  {isHome ? (
                    <span className="bg-[#7C3AED] text-white text-[10px] font-extrabold px-2 py-0.5 rounded-md flex items-center space-x-1">
                      <Home className="w-3 h-3 inline mr-0.5" />
                      <span>HOME</span>
                    </span>
                  ) : isWork ? (
                    <span className="bg-blue-600 text-white text-[10px] font-extrabold px-2 py-0.5 rounded-md flex items-center space-x-1">
                      <Briefcase className="w-3 h-3 inline mr-0.5" />
                      <span>WORK</span>
                    </span>
                  ) : isFamily ? (
                    <span className="bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 text-[10px] font-extrabold px-2 py-0.5 rounded-md flex items-center space-x-1">
                      <Users className="w-3 h-3 inline mr-0.5" />
                      <span>FRIENDS & FAMILY</span>
                    </span>
                  ) : (
                    <span className="bg-[#7C3AED] text-white text-[10px] font-extrabold px-2 py-0.5 rounded-md">
                      {tag}
                    </span>
                  )}

                  {addr.is_account_address && (
                    <span className="bg-[#D1FAE5] dark:bg-emerald-950/60 text-[#059669] dark:text-emerald-300 text-[10px] font-black px-2 py-0.5 rounded-md">
                      ACCOUNT ADDRESS
                    </span>
                  )}

                  {isSelected && (
                    <span className="bg-purple-100 dark:bg-purple-900/60 text-[#7C3AED] dark:text-purple-300 text-[10px] font-black px-2 py-0.5 rounded-md flex items-center space-x-0.5">
                      <Check className="w-3 h-3 inline" />
                      <span>DELIVERING HERE</span>
                    </span>
                  )}
                </div>

                {/* Name & Phone header */}
                <div className="flex items-center justify-between">
                  <h4 className="font-extrabold text-sm text-gray-900 dark:text-white">
                    {addr.name || addr.receiver_name || 'Prince'} | +91 {addr.phone || addr.mobile || addr.receiver_mobile || ''}
                  </h4>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      if (addr.id) {
                        deleteAddressMutation.mutate(addr.id);
                      } else {
                        if (onShowToast) onShowToast('info', 'Address removed');
                      }
                    }}
                    disabled={deleteAddressMutation.isPending}
                    className="p-1.5 text-gray-400 hover:text-red-500 rounded-lg hover:bg-red-50 dark:hover:bg-red-950/40 transition-colors"
                    aria-label="Delete address"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>

                {/* Full Address details */}
                <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed font-normal">
                  {addr.formatted_address || addr.address || [addr.house, addr.area, addr.landmark, addr.city].filter(Boolean).join(', ')}
                </p>
              </div>
            );
          })}
        </div>
      )}

      {/* 5. Precise Map Pinning Modal Sheet (Modern & Complete UI) */}
      {isAddModalOpen && typeof document !== 'undefined' && createPortal(
        <div className="fixed inset-0 z-[100] flex items-end justify-center bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="absolute inset-0" onClick={() => setIsAddModalOpen(false)} />
          <div className="relative w-full max-w-md bg-white dark:bg-[#1E293B] rounded-t-[32px] p-5 pb-8 shadow-2xl border-t border-gray-100 dark:border-gray-800 z-10 max-h-[90vh] flex flex-col overflow-y-auto animate-slide-up">
            <div className="w-12 h-1 bg-gray-300 dark:bg-gray-600 rounded-full mx-auto mb-3" />
            
            {/* Modal Header */}
            <div className="flex items-center justify-between pb-3 border-b border-gray-100 dark:border-gray-800">
              <div className="flex items-center space-x-2">
                <div className="w-7 h-7 rounded-lg bg-purple-50 dark:bg-purple-950 flex items-center justify-center text-[#7C3AED]">
                  <Compass className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="font-black text-sm text-gray-900 dark:text-white">
                    Pin Location on Map
                  </h3>
                  <p className="text-[10px] text-gray-400">Drag pin or search locality</p>
                </div>
              </div>
              <button
                onClick={() => setIsAddModalOpen(false)}
                className="w-7 h-7 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-gray-500 hover:text-gray-700"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Place Search Bar */}
            <div className="relative mt-3">
              <div className="flex items-center bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl px-3 py-2 text-xs focus-within:border-[#7C3AED]">
                <Search className="w-4 h-4 text-gray-400 mr-2 flex-shrink-0" />
                <input
                  type="text"
                  placeholder="Search society, street or locality..."
                  value={placeSearchInput}
                  onChange={(e) => handlePlaceSearchChange(e.target.value)}
                  className="w-full bg-transparent text-gray-900 dark:text-white focus:outline-none text-xs"
                />
                {isSearchingPlaces && <Loader2 className="w-3.5 h-3.5 animate-spin text-[#7C3AED] ml-1" />}
                {placeSearchInput && !isSearchingPlaces && (
                  <button onClick={() => { setPlaceSearchInput(''); setPlaceSearchResults([]); }}>
                    <X className="w-3.5 h-3.5 text-gray-400" />
                  </button>
                )}
              </div>

              {/* Suggestions Dropdown */}
              {placeSearchResults.length > 0 && (
                <div className="absolute top-full left-0 right-0 mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl shadow-xl z-20 max-h-48 overflow-y-auto divide-y divide-gray-100 dark:divide-gray-700">
                  {placeSearchResults.map((p, pIdx) => (
                    <button
                      key={pIdx}
                      type="button"
                      onClick={() => handleSelectSearchResult(p)}
                      className="w-full text-left p-2.5 hover:bg-purple-50 dark:hover:bg-purple-950/40 flex items-start space-x-2 transition-colors"
                    >
                      <MapPin className="w-3.5 h-3.5 text-[#7C3AED] mt-0.5 flex-shrink-0" />
                      <div className="min-w-0 flex-1">
                        <div className="font-bold text-xs text-gray-900 dark:text-white truncate">{p.name || p.area}</div>
                        <div className="text-[10px] text-gray-400 truncate">{p.display_name}</div>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Map Preview Container */}
            <div className="mt-3 relative rounded-2xl overflow-hidden border border-gray-200 dark:border-gray-700 shadow-sm h-56 bg-gray-100 dark:bg-gray-800">
              <div id="leaflet-map-canvas" className="w-full h-full z-0" />
              <button
                type="button"
                onClick={handleGetLiveLocation}
                disabled={isLocating}
                className="absolute top-2 right-2 z-10 bg-white/95 dark:bg-gray-800/95 backdrop-blur-sm border border-gray-200 dark:border-gray-700 text-[#7C3AED] dark:text-purple-300 px-3 py-1.5 rounded-xl shadow-md text-xs font-black flex items-center space-x-1.5 active:scale-95 transition-all"
              >
                <Crosshair className={`w-3.5 h-3.5 ${isLocating ? 'animate-spin' : ''}`} />
                <span>{isLocating ? 'Locating...' : 'Use Current GPS'}</span>
              </button>
              <div className="absolute bottom-2 left-2 right-2 z-10 bg-black/60 backdrop-blur-md rounded-xl p-1.5 text-[10px] text-white text-center font-mono truncate">
                Pin: {lat.toFixed(5)}, {lng.toFixed(5)}
              </div>
            </div>

            {/* Detected Location Card */}
            <div className="mt-3 bg-purple-50/60 dark:bg-purple-950/30 border border-purple-100 dark:border-purple-900/50 rounded-2xl p-3 flex items-start space-x-2.5">
              <div className="w-6 h-6 rounded-lg bg-[#7C3AED] text-white flex items-center justify-center flex-shrink-0 mt-0.5">
                <MapPin className="w-3.5 h-3.5" />
              </div>
              <div className="min-w-0 flex-1">
                <h4 className="font-extrabold text-xs text-gray-900 dark:text-white truncate">
                  {area || 'Selected Location'}
                </h4>
                <p className="text-[11px] text-gray-500 dark:text-gray-400 truncate">
                  {city ? `${city}, ${stateName} ${postalCode}` : `${lat.toFixed(4)}, ${lng.toFixed(4)}`}
                </p>
              </div>
            </div>

            {/* Detailed Address Form */}
            <form onSubmit={handleAddSubmit} className="space-y-3 mt-3">
              {/* Tag Selector */}
              <div>
                <label className="block text-[11px] font-bold text-gray-500 uppercase mb-1.5">
                  Save Address As
                </label>
                <div className="grid grid-cols-4 gap-1.5">
                  {tagOptions.map(({ label, icon: IconComponent }) => {
                    const isSelected = annotation.toLowerCase() === label.toLowerCase();
                    return (
                      <button
                        key={label}
                        type="button"
                        onClick={() => setAnnotation(label)}
                        className={`py-2 px-1 rounded-xl text-xs font-extrabold flex flex-col items-center justify-center space-y-1 transition-all ${
                          isSelected
                            ? 'bg-[#7C3AED] text-white shadow-sm ring-2 ring-purple-500/20'
                            : 'bg-gray-50 dark:bg-gray-800 text-gray-600 dark:text-gray-300 border border-gray-100 dark:border-gray-700 hover:border-gray-200'
                        }`}
                      >
                        <IconComponent className="w-3.5 h-3.5" />
                        <span className="text-[10px] leading-tight truncate">{label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Flat / House */}
              <div>
                <label className="block text-[11px] font-bold text-gray-500 uppercase mb-1">
                  Flat / House / Building / Floor No. *
                </label>
                <input
                  type="text"
                  placeholder="e.g. E6 Silver Oaks, Flat 204"
                  value={house}
                  onChange={(e) => setHouse(e.target.value)}
                  className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-3 py-2 text-xs text-gray-900 dark:text-white focus:outline-none focus:border-purple-500 font-medium"
                  required
                />
              </div>

              {/* Area / Locality */}
              <div>
                <label className="block text-[11px] font-bold text-gray-500 uppercase mb-1">
                  Area / Sector / Society *
                </label>
                <input
                  type="text"
                  placeholder="e.g. Near Judge Society, Alpha 1"
                  value={area}
                  onChange={(e) => setArea(e.target.value)}
                  className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-3 py-2 text-xs text-gray-900 dark:text-white focus:outline-none focus:border-purple-500 font-medium"
                  required
                />
              </div>

              {/* Landmark */}
              <div>
                <label className="block text-[11px] font-bold text-gray-500 uppercase mb-1">
                  Landmark (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Opposite Community Center"
                  value={landmark}
                  onChange={(e) => setLandmark(e.target.value)}
                  className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-3 py-2 text-xs text-gray-900 dark:text-white focus:outline-none focus:border-purple-500 font-medium"
                />
              </div>

              {/* Receiver Info */}
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[11px] font-bold text-gray-500 uppercase mb-1">
                    Receiver Name
                  </label>
                  <input
                    type="text"
                    value={receiverName}
                    onChange={(e) => setReceiverName(e.target.value)}
                    className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-3 py-2 text-xs text-gray-900 dark:text-white focus:outline-none focus:border-purple-500 font-medium"
                    required
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-bold text-gray-500 uppercase mb-1">
                    Receiver Phone
                  </label>
                  <input
                    type="tel"
                    value={receiverPhone}
                    onChange={(e) => setReceiverPhone(e.target.value)}
                    className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-3 py-2 text-xs text-gray-900 dark:text-white focus:outline-none focus:border-purple-500 font-medium"
                    maxLength={10}
                    required
                  />
                </div>
              </div>

              {/* Submit CTA */}
              <button
                type="submit"
                disabled={addAddressMutation.isPending}
                className="w-full bg-gradient-to-r from-[#9061F9] to-[#7E3AF2] hover:from-[#8250f5] hover:to-[#7030e5] text-white font-black py-3.5 rounded-2xl shadow-lg shadow-purple-500/25 flex items-center justify-center space-x-2 active:scale-[0.99] transition-all cursor-pointer mt-2"
              >
                {addAddressMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Saving Address...</span>
                  </>
                ) : (
                  <>
                    <Plus className="w-4 h-4" />
                    <span>Save Address</span>
                  </>
                )}
              </button>
            </form>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
}
