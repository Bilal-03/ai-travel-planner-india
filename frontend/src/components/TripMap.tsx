"use client";

import { useEffect, useRef, useState } from "react";
import { DayPlan, RouteSegment, GeoPoint } from "@/lib/api";

interface TripMapProps {
  center: GeoPoint;
  dayPlans: DayPlan[];
  routeSegments: RouteSegment[];
  destination: string;
}

// Day colors for routes
const DAY_COLORS = [
  "#6366f1", "#8b5cf6", "#06b6d4", "#22c55e",
  "#f59e0b", "#ec4899", "#ef4444", "#14b8a6",
];

export default function TripMap({
  center,
  dayPlans,
  routeSegments,
  destination,
}: TripMapProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const [selectedDay, setSelectedDay] = useState<number | null>(null);
  const [L, setL] = useState<any>(null);

  // Store markers and polylines grouped by day index
  const dayLayersRef = useRef<Map<number, any[]>>(new Map());
  // Store route polylines (not per-day)
  const routeLayersRef = useRef<any[]>([]);
  // Store all points for bounds fitting per day
  const dayPointsRef = useRef<Map<number, [number, number][]>>(new Map());

  useEffect(() => {
    // Dynamic import of Leaflet (client-only)
    import("leaflet").then((leaflet) => {
      setL(leaflet.default);
    });
  }, []);

  useEffect(() => {
    if (!L || !mapRef.current || mapInstanceRef.current) return;

    // Initialize map
    const map = L.map(mapRef.current, {
      center: [center.lat, center.lng],
      zoom: 12,
      zoomControl: true,
      attributionControl: true,
    });

    // Dark-themed OSM tiles
    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      attribution:
        '&copy; <a href="https://carto.com/">CARTO</a> &copy; <a href="https://osm.org/copyright">OSM</a>',
      subdomains: "abcd",
      maxZoom: 19,
    }).addTo(map);

    mapInstanceRef.current = map;

    // Clear previous layer refs
    dayLayersRef.current = new Map();
    dayPointsRef.current = new Map();
    routeLayersRef.current = [];

    const allPoints: [number, number][] = [];

    // Add markers for all activities, grouped by day
    dayPlans.forEach((day, dayIdx) => {
      const color = DAY_COLORS[dayIdx % DAY_COLORS.length];
      const dayMarkers: any[] = [];
      const dayPoints: [number, number][] = [];

      day.activities.forEach((act) => {
        const { lat, lng } = act.poi.coordinates;
        if (lat === 0 && lng === 0) return;

        allPoints.push([lat, lng]);
        dayPoints.push([lat, lng]);

        const icon = L.divIcon({
          className: "custom-marker",
          html: `<div style="
            background: ${color};
            color: white;
            width: 28px;
            height: 28px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: bold;
            border: 2px solid white;
            box-shadow: 0 2px 8px rgba(0,0,0,0.4);
          ">D${day.day_number}</div>`,
          iconSize: [28, 28],
          iconAnchor: [14, 14],
        });

        const marker = L.marker([lat, lng], { icon })
          .addTo(map)
          .bindPopup(
            `<div style="font-family: system-ui; padding: 4px;">
              <strong>${act.poi.name}</strong><br/>
              <span style="opacity: 0.7">Day ${day.day_number} • ${act.poi.category}</span>
              ${act.start_time ? `<br/><span style="opacity: 0.7">${act.start_time} – ${act.end_time || ""}</span>` : ""}
            </div>`
          );

        dayMarkers.push(marker);
      });

      dayLayersRef.current.set(dayIdx, dayMarkers);
      dayPointsRef.current.set(dayIdx, dayPoints);
    });

    // Draw route segments
    routeSegments.forEach((seg, idx) => {
      if (seg.geometry && seg.geometry.length > 0) {
        const coords = seg.geometry.map(
          (p: number[]) => [p[1], p[0]] as [number, number]
        );
        const polyline = L.polyline(coords, {
          color: DAY_COLORS[idx % DAY_COLORS.length],
          weight: 3,
          opacity: 0.7,
          dashArray: "5, 10",
        }).addTo(map);
        routeLayersRef.current.push(polyline);
      }
    });

    // Fit bounds to all markers
    if (allPoints.length > 0) {
      const bounds = L.latLngBounds(allPoints);
      map.fitBounds(bounds, { padding: [30, 30] });
    }

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [L, center, dayPlans, routeSegments]);

  // React to day filter changes — show/hide markers per day
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !L) return;

    // Toggle marker visibility per day
    dayLayersRef.current.forEach((markers, dayIdx) => {
      markers.forEach((marker: any) => {
        if (selectedDay === null || selectedDay === dayIdx) {
          // Show marker
          if (!map.hasLayer(marker)) {
            marker.addTo(map);
          }
        } else {
          // Hide marker
          if (map.hasLayer(marker)) {
            map.removeLayer(marker);
          }
        }
      });
    });

    // Toggle route segment visibility
    routeLayersRef.current.forEach((polyline: any, idx: number) => {
      if (selectedDay === null || selectedDay === idx) {
        if (!map.hasLayer(polyline)) {
          polyline.addTo(map);
        }
      } else {
        if (map.hasLayer(polyline)) {
          map.removeLayer(polyline);
        }
      }
    });

    // Fit bounds to visible points
    if (selectedDay !== null) {
      const dayPoints = dayPointsRef.current.get(selectedDay);
      if (dayPoints && dayPoints.length > 0) {
        const bounds = L.latLngBounds(dayPoints);
        map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 });
      }
    } else {
      // Show all — fit to all points
      const allPoints: [number, number][] = [];
      dayPointsRef.current.forEach((points) => {
        allPoints.push(...points);
      });
      if (allPoints.length > 0) {
        const bounds = L.latLngBounds(allPoints);
        map.fitBounds(bounds, { padding: [30, 30] });
      }
    }
  }, [selectedDay, L]);

  return (
    <div className="glass rounded-xl overflow-hidden">
      <div className="flex items-center justify-between p-4 border-b border-glass-border">
        <h3 className="font-bold font-[family-name:var(--font-outfit)] text-foreground flex items-center gap-2">
          🗺️ Trip Map — {destination}
        </h3>

        {/* Day filter buttons */}
        <div className="flex gap-1.5">
          <button
            onClick={() => setSelectedDay(null)}
            className={`px-2 py-1 rounded-md text-xs transition-colors ${
              selectedDay === null
                ? "bg-primary text-white"
                : "bg-glass-bg text-foreground-muted hover:bg-glass-highlight"
            }`}
          >
            All
          </button>
          {dayPlans.map((_, idx) => (
            <button
              key={idx}
              onClick={() => setSelectedDay(idx)}
              className={`px-2 py-1 rounded-md text-xs transition-colors ${
                selectedDay === idx
                  ? "text-white"
                  : "bg-glass-bg text-foreground-muted hover:bg-glass-highlight"
              }`}
              style={
                selectedDay === idx
                  ? { backgroundColor: DAY_COLORS[idx % DAY_COLORS.length] }
                  : {}
              }
            >
              D{idx + 1}
            </button>
          ))}
        </div>
      </div>

      <div ref={mapRef} className="w-full h-[400px] md:h-[500px]" id="trip-map" />
    </div>
  );
}
