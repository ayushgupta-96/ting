import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { 
  MapPin, 
  X, 
  Search, 
  Crosshair, 
  ChevronRight, 
  Home, 
  Users, 
  Loader2 
} from 'lucide-react';
import { api } from '../services/api';

export default function SelectLocationModal({
  isOpen,
  onClose,
  activeAccount,
  activeAddress,
  onSelectAddress,
  onShowToast,
}) {
  const [searchFilter, setSearchFilter] = useState('');
  const [isLocating, setIsLocating] = useState(false);

  const mobile = activeAccount?.mobile || '';

  const {
    data: addressData,
    isLoading,
  } = useQuery({
    queryKey: ['addresses', mobile],
    queryFn: () => api.getAddresses(mobile),
    enabled: isOpen && !!mobile,
    staleTime: 1000 * 60 * 5,
  });

  if (!isOpen) return null;

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

  const filteredAddresses = allAddresses.filter((addr) => {
    if (!searchFilter.trim()) return true;
    const term = searchFilter.toLowerCase();
    const fullText = [
      addr.name,
      addr.receiver_name,
      addr.phone,
      addr.mobile,
      addr.formatted_address,
      addr.address,
      addr.area,
      addr.city,
      addr.annotation,
    ]
      .filter(Boolean)
      .join(' ')
      .toLowerCase();
    return fullText.includes(term);
  });

  const handleUseCurrentLocation = () => {
    if (!navigator.geolocation) {
      if (onShowToast) onShowToast('error', 'Geolocation is not supported by your browser');
      return;
    }

    setIsLocating(true);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const { latitude, longitude } = pos.coords;
        try {
          const rev = await api.reverseGeocode(latitude, longitude, mobile);
          const loc = rev?.location || {};
          const customAddr = {
            id: `gps_${Date.now()}`,
            name: activeAccount?.name || 'Current Location',
            phone: mobile,
            lat: latitude,
            lng: longitude,
            formatted_address: loc.formatted_address || `${loc.locality || 'Current Spot'}, ${loc.city || ''} ${loc.postal_code || ''}`,
            area: loc.locality || 'Current Spot',
            city: loc.city || '',
            annotation: 'Home',
            is_global: false,
          };
          onSelectAddress(customAddr);
          if (onShowToast) onShowToast('success', 'Location updated to current GPS!');
          onClose();
        } catch (err) {
          const customAddr = {
            id: `gps_${Date.now()}`,
            name: activeAccount?.name || 'Current Location',
            phone: mobile,
            lat: latitude,
            lng: longitude,
            formatted_address: `GPS Pin (${latitude.toFixed(4)}, ${longitude.toFixed(4)})`,
            area: 'Current Spot',
            annotation: 'Home',
            is_global: false,
          };
          onSelectAddress(customAddr);
          if (onShowToast) onShowToast('success', 'GPS coordinates selected!');
          onClose();
        } finally {
          setIsLocating(false);
        }
      },
      (err) => {
        setIsLocating(false);
        if (onShowToast) onShowToast('error', `Location error: ${err.message}`);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 backdrop-blur-sm animate-fade-in">
      <div className="absolute inset-0" onClick={onClose} />
      
      <div className="relative w-full max-w-md bg-white dark:bg-[#1E293B] rounded-t-[32px] p-5 shadow-2xl border-t border-gray-100 dark:border-gray-800 z-10 max-h-[85vh] flex flex-col overflow-y-auto animate-slide-up">
        {/* Drag handle */}
        <div className="w-12 h-1 bg-gray-200 dark:bg-gray-700 rounded-full mx-auto mb-4" />

        {/* Modal Header */}
        <div className="flex items-center justify-between pb-3">
          <div className="flex items-center space-x-2.5">
            <div className="w-7 h-7 rounded-full bg-purple-50 dark:bg-purple-950/60 flex items-center justify-center text-[#7C3AED] dark:text-purple-300">
              <MapPin className="w-4 h-4" />
            </div>
            <h3 className="font-black text-base text-gray-900 dark:text-white">
              Select your location
            </h3>
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-gray-500 hover:text-gray-900 dark:hover:text-white transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Search Input */}
        <div className="relative mt-2 mb-4">
          <Search className="w-4 h-4 absolute left-3.5 top-3.5 text-gray-400" />
          <input
            type="text"
            placeholder="Search for area, street name..."
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            className="w-full bg-[#F8FAFC] dark:bg-gray-800/80 border border-gray-200 dark:border-gray-700 rounded-2xl pl-10 pr-4 py-3 text-xs text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:border-purple-500 transition-all"
          />
        </div>

        {/* Use Current Location Row */}
        <button
          onClick={handleUseCurrentLocation}
          disabled={isLocating}
          className="w-full bg-white dark:bg-[#1E293B] hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-2xl p-3 border border-gray-100 dark:border-gray-800 flex items-center justify-between transition-all active:scale-[0.99] mb-4 shadow-sm"
        >
          <div className="flex items-center space-x-3 text-left">
            <div className="w-9 h-9 rounded-xl bg-purple-50 dark:bg-purple-950/60 flex items-center justify-center text-[#7C3AED] dark:text-purple-300 flex-shrink-0">
              {isLocating ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Crosshair className="w-4 h-4" />
              )}
            </div>
            <div>
              <h4 className="font-extrabold text-xs text-gray-900 dark:text-white">
                Use current location
              </h4>
              <p className="text-[11px] text-gray-400">
                {isLocating ? 'Acquiring GPS fix...' : 'Using GPS'}
              </p>
            </div>
          </div>
          <ChevronRight className="w-4 h-4 text-gray-400 flex-shrink-0" />
        </button>

        {/* Saved Addresses Header */}
        <div className="flex items-center space-x-2 my-2">
          <div className="w-4 h-4 rounded text-[#7C3AED] dark:text-purple-400 flex items-center justify-center">
            <MapPin className="w-3.5 h-3.5" />
          </div>
          <span className="font-extrabold text-xs text-gray-900 dark:text-white">
            Saved Addresses
          </span>
          <div className="flex-1 h-[1px] bg-purple-100 dark:bg-purple-950 ml-2" />
        </div>

        {/* Address Cards List */}
        {isLoading ? (
          <div className="py-12 flex flex-col items-center justify-center space-y-2 text-gray-400 text-xs">
            <Loader2 className="w-5 h-5 animate-spin text-[#7C3AED]" />
            <span>Loading addresses...</span>
          </div>
        ) : filteredAddresses.length === 0 ? (
          <div className="py-8 text-center text-xs text-gray-400">
            No addresses match your search.
          </div>
        ) : (
          <div className="space-y-3 pb-2">
            {filteredAddresses.map((addr, idx) => {
              const isSelected = activeAddress?.id === addr.id || (activeAddress?.lat === addr.lat && activeAddress?.lng === addr.lng);
              const tag = (addr.annotation || addr.tag || 'HOME').toUpperCase();
              const isHome = tag.includes('HOME');
              const isFamily = tag.includes('FRIENDS') || tag.includes('FAMILY');

              return (
                <div
                  key={addr.id || `${addr.lat}-${addr.lng}-${idx}`}
                  onClick={() => {
                    onSelectAddress(addr);
                    onClose();
                  }}
                  className={`bg-white dark:bg-[#1E293B] rounded-2xl p-4 border shadow-sm cursor-pointer transition-all active:scale-[0.99] space-y-2 flex items-start space-x-3 ${
                    isSelected
                      ? 'border-purple-400 dark:border-purple-600 ring-2 ring-purple-500/20'
                      : 'border-gray-100 dark:border-gray-800 hover:border-gray-200'
                  }`}
                >
                  <div className="w-6 h-6 rounded-full bg-purple-50 dark:bg-purple-950/60 flex items-center justify-center text-[#7C3AED] dark:text-purple-300 flex-shrink-0 mt-0.5">
                    <MapPin className="w-3.5 h-3.5" />
                  </div>

                  <div className="flex-1 min-w-0 space-y-1.5">
                    {/* Tags */}
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

                      {(addr.is_account_address || addr.is_global === false) && (
                        <span className="bg-[#D1FAE5] dark:bg-emerald-950/60 text-[#059669] dark:text-emerald-300 text-[10px] font-black px-2 py-0.5 rounded-md">
                          ACCOUNT ADDRESS
                        </span>
                      )}
                    </div>

                    {/* Name & Phone */}
                    <h4 className="font-extrabold text-xs text-gray-900 dark:text-white">
                      {addr.name || addr.receiver_name || 'Ak'} | +91 {addr.phone || addr.mobile || ''}
                    </h4>

                    {/* Formatted address */}
                    <p className="text-[11px] text-gray-500 dark:text-gray-400 leading-relaxed truncate-2-lines">
                      {addr.formatted_address || addr.address || [addr.house, addr.area, addr.landmark, addr.city].filter(Boolean).join(', ')}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
