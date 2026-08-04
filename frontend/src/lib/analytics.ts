import { API_BASE } from "@/lib/api";

export type ProductEvent =
  | "planner_started"
  | "planner_completed"
  | "generation_started"
  | "generation_completed"
  | "generation_failed"
  | "trip_shared"
  | "trip_exported"
  | "activity_replaced"
  | "day_regenerated"
  | "transport_selected"
  | "provider_link_clicked";

export type AnalyticsMetadata = Record<string, string | number | boolean | null | undefined>;

const EVENTS: ReadonlySet<ProductEvent> = new Set([
  "planner_started",
  "planner_completed",
  "generation_started",
  "generation_completed",
  "generation_failed",
  "trip_shared",
  "trip_exported",
  "activity_replaced",
  "day_regenerated",
  "transport_selected",
  "provider_link_clicked",
]);

const METADATA_KEYS = new Set([
  "kind",
  "source",
  "status",
  "provider",
  "freshness_status",
  "estimated_data",
  "invalid_itinerary",
  "accepted",
  "days",
  "cost_inr",
  "cost_usd",
  "duration_ms",
]);

function cleanMetadata(metadata: AnalyticsMetadata): Record<string, string | number | boolean | null> {
  const clean: Record<string, string | number | boolean | null> = {};
  for (const [key, value] of Object.entries(metadata).slice(0, 12)) {
    if (!METADATA_KEYS.has(key)) continue;
    if (typeof value === "string") clean[key] = value.slice(0, 120);
    else if (typeof value === "number" || typeof value === "boolean" || value === null) clean[key] = value;
  }
  return clean;
}

export function track(event: ProductEvent, options: { tripId?: string; kind?: "single" | "multi_city"; metadata?: AnalyticsMetadata } = {}): void {
  if (typeof window === "undefined" || !EVENTS.has(event)) return;
  const body = JSON.stringify({
    event,
    trip_id: options.tripId,
    kind: options.kind,
    metadata: cleanMetadata(options.metadata || {}),
  });
  const endpoint = `${API_BASE}/api/analytics/events`;
  try {
    const blob = new Blob([body], { type: "application/json" });
    if (navigator.sendBeacon && navigator.sendBeacon(endpoint, blob)) return;
  } catch {
    // Fall through to a keepalive request when Beacon is unavailable.
  }
  void fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
    keepalive: true,
  }).catch(() => undefined);
}
