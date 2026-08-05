"use client";

import { useEffect, useState } from "react";
import { isOfflineSnapshotStale } from "@/lib/offline";

interface ConnectivityIndicatorProps {
  savedAt?: string | null;
  usingSnapshot?: boolean;
}

export default function ConnectivityIndicator({ savedAt = null, usingSnapshot = false }: ConnectivityIndicatorProps) {
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
  if (online && !stale && !usingSnapshot) return null;

  const title = usingSnapshot
    ? "Viewing a saved trip snapshot"
    : online
      ? "Saved trip snapshot may be stale"
      : "You are offline";
  const message = usingSnapshot
    ? "This trip was loaded from this device because the live trip could not be reached. It is read-only; reconnect before refreshing prices, hours, weather, or provider availability."
    : online
      ? "The itinerary remains available, but refresh live prices, hours, weather, and emergency information before booking."
      : "Your saved itinerary, commitments, addresses, and emergency notes remain available. Changes will wait until the connection returns.";

  return (
    <div data-testid="connectivity-indicator" className="fixed bottom-4 left-4 right-4 z-[60] mx-auto max-w-xl rounded-xl border border-warning/40 bg-background/95 px-4 py-3 text-xs text-foreground shadow-lg backdrop-blur sm:left-auto sm:right-5 print:hidden">
      <p className="font-semibold text-warning">{usingSnapshot ? "🗂️" : online ? "⚠️" : "📡"} {title}</p>
      <p className="mt-1 leading-relaxed text-foreground-muted">{message}</p>
    </div>
  );
}
