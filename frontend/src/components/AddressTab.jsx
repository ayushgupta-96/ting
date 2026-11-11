import React, { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  Link2, 
  MapPin, 
  RefreshCw, 
  Trash2, 
  Home, 
  Users, 
  Loader2, 
  X, 
  Plus, 
  Crosshair,
  ExternalLink,
  ChevronDown,
  ChevronUp
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

  // Form Fields initialized dynamically from active location if present
  const [lat, setLat] = useState(() => activeAddress?.lat || 28.4535279);
  const [lng, setLng] = useState(() => activeAddress?.lng || 77.4987012);
  const [house, setHouse] = useState('');
  const [area, setArea] = useState(() => activeAddress?.area || '');
  const [landmark, setLandmark] = useState('');
  const [annotation, setAnnotation] = useState('Home'); // 'Home' | 'Friends & Family' | 'Other'
  const [receiverName, setReceiverName] = useState(activeAccount?.name || 'Self');
  const [receiverPhone, setReceiverPhone] = useState(activeAccount?.mobile || '');
  const [city, setCity] = useState(() => activeAddress?.city || '');
  const [stateName, setStateName] = useState(() => activeAddress?.state || '');
  const [postalCode, setPostalCode] = useState(() => activeAddress?.postal_code || '');

  const mapInstanceRef = useRef(null);
  const markerRef = useRef(null);

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
    staleTime: 1000 * 60 * 5,
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
          mapInstanceRef.current.remove();
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

        marker.on('dragend', async (e) => {
          const pos = e.target.getLatLng();
          setLat(pos.lat);
          setLng(pos.lng);
          try {
            const rev = await api.reverseGeocode(pos.lat, pos.lng, mobile);
            if (rev?.location) {
              if (rev.location.locality) setArea(rev.location.locality);
              if (rev.location.city) setCity(rev.location.city);
              if (rev.location.state) setStateName(rev.location.state);
              if (rev.location.postal_code) setPostalCode(rev.location.postal_code);
            }
          } catch (err) {
            // ignore
          }
        });

        mapInstanceRef.current = map;
      }
    }, 250);

    return () => {
      clearTimeout(timer);
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [isAddModalOpen]);

  // 3. Live Geolocation Trigger (Telegram SDK or Browser API)
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
        if (rev?.location) {
          if (rev.location.locality) setArea(rev.location.locality);
          if (rev.location.city) setCity(rev.location.city);
          if (rev.location.state) setStateName(rev.location.state);
          if (rev.location.postal_code) setPostalCode(rev.location.postal_code);
        }
      } catch (e) {
        // ignore
      }

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

  // 4. Save Link Mutation (Swiggy Deep Link mapped directly to Toing add_link)
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
        onShowToast(res?.success ? 'success' : 'info', res?.message || 'Address imported successfully!');
      }
    } catch (err) {
      const msg = err.response?.data?.detail || err.response?.data?.error || err.message || 'Failed to import address link';
      if (onShowToast) onShowToast('error', msg);
    } finally {
      setIsSavingLink(false);
    }
  };

  // 5. Add Address Mutation (exact payload mapped from HAR)
  const addAddressMutation = useMutation({
    mutationFn: async (payload) => {
      return await api.addAddress(payload);
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['addresses', mobile] });
      setIsAddModalOpen(false);
      if (onShowToast) onShowToast('success', 'Address added successfully!');
      if (data?.address) {
        onSelectAddress(data.address);
      }
      setHouse('');
      setArea('');
      setLandmark('');
    },
    onError: (err) => {
      const msg = err.response?.data?.detail || err.response?.data?.error || err.message || 'Failed to add address';
      if (onShowToast) onShowToast('error', msg);
    },
  });

  // 6. Delete Address Mutation
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
      if (onShowToast) onShowToast('error', 'Please fill in house, area, and receiver phone.');
      return;
    }

    const payload = {
      mobile: mobile,
      house: house.trim(),
      area: area.trim(),
      landmark: landmark.trim(),
      annotation: annotation,
      lat: parseFloat(lat),
      lng: parseFloat(lng),
      name: receiverName.trim(),
      receiver_mobile: receiverPhone.trim(),
      instructions: '',
      formatted_address: `${house.trim()}, ${area.trim()}, ${city}, ${stateName} ${postalCode}, India`,
      locality: area.trim(),
      city: city,
      state: stateName,
      postal_code: postalCode,
    };

    addAddressMutation.mutate(payload);
  };

  return (
    <div className="space-y-4 pb-24 animate-fade-in">
      {/* 1. Add by Address Link Card (Updated with URL Input) */}
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
              Live GPS pinpoint & precise location
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
            const isFamily = tag.includes('FRIENDS') || tag.includes('FAMILY');

            return (
              <div
                key={addr.id || `${addr.lat}-${addr.lng}-${idx}`}
                onClick={() => onSelectAddress(addr)}
                className={`bg-white dark:bg-[#1E293B] rounded-2xl p-4 border shadow-card cursor-pointer transition-all active:scale-[0.99] space-y-2 ${
                  isSelected
                    ? 'border-purple-400 dark:border-purple-600 ring-2 ring-purple-500/20'
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
                </div>

                {/* Name & Phone header */}
                <div className="flex items-center justify-between">
                  <h4 className="font-extrabold text-sm text-gray-900 dark:text-white">
                    {addr.name || addr.receiver_name || 'Ak'} | +91 {addr.phone || addr.mobile || ''}
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
                    className="p-1 text-gray-400 hover:text-red-500 transition-colors"
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

      {/* 5. Precise Map Pinning Modal Sheet */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 backdrop-blur-sm animate-fade-in">
          <div className="absolute inset-0" onClick={() => setIsAddModalOpen(false)} />
          <div className="relative w-full max-w-md bg-white dark:bg-[#1E293B] rounded-t-[28px] p-5 shadow-2xl border-t border-gray-100 dark:border-gray-800 z-10 max-h-[92vh] flex flex-col overflow-y-auto animate-slide-up">
            <div className="w-12 h-1 bg-gray-300 dark:bg-gray-600 rounded-full mx-auto mb-3" />
            <div className="flex items-center justify-between pb-3 border-b border-gray-100 dark:border-gray-800">
              <h3 className="font-black text-base text-gray-900 dark:text-white">
                Pin Location on Map
              </h3>
              <button
                onClick={() => setIsAddModalOpen(false)}
                className="w-7 h-7 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-gray-500"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Map Preview Container */}
            <div className="mt-3 relative rounded-2xl overflow-hidden border border-gray-200 dark:border-gray-700 shadow-sm h-48 bg-gray-100 dark:bg-gray-800">
              <div id="leaflet-map-canvas" className="w-full h-full z-0" />
              <button
                type="button"
                onClick={handleGetLiveLocation}
                disabled={isLocating}
                className="absolute top-2 right-2 z-10 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-purple-600 px-3 py-1.5 rounded-xl shadow-md text-xs font-black flex items-center space-x-1.5 active:scale-95 transition-all"
              >
                <Crosshair className={`w-3.5 h-3.5 ${isLocating ? 'animate-spin' : ''}`} />
                <span>{isLocating ? 'Locating...' : 'Use Current GPS'}</span>
              </button>
              <div className="absolute bottom-2 left-2 right-2 z-10 bg-black/60 backdrop-blur-md rounded-xl p-1.5 text-[10px] text-white text-center font-mono truncate">
                Pin: {lat.toFixed(5)}, {lng.toFixed(5)}
              </div>
            </div>

            <form onSubmit={handleAddSubmit} className="space-y-3 mt-3">
              <div>
                <label className="block text-[11px] font-bold text-gray-500 uppercase mb-1">
                  Tag
                </label>
                <div className="flex items-center space-x-2">
                  {['Home', 'Friends & Family', 'Other'].map((t) => (
                    <button
                      key={t}
                      type="button"
                      onClick={() => setAnnotation(t)}
                      className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
                        annotation === t
                          ? 'bg-[#7C3AED] text-white shadow-sm'
                          : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300'
                      }`}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-gray-500 uppercase mb-1">
                  Flat / House / Building No.
                </label>
                <input
                  type="text"
                  placeholder="e.g. E6, Flat 204"
                  value={house}
                  onChange={(e) => setHouse(e.target.value)}
                  className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-3 py-2 text-xs text-gray-900 dark:text-white focus:outline-none focus:border-purple-500"
                  required
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-gray-500 uppercase mb-1">
                  Area / Locality
                </label>
                <input
                  type="text"
                  placeholder="e.g. Judge Society, Knowledge Park"
                  value={area}
                  onChange={(e) => setArea(e.target.value)}
                  className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-3 py-2 text-xs text-gray-900 dark:text-white focus:outline-none focus:border-purple-500"
                  required
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-gray-500 uppercase mb-1">
                  Landmark (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Near metro station"
                  value={landmark}
                  onChange={(e) => setLandmark(e.target.value)}
                  className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-3 py-2 text-xs text-gray-900 dark:text-white focus:outline-none focus:border-purple-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[11px] font-bold text-gray-500 uppercase mb-1">
                    Receiver Name
                  </label>
                  <input
                    type="text"
                    value={receiverName}
                    onChange={(e) => setReceiverName(e.target.value)}
                    className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-3 py-2 text-xs text-gray-900 dark:text-white focus:outline-none focus:border-purple-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-bold text-gray-500 uppercase mb-1">
                    Receiver Mobile
                  </label>
                  <input
                    type="tel"
                    value={receiverPhone}
                    onChange={(e) => setReceiverPhone(e.target.value)}
                    className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-3 py-2 text-xs text-gray-900 dark:text-white focus:outline-none focus:border-purple-500"
                    maxLength={10}
                    required
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={addAddressMutation.isPending}
                className="w-full bg-gradient-to-r from-[#9061F9] to-[#7E3AF2] text-white font-black py-3 rounded-2xl shadow-lg shadow-purple-500/25 flex items-center justify-center space-x-2 active:scale-[0.99] transition-all"
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
        </div>
      )}
    </div>
  );
}
