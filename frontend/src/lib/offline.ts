import type { Itinerary } from "@/lib/api";

export type OfflineTrip = Itinerary;
export type OfflineTripKind = "single";

export interface OfflineTripSnapshot {
  tripId: string;
  kind: OfflineTripKind;
  savedAt: string;
  trip: OfflineTrip;
  essentials: {
    addresses: string[];
    emergencyNotes: string[];
  };
}

const SNAPSHOT_PREFIX = "yatraai:offline-trip:";
export const OFFLINE_SNAPSHOT_MAX_AGE_MS = 24 * 60 * 60 * 1000;

function key(tripId: string): string {
  return `${SNAPSHOT_PREFIX}${tripId}`;
}

function addressesForTrip(trip: OfflineTrip): string[] {
  return [
    `${trip.origin.name}${trip.origin.state ? `, ${trip.origin.state}` : ""}`,
    `${trip.destination.name}${trip.destination.state ? `, ${trip.destination.state}` : ""}`,
  ];
}

export function saveOfflineTrip(trip: OfflineTrip, kind: OfflineTripKind): void {
  if (typeof window === "undefined" || !trip.id) return;
  const snapshot: OfflineTripSnapshot = {
    tripId: trip.id,
    kind,
    savedAt: new Date().toISOString(),
    trip,
    essentials: {
      addresses: addressesForTrip(trip),
      emergencyNotes: [
        "Emergency services in India: 112.",
        "Offline details may be stale; verify live transport and venue information when connected.",
        "Keep your government photo ID and booking references accessible while travelling.",
      ],
    },
  };
  try {
    window.localStorage.setItem(key(trip.id), JSON.stringify(snapshot));
  } catch {
    // A full/private-mode storage area should not block itinerary viewing.
  }
}

export function loadOfflineTrip(tripId: string): OfflineTripSnapshot | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(key(tripId));
  if (!raw) return null;
  try {
    const snapshot = JSON.parse(raw) as OfflineTripSnapshot;
    if (!snapshot.trip || snapshot.tripId !== tripId || !snapshot.savedAt) return null;
    return snapshot;
  } catch {
    return null;
  }
}

export function isOfflineSnapshotStale(savedAt: string, now = Date.now()): boolean {
  const timestamp = Date.parse(savedAt);
  return !Number.isFinite(timestamp) || now - timestamp > OFFLINE_SNAPSHOT_MAX_AGE_MS;
}
