import React from 'react';
import { Clock, MapPin } from 'lucide-react';

export default function RestaurantList({ restaurants, loading, onSelectRestaurant }) {
  if (loading) {
    return (
      <div className="p-4 space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="animate-pulse bg-gray-100 rounded-2xl h-28 w-full" />
        ))}
      </div>
    );
  }

  if (!restaurants || restaurants.length === 0) {
    return (
      <div className="text-center py-12 px-4 text-gray-500">
        <p className="font-medium">No restaurants found.</p>
        <p className="text-sm">Try searching for popular outlets or sweet shops.</p>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-3">
      <h2 className="font-bold text-sm text-gray-500 uppercase tracking-wider mb-2">
        Available Outlets
      </h2>
      {restaurants.map((r) => (
        <div
          key={r.id}
          onClick={() => onSelectRestaurant(r)}
          className="flex items-center space-x-3 bg-white p-3 rounded-2xl border border-gray-100 shadow-sm hover:shadow transition-shadow cursor-pointer active:scale-[0.99]"
        >
          {r.image ? (
            <img
              src={r.image}
              alt={r.name}
              className="w-20 h-20 rounded-xl object-cover flex-shrink-0"
              loading="lazy"
            />
          ) : (
            <div className="w-20 h-20 rounded-xl bg-gray-100 flex items-center justify-center text-gray-400 font-bold">
              🍴
            </div>
          )}

          <div className="flex-1 min-w-0">
            <h3 className="font-bold text-gray-900 truncate text-base">{r.name}</h3>
            {r.area && (
              <div className="flex items-center text-xs text-gray-500 mt-1">
                <MapPin className="w-3 h-3 mr-1 text-gray-400" />
                <span className="truncate">{r.area}</span>
              </div>
            )}
            {r.sla && (
              <div className="flex items-center text-xs text-green-600 font-medium mt-1">
                <Clock className="w-3 h-3 mr-1" />
                <span>{r.sla}</span>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
