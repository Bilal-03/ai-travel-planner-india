/**
 * API client for the FastAPI backend.
 * Type-safe request/response handling with error management.
 */

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const EDIT_TOKEN_HEADER = "X-Trip-Edit-Token";
const SHARE_TOKEN_HEADER = "X-Trip-Share-Token";

export type CollaborationRole = "owner" | "editor" | "viewer";
export type TripKind = "single";

function editTokenKey(tripId: string): string {
  return `yatraai:trip-edit-token:${tripId}`;
}

function saveEditToken(tripId: string, token: string | null): void {
  if (typeof window !== "undefined" && token) {
    window.sessionStorage.setItem(editTokenKey(tripId), token);
  }
}

function getEditToken(tripId: string): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(editTokenKey(tripId));
}

function shareTokenKey(tripId: string): string {
  return `yatraai:trip-share-token:${tripId}`;
}

function revisionKey(tripId: string): string {
  return `yatraai:trip-revision:${tripId}`;
}

function saveRevision(tripId: string, response: Response): void {
  if (typeof window === "undefined") return;
  const tag = response.headers.get("ETag");
  if (tag) window.sessionStorage.setItem(revisionKey(tripId), tag);
}

function getRevision(tripId: string): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(revisionKey(tripId));
}

export function setShareToken(tripId: string, token: string | null): void {
  if (typeof window === "undefined" || !token) return;
  window.sessionStorage.setItem(shareTokenKey(tripId), token);
}

function getShareToken(tripId: string): string | null {
  if (typeof window === "undefined") return null;
  const stored = window.sessionStorage.getItem(shareTokenKey(tripId));
  if (stored) return stored;
  const fromUrl = new URLSearchParams(window.location.search).get("share");
  if (fromUrl) setShareToken(tripId, fromUrl);
  return fromUrl;
}

function editHeaders(tripId: string): HeadersInit | undefined {
  const token = getEditToken(tripId);
  const shareToken = getShareToken(tripId);
  const headers: Record<string, string> = {};
  if (token) headers[EDIT_TOKEN_HEADER] = token;
  if (shareToken) headers[SHARE_TOKEN_HEADER] = shareToken;
  const revision = getRevision(tripId);
  if (revision) headers["If-Match"] = revision;
  return Object.keys(headers).length ? headers : undefined;
}

function shareHeaders(tripId: string): HeadersInit | undefined {
  const token = getShareToken(tripId);
  return token ? { [SHARE_TOKEN_HEADER]: token } : undefined;
}

// ── Types ─────────────────────────────────────────────────────────────

export interface GeoPoint {
  lat: number;
  lng: number;
}

export interface CitySearchResult {
  name: string;
  state: string | null;
  display_name: string;
  coordinates: GeoPoint;
}

export type TransportMode = "flight" | "train" | "road";

export type DataStatus =
  | "live"
  | "recently_verified"
  | "schedule_only"
  | "estimated"
  | "static_reference"
  | "unavailable";

export interface DataProvenance {
  provider: string;
  status: DataStatus;
  retrieved_at: string | null;
  expires_at: string | null;
  confidence: number | null;
  source_reference: string | null;
  disclaimer: string;
}

export type TravelPace = "relaxed" | "balanced" | "active";
export type TravellerType = "solo" | "couple" | "family" | "friends" | "seniors" | "business";

export interface TripPreferences {
  experiences: string[];
  pace: TravelPace | null;
  traveller_type: TravellerType | null;
  transport_preferences: TransportMode[];
  hotel_style: string | null;
  dietary_preferences: string[];
  accessibility_requirements: string[];
  arrival_window: string | null;
  flexible_dates: boolean;
}

export const UNAVAILABLE_PROVENANCE: DataProvenance = {
  provider: "not_provided",
  status: "unavailable",
  retrieved_at: null,
  expires_at: null,
  confidence: null,
  source_reference: null,
  disclaimer: "Provider provenance is unavailable; verify before booking.",
};

export interface TripRequest {
  origin: string;
  destination: string;
  start_date: string;
  end_date: string;
  budget: number;
  transport_mode?: TransportMode;
  members: number;
  planning_notes?: string;
  preferences?: Partial<TripPreferences>;
}

export type ClarificationInput = "choice" | "text" | "date_range" | "number";

export interface ClarificationOption {
  id: string;
  label: string;
  description?: string | null;
}

export interface ClarificationQuestion {
  id: string;
  prompt: string;
  input_type: ClarificationInput;
  options: ClarificationOption[];
  allow_custom: boolean;
}

export interface PlannerAnswer {
  question_id: string;
  option_id?: string | null;
  answer: string;
}

export interface PlanningBrief {
  origin: string | null;
  destination: string | null;
  start_date: string | null;
  end_date: string | null;
  budget: number | null;
  members: number | null;
  transport_mode: TransportMode | null;
  planning_notes: string;
}

export interface PlannerClarificationResponse {
  status: "questions" | "ready";
  brief: PlanningBrief;
  questions: ClarificationQuestion[];
  trip_request: TripRequest | null;
}

export interface TransportOption {
  mode: TransportMode;
  provider: string;
  code: string | null;
  price: number;
  duration_minutes: number;
  departure_time: string | null;
  arrival_time: string | null;
  departure_city: string;
  arrival_city: string;
  is_recommended: boolean;
  is_fallback: boolean;
  field_provenance: Record<string, string>;
  field_data_provenance?: Record<string, DataProvenance>;
  provenance?: DataProvenance;
  availability_status: string;
  last_checked_at: string | null;
}

export interface POI {
  id: string;
  name: string;
  category: string;
  coordinates: GeoPoint;
  estimated_visit_minutes: number;
  estimated_cost: number;
  description: string | null;
  opening_hours: string | null;
  provenance?: DataProvenance;
  field_provenance?: Record<string, DataProvenance>;
}

export interface PlacePhoto {
  url: string;
  alt: string;
  credit: string | null;
  source_url: string | null;
  provenance?: DataProvenance;
}

export interface Place {
  id: string;
  name: string;
  category: string;
  coordinates: GeoPoint;
  address: string | null;
  city: string | null;
  state: string | null;
  country: string;
  description: string | null;
  opening_hours: string | null;
  rating: number | null;
  review_count: number | null;
  price_level: number | null;
  official_url: string | null;
  maps_url: string | null;
  provider_ids: Record<string, string>;
  photos: PlacePhoto[];
  provenance?: DataProvenance;
  field_provenance?: Record<string, DataProvenance>;
}

export type ItineraryItemType =
  | "place_visit"
  | "stay"
  | "flight"
  | "train"
  | "road_transfer"
  | "restaurant"
  | "event"
  | "note";

export interface ItineraryItem {
  id: string;
  item_type: ItineraryItemType;
  title: string;
  day_number: number | null;
  position: number;
  place_id: string | null;
  coordinates: GeoPoint | null;
  start_time: string | null;
  end_time: string | null;
  duration_minutes: number | null;
  description: string | null;
  notes: string | null;
  image_url: string | null;
  source_ids: string[];
  provenance?: DataProvenance;
  is_locked: boolean;
  metadata: Record<string, unknown>;
}

export type SourceKind = "official" | "provider" | "map" | "editorial" | "image" | "user";

export interface TripSource {
  id: string;
  source_type: SourceKind;
  publisher: string;
  title: string;
  url: string | null;
  attribution_text: string | null;
  provenance?: DataProvenance;
  captured_at: string;
}

export type ResearchEventType =
  | "understanding_request"
  | "asking_question"
  | "searching"
  | "found_places"
  | "found_transport"
  | "found_stays"
  | "validating"
  | "updated_plan"
  | "completed"
  | "failed";
export type ResearchEventStatus = "pending" | "complete" | "warning" | "error";

export interface ResearchEvent {
  id: string;
  event_type: ResearchEventType;
  status: ResearchEventStatus;
  message: string;
  query: string | null;
  result_count: number | null;
  source_ids: string[];
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface Activity {
  poi: POI;
  start_time: string | null;
  end_time: string | null;
  estimated_cost: number;
  notes: string | null;
  is_backup: boolean;
  is_locked?: boolean;
}

export interface MealRecommendation {
  name: string;
  cuisine: string | null;
  meal_type: string;
  estimated_cost: number;
  notes: string | null;
  provenance?: DataProvenance;
  field_provenance?: Record<string, DataProvenance>;
}

export interface DayWeather {
  date: string;
  temp_min: number;
  temp_max: number;
  condition: string;
  icon: string;
  rain_probability: number;
  severity: "great" | "okay" | "indoor";
  summary: string;
  alerts: string[];
  provenance?: DataProvenance;
}

export interface DayPlan {
  day_number: number;
  date: string;
  weather: DayWeather | null;
  transport: TransportOption | null;
  activities: Activity[];
  meals: MealRecommendation[];
  backup_activities: Activity[];
  day_budget: number;
  day_spent: number;
  local_transport_minutes: number;
  local_transport_cost: number;
  notes: string | null;
}

export interface BudgetBreakdown {
  outbound_transport: number;
  return_transport: number;
  transport: number;
  food: number;
  activities: number;
  local_transport: number;
  taxes_buffer: number;
  miscellaneous: number;
  total_estimated: number;
  remaining: number;
  provenance?: DataProvenance;
}

export interface RouteSegment {
  from_point: GeoPoint;
  to_point: GeoPoint;
  geometry: number[][] | null;
  distance_km: number;
  duration_minutes: number;
  day_number: number | null;
  provenance?: DataProvenance;
}

export interface CityInfo {
  name: string;
  state: string | null;
  coordinates: GeoPoint;
  iata_code: string | null;
  station_code: string | null;
  provenance?: DataProvenance;
}

export interface DestinationPhoto {
  url: string;
  alt: string;
  photographer_name: string | null;
  photographer_url: string | null;
  provenance?: DataProvenance;
}

export interface FestivalEvent {
  name: string;
  start_date: string;
  end_date: string;
  description: string;
  travel_tip: string;
}

export interface PackingItem {
  item: string;
  reason: string;
  category: string;
}

export interface Itinerary {
  id: string;
  origin: CityInfo;
  destination: CityInfo;
  start_date: string;
  end_date: string;
  total_days: number;
  members: number;
  planning_notes: string | null;
  places?: Place[];
  items?: ItineraryItem[];
  sources?: TripSource[];
  research_events?: ResearchEvent[];
  transport_options: TransportOption[];
  selected_transport: TransportOption | null;
  day_plans: DayPlan[];
  budget: BudgetBreakdown;
  route_segments: RouteSegment[];
  plan_options: PlanOption[];
  selected_plan_id: string;
  weather_forecast: DayWeather[];
  destination_photos: DestinationPhoto[];
  festivals: FestivalEvent[];
  packing_list: PackingItem[];
  share_url: string | null;
  generation_notes: string[];
}

export interface PlanOption {
  id: string;
  title: string;
  description: string;
  day_plans: DayPlan[];
  budget: BudgetBreakdown;
  route_segments: RouteSegment[];
  generation_notes: string[];
}

export interface ShareLink {
  id: string;
  trip_id: string;
  kind: TripKind;
  role: Exclude<CollaborationRole, "owner">;
  share_url: string;
  invite_email: string | null;
  expires_at: string;
  revoked_at: string | null;
}

export interface TripVersion {
  id: string;
  trip_id: string;
  kind: TripKind;
  version: number;
  action: string;
  actor_id: string | null;
  created_at: string;
  snapshot?: Record<string, unknown> | null;
}

export interface TripActivity {
  id: string;
  trip_id: string;
  kind: TripKind;
  action: string;
  actor_id: string | null;
  version: number | null;
  metadata: Record<string, string | number | boolean | null>;
  created_at: string;
}

export interface GenerationStatus {
  step: string;
  message: string;
  progress: number;
  status?: TripJobState;
  id?: number;
  job_id?: string;
  error?: string | null;
}

export type TripJobState =
  | "accepted"
  | "retrieving_data"
  | "resolving_locations"
  | "fetching_transport"
  | "fetching_places"
  | "fetching_weather"
  | "optimising"
  | "generating_narrative"
  | "validating"
  | "saving"
  | "completed"
  | "failed"
  | "cancelled";

export interface TripJob {
  id: string;
  status: TripJobState;
  step: string;
  message: string;
  progress: number;
  result_trip_id: string | null;
  error: string | null;
  attempts: number;
  cancel_requested: boolean;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface TripJobEvent extends GenerationStatus {
  id: number;
  job_id: string;
  status: TripJobState;
}

export interface GenerationRequestOptions {
  signal?: AbortSignal;
  progressToken?: string;
  timeoutMs?: number;
  retries?: number;
}

// ── API Client ────────────────────────────────────────────────────────

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function request<T>(
  endpoint: string,
  options?: RequestInit & {
    timeoutMs?: number;
    retries?: number;
    onResponse?: (response: Response) => void;
  }
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const { timeoutMs = 30_000, retries = 0, onResponse, ...fetchOptions } = options || {};

  for (let attempt = 0; attempt <= retries; attempt += 1) {
    const controller = new AbortController();
    let timedOut = false;
    const abortFromCaller = () => controller.abort();
    fetchOptions.signal?.addEventListener("abort", abortFromCaller, { once: true });
    const timeout = window.setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, timeoutMs);

    try {
      const res = await fetch(url, {
        ...fetchOptions,
        signal: controller.signal,
        headers: {
          "Content-Type": "application/json",
          ...fetchOptions.headers,
        },
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: res.statusText }));
        throw new ApiError(body.detail || "Request failed", res.status);
      }
      onResponse?.(res);
      return res.json();
    } catch (error) {
      if (fetchOptions.signal?.aborted) throw error;
      const retryable = !(error instanceof ApiError) || error.status >= 500;
      if (attempt < retries && retryable && !timedOut) continue;
      if (timedOut) throw new ApiError("The planner is taking longer than expected. Please retry.", 408);
      throw error;
    } finally {
      window.clearTimeout(timeout);
      fetchOptions.signal?.removeEventListener("abort", abortFromCaller);
    }
  }
  throw new ApiError("Request failed", 500);
}

// ── Endpoints ─────────────────────────────────────────────────────────

export const api = {
  /** Search Indian cities for autocomplete */
  searchCities: (query: string, signal?: AbortSignal) =>
    request<CitySearchResult[]>(`/api/search/cities?q=${encodeURIComponent(query)}`, {
      signal,
      timeoutMs: 15_000,
      retries: 1,
    }),

  /** Extract a trip request or return the next small set of questions. */
  clarifyPlanner: (data: { prompt: string; answers: PlannerAnswer[] }, signal?: AbortSignal) =>
    request<PlannerClarificationResponse>("/api/planner/clarify", {
      method: "POST",
      body: JSON.stringify(data),
      signal,
      timeoutMs: 45_000,
      retries: 1,
    }),

  /** Generate a complete AI itinerary */
  generateTrip: async (data: TripRequest, options: GenerationRequestOptions = {}) => {
    let editToken: string | null = null;
    const itinerary = await request<Itinerary>("/api/trips/generate", {
      method: "POST",
      body: JSON.stringify(data),
      signal: options.signal,
      timeoutMs: options.timeoutMs ?? 90_000,
      retries: options.retries ?? 1,
      headers: options.progressToken ? { "X-Progress-Token": options.progressToken } : undefined,
      onResponse: (response) => {
        editToken = response.headers.get(EDIT_TOKEN_HEADER);
      },
    });
    saveEditToken(itinerary.id, editToken);
    return itinerary;
  },

  /** Accept a durable asynchronous trip-generation job. */
  createTripJob: (data: TripRequest, idempotencyKey: string, signal?: AbortSignal) =>
    request<TripJob>("/api/trip-jobs", {
      method: "POST",
      body: JSON.stringify(data),
      signal,
      timeoutMs: 30_000,
      retries: 1,
      headers: { "Idempotency-Key": idempotencyKey },
    }),

  getTripJob: (jobId: string) => request<TripJob>(`/api/trip-jobs/${encodeURIComponent(jobId)}`),

  cancelTripJob: (jobId: string) =>
    request<TripJob>(`/api/trip-jobs/${encodeURIComponent(jobId)}/cancel`, {
      method: "POST",
    }),

  getTripJobResult: async (jobId: string) => {
    let editToken: string | null = null;
    const itinerary = await request<Itinerary>(
      `/api/trip-jobs/${encodeURIComponent(jobId)}/result`,
      {
        timeoutMs: 30_000,
        retries: 1,
        onResponse: (response) => {
          editToken = response.headers.get(EDIT_TOKEN_HEADER);
        },
      },
    );
    saveEditToken(itinerary.id, editToken);
    return itinerary;
  },

  subscribeTripJobEvents: (
    jobId: string,
    onProgress: (event: TripJobEvent) => void,
    lastEventId?: number,
  ) => {
    const query = lastEventId ? `?last_event_id=${encodeURIComponent(String(lastEventId))}` : "";
    const stream = new EventSource(`${API_BASE}/api/trip-jobs/${encodeURIComponent(jobId)}/events${query}`);
    stream.addEventListener("progress", (event) => {
      try {
        onProgress(JSON.parse((event as MessageEvent).data) as TripJobEvent);
      } catch {
        // Ignore malformed intermediary events; the status endpoint remains authoritative.
      }
    });
    return () => stream.close();
  },

  subscribeTripProgress: (token: string, onProgress: (status: GenerationStatus) => void) => {
    const stream = new EventSource(`${API_BASE}/api/trips/progress/${encodeURIComponent(token)}`);
    stream.addEventListener("progress", (event) => {
      try {
        onProgress(JSON.parse((event as MessageEvent).data) as GenerationStatus);
      } catch {
        // Ignore malformed intermediary events; the final request still reports errors.
      }
    });
    return () => stream.close();
  },

  /** Get a saved trip by ID */
  getTrip: (tripId: string) => request<Itinerary>(`/api/trips/${encodeURIComponent(tripId)}`, {
    headers: shareHeaders(tripId),
    onResponse: (response) => saveRevision(tripId, response),
  }),

  /** Get share URL for a trip */
  shareTrip: (tripId: string) =>
    request<{ share_url: string; trip_id: string }>(
      `/api/trips/${tripId}/share`,
      { method: "POST" }
    ),

  createShareLink: (tripId: string, role: Exclude<CollaborationRole, "owner">, inviteEmail?: string) =>
    request<ShareLink>(`/api/trips/${encodeURIComponent(tripId)}/share-links`, {
      method: "POST",
      body: JSON.stringify({ role, invite_email: inviteEmail || null }),
      headers: editHeaders(tripId),
      onResponse: (response) => saveRevision(tripId, response),
      timeoutMs: 15_000,
      retries: 0,
    }),

  listShareLinks: (tripId: string) =>
    request<ShareLink[]>(`/api/trips/${encodeURIComponent(tripId)}/share-links`, {
      headers: editHeaders(tripId),
      timeoutMs: 15_000,
      retries: 0,
    }),

  revokeShareLink: (tripId: string, linkId: string) =>
    request<{ revoked: boolean }>(`/api/trips/${encodeURIComponent(tripId)}/share-links/${encodeURIComponent(linkId)}`, {
      method: "DELETE",
      headers: editHeaders(tripId),
      timeoutMs: 15_000,
      retries: 0,
    }),

  getShareAccess: (tripId: string) =>
    request<{ trip_id: string; kind: TripKind; role: CollaborationRole; version: number }>(`/api/trips/${encodeURIComponent(tripId)}/access`, {
      headers: editHeaders(tripId),
      timeoutMs: 15_000,
      retries: 0,
    }),

  getTripHistory: (tripId: string, kind: TripKind = "single") =>
    request<TripVersion[]>(`/api/trips/${encodeURIComponent(tripId)}/history?kind=${kind}`, {
      headers: editHeaders(tripId),
      timeoutMs: 15_000,
      retries: 0,
    }),

  getTripActivity: (tripId: string, kind: TripKind = "single") =>
    request<TripActivity[]>(`/api/trips/${encodeURIComponent(tripId)}/activity?kind=${kind}`, {
      headers: editHeaders(tripId),
      timeoutMs: 15_000,
      retries: 0,
    }),

  copyTrip: async (tripId: string, kind: TripKind = "single") => {
    let editToken: string | null = null;
    const result = await request<{ trip_id: string; kind: TripKind; trip: Itinerary }>(`/api/trips/${encodeURIComponent(tripId)}/copy`, {
      method: "POST",
      body: JSON.stringify({ kind }),
      headers: editHeaders(tripId),
      timeoutMs: 30_000,
      retries: 0,
      onResponse: (response) => {
        editToken = response.headers.get(EDIT_TOKEN_HEADER);
      },
    });
    saveEditToken(result.trip_id, editToken);
    return result;
  },

  refineTrip: (tripId: string, instruction: string) =>
    request<Itinerary>(`/api/trips/${tripId}/refine`, {
      method: "POST",
      body: JSON.stringify({ instruction }),
      headers: editHeaders(tripId),
      onResponse: (response) => saveRevision(tripId, response),
    }),

  undoTrip: (tripId: string) =>
    request<Itinerary>(`/api/trips/${tripId}/undo`, {
      method: "POST",
      headers: editHeaders(tripId),
      onResponse: (response) => saveRevision(tripId, response),
    }),

  selectTransport: (tripId: string, option: TransportOption) =>
    request<Itinerary>(`/api/trips/${tripId}/transport`, {
      method: "POST",
      body: JSON.stringify({
        mode: option.mode,
        provider: option.provider,
        code: option.code,
      }),
      headers: editHeaders(tripId),
      onResponse: (response) => saveRevision(tripId, response),
    }),

  selectPlan: (tripId: string, planId: string) =>
    request<Itinerary>(`/api/trips/${tripId}/plan`, {
      method: "POST",
      body: JSON.stringify({ plan_id: planId }),
      headers: editHeaders(tripId),
      onResponse: (response) => saveRevision(tripId, response),
    }),

  generatePackingList: (tripId: string) =>
    request<PackingItem[]>(`/api/trips/${tripId}/packing-list`, {
      method: "POST",
      headers: editHeaders(tripId),
      onResponse: (response) => saveRevision(tripId, response),
    }),

  /** Search flights */
  searchFlights: (from: string, to: string, date: string) =>
    request<TransportOption[]>(
      `/api/transport/flights?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}&date=${date}`
    ),

  /** Search trains */
  searchTrains: (from: string, to: string) =>
    request<TransportOption[]>(
      `/api/transport/trains?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`
    ),

  /** Health check */
  health: () => request<{ status: string; ready?: boolean; services: Record<string, unknown> }>("/health"),

  /**
   * Starts a backend cold start as soon as the visitor opens the site.
   * A failed warm-up is intentionally ignored: the real request will still
   * surface a useful error to the visitor.
   */
  warmUp: async () => {
    try {
      await api.health();
      return true;
    } catch {
      return false;
    }
  },
};

// ── Helpers ───────────────────────────────────────────────────────────

/** Format INR currency */
export function formatINR(amount: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

/** Format duration in minutes to human readable */
export function formatDuration(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  if (hours === 0) return `${mins}m`;
  if (mins === 0) return `${hours}h`;
  return `${hours}h ${mins}m`;
}

/** Format date string */
export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-IN", {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
}

/** Get weather severity color */
export function getWeatherColor(severity: string): string {
  switch (severity) {
    case "great":
      return "var(--weather-great)";
    case "okay":
      return "var(--weather-okay)";
    case "indoor":
      return "var(--weather-indoor)";
    default:
      return "var(--foreground-muted)";
  }
}

export { ApiError };
