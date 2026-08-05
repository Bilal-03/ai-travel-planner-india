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
    commitments?: {
      transport: string | null;
      stays: string[];
    };
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

function currency(amount: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

export function commitmentsForTrip(trip: OfflineTrip): { transport: string | null; stays: string[] } {
  const transport = trip.selected_transport
    ? `${trip.selected_transport.provider}${trip.selected_transport.code ? ` · ${trip.selected_transport.code}` : ""} · ${trip.origin.name} → ${trip.destination.name}`
    : null;
  const stays = (trip.items || [])
    .filter((item) => item.item_type === "stay")
    .map((item) => {
      const metadata = item.metadata || {};
      const area = typeof metadata.area === "string" ? metadata.area : "Destination stay";
      const total = typeof metadata.total_price === "number" ? ` · ${currency(metadata.total_price)}` : "";
      return `${item.title} · ${area}${total}`;
    });
  return { transport, stays };
}

export function saveOfflineTrip(trip: OfflineTrip, kind: OfflineTripKind): void {
  if (typeof window === "undefined" || !trip.id) return;
  const commitments = commitmentsForTrip(trip);
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
      commitments,
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
