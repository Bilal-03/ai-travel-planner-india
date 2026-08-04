"use client";

import { useEffect, useState } from "react";
import { isOfflineSnapshotStale } from "@/lib/offline";

interface ConnectivityIndicatorProps {
  savedAt?: string | null;
}

export default function ConnectivityIndicator({ savedAt = null }: ConnectivityIndicatorProps) {
  const [online, setOnline] = useState(true);

  useEffect(() => {
    const update = () => setOnline(navigator.onLine);
    update();
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);

  const stale = Boolean(savedAt && isOfflineSnapshotStale(savedAt));
  if (online && !stale) return null;

  return (
    <div className="fixed bottom-4 left-4 right-4 z-[60] mx-auto max-w-xl rounded-xl border border-warning/40 bg-background/95 px-4 py-3 text-xs text-foreground shadow-lg backdrop-blur sm:left-auto sm:right-5">
      <p className="font-semibold text-warning">{online ? "⚠️ Saved trip snapshot may be stale" : "📡 You are offline"}</p>
      <p className="mt-1 leading-relaxed text-foreground-muted">
        {online ? "The itinerary remains available, but refresh live prices, hours, weather, and emergency information before booking." : "Your saved itinerary, addresses, and emergency notes remain available. Changes will wait until the connection returns."}
      </p>
    </div>
  );
}
