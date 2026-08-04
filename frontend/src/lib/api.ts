/**
 * API client for the FastAPI backend.
 * Type-safe request/response handling with error management.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const EDIT_TOKEN_HEADER = "X-Trip-Edit-Token";
const ACCOUNT_TOKEN_HEADER = "X-Yatra-Account-Token";
const ACCOUNT_TOKEN_STORAGE_KEY = "yatraai:account-token";

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

function saveAccountToken(token: string | null): void {
  if (typeof window !== "undefined" && token) {
    window.localStorage.setItem(ACCOUNT_TOKEN_STORAGE_KEY, token);
  }
}

function getAccountToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ACCOUNT_TOKEN_STORAGE_KEY);
}

function editHeaders(tripId: string): HeadersInit | undefined {
  const token = getEditToken(tripId);
  return token ? { [EDIT_TOKEN_HEADER]: token } : undefined;
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

export type TravelVibe =
  | "adventure"
  | "culture"
  | "food"
  | "relaxation"
  | "spiritual"
  | "nightlife";

export type TransportMode = "flight" | "train" | "road";
export type AccommodationPreference = "budget" | "standard" | "comfort";
export type TravelPreference = "cheapest" | "fastest" | "balanced";
export type TripPace = "relaxed" | "balanced" | "packed";
export type DietaryPreference = "vegetarian" | "non_vegetarian";

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
  vibes: TravelVibe[];
  transport_mode?: TransportMode;
  accommodation_preference: AccommodationPreference;
  adults: number;
  children: number;
  travel_preference: TravelPreference;
  pace: TripPace;
  dietary_preference?: DietaryPreference;
  senior_citizens: number;
  accessibility_requirements?: string;
  mandatory_places?: string[];
  excluded_places?: string[];
  free_text_notes?: string;
  allow_early_morning_travel: boolean;
  allow_late_night_travel: boolean;
}

export interface DestinationStayRequest {
  destination: string;
  nights: number;
  notes?: string | null;
}

export interface MultiCityTripRequest {
  origin: string;
  stays: DestinationStayRequest[];
  start_date: string;
  budget: number;
  vibes: TravelVibe[];
  transport_mode?: TransportMode;
  accommodation_preference: AccommodationPreference;
  adults: number;
  children: number;
  travel_preference: TravelPreference;
  pace: TripPace;
  dietary_preference?: DietaryPreference;
  senior_citizens: number;
  accessibility_requirements?: string;
  mandatory_places?: string[];
  excluded_places?: string[];
  free_text_notes?: string;
  allow_early_morning_travel: boolean;
  allow_late_night_travel: boolean;
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
  accommodation: number;
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
  vibes: TravelVibe[];
  accommodation_preference: AccommodationPreference;
  adults: number;
  children: number;
  travel_preference: TravelPreference;
  pace: TripPace;
  dietary_preference: DietaryPreference | null;
  senior_citizens: number;
  accessibility_requirements: string | null;
  mandatory_places?: string[];
  excluded_places?: string[];
  free_text_notes?: string | null;
  allow_early_morning_travel: boolean;
  allow_late_night_travel: boolean;
  transport_options: TransportOption[];
  selected_transport: TransportOption | null;
  day_plans: DayPlan[];
  budget: BudgetBreakdown;
  route_segments: RouteSegment[];
  weather_forecast: DayWeather[];
  destination_photos: DestinationPhoto[];
  festivals: FestivalEvent[];
  packing_list: PackingItem[];
  share_url: string | null;
  generation_notes: string[];
}

export interface DestinationStay {
  id: string;
  city: CityInfo;
  position: number;
  arrival_date: string;
  departure_date: string;
  nights: number;
  notes: string | null;
  provenance?: DataProvenance;
}

export interface TravelLeg {
  id: string;
  origin: CityInfo;
  destination: CityInfo;
  date: string;
  mode: TransportMode;
  selected_offer: TransportOption | null;
  alternatives: TransportOption[];
  duration_minutes: number;
  fare: number;
  origin_stay_id: string | null;
  destination_stay_id: string | null;
  provenance?: DataProvenance;
}

export interface AccommodationSelection {
  id: string;
  stay_id: string;
  destination: CityInfo;
  category: AccommodationPreference;
  nights: number;
  provider: string;
  name: string;
  estimated_total: number;
  provenance?: DataProvenance;
}

export interface TransportSelection {
  leg_id: string;
  selected_offer: TransportOption | null;
  alternatives: TransportOption[];
  provenance?: DataProvenance;
}

export interface Visit {
  id: string;
  stay_id: string;
  date: string;
  poi: POI;
  start_time: string | null;
  end_time: string | null;
  estimated_cost: number;
  notes: string | null;
  is_backup: boolean;
  is_locked: boolean;
}

export interface ItineraryDay {
  day_number: number;
  date: string;
  stay_id: string | null;
  destination: CityInfo | null;
  weather: DayWeather | null;
  visits: Visit[];
  meals: MealRecommendation[];
  travel_leg_id: string | null;
  day_budget: number;
  day_spent: number;
  notes: string | null;
}

export interface MultiCityTrip {
  id: string;
  origin: CityInfo;
  destination_stays: DestinationStay[];
  travel_legs: TravelLeg[];
  itinerary_days: ItineraryDay[];
  visits: Visit[];
  accommodation_selections: AccommodationSelection[];
  transport_selections: TransportSelection[];
  start_date: string;
  end_date: string;
  total_days: number;
  vibes: TravelVibe[];
  accommodation_preference: AccommodationPreference;
  adults: number;
  children: number;
  travel_preference: TravelPreference;
  pace: TripPace;
  dietary_preference: DietaryPreference | null;
  senior_citizens: number;
  accessibility_requirements: string | null;
  budget: BudgetBreakdown;
  generation_notes: string[];
  created_at: string;
}

export interface Account {
  id: string;
  email: string | null;
  display_name: string | null;
  is_anonymous: boolean;
  memory_enabled: boolean;
  created_at: string;
}

export interface AccountSession {
  access_token: string;
  expires_at: string;
  account: Account;
}

export interface PreferenceMemory {
  memory_enabled: boolean;
  preferred_transport: TransportMode | null;
  hotel_category: AccommodationPreference | null;
  typical_budget_min: number | null;
  typical_budget_max: number | null;
  dietary_preference: DietaryPreference | null;
  travel_pace: TripPace | null;
  accessibility_requirements: string | null;
  preferred_departure_times: string[];
  updated_at: string;
}

export interface PreferenceMemoryUpdate {
  memory_enabled?: boolean;
  preferred_transport?: TransportMode | null;
  hotel_category?: AccommodationPreference | null;
  typical_budget_min?: number | null;
  typical_budget_max?: number | null;
  dietary_preference?: DietaryPreference | null;
  travel_pace?: TripPace | null;
  accessibility_requirements?: string | null;
  preferred_departure_times?: string[];
}

export interface SavedTripSummary {
  id: string;
  kind: "single" | "multi_city";
  origin: string;
  destination: string;
  start_date: string;
  end_date: string;
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
          ...(getAccountToken()
            ? {
                [ACCOUNT_TOKEN_HEADER]: getAccountToken() as string,
                ...(getAccountToken()?.split(".").length === 3
                  ? { Authorization: `Bearer ${getAccountToken() as string}` }
                  : {}),
              }
            : {}),
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

  /** Keep anonymous visitors continuous across refreshes without requiring sign-in. */
  ensureAnonymousSession: async () => {
    const existing = getAccountToken();
    if (existing) {
      try {
        return await request<Account>("/api/account/me", { timeoutMs: 15_000, retries: 0 });
      } catch {
        if (typeof window !== "undefined") window.localStorage.removeItem(ACCOUNT_TOKEN_STORAGE_KEY);
      }
    }
    let sessionToken: string | null = null;
    const session = await request<AccountSession>("/api/account/anonymous", {
      method: "POST",
      timeoutMs: 15_000,
      retries: 1,
      onResponse: (response) => {
        sessionToken = response.headers.get(ACCOUNT_TOKEN_HEADER);
      },
    });
    saveAccountToken(sessionToken || session.access_token);
    return session.account;
  },

  registerAccount: async (data: { email: string; display_name?: string }) => {
    let sessionToken: string | null = null;
    const session = await request<AccountSession>("/api/account/register", {
      method: "POST",
      body: JSON.stringify(data),
      timeoutMs: 15_000,
      retries: 0,
      onResponse: (response) => {
        sessionToken = response.headers.get(ACCOUNT_TOKEN_HEADER);
      },
    });
    saveAccountToken(sessionToken || session.access_token);
    return session.account;
  },

  getAccount: () => request<Account>("/api/account/me", { timeoutMs: 15_000, retries: 0 }),

  getSavedTrips: () => request<SavedTripSummary[]>("/api/account/trips", { timeoutMs: 15_000, retries: 0 }),

  claimTrip: (tripId: string) =>
    request<{ claimed: boolean; trip_id: string; account_id: string }>("/api/account/claim-trip", {
      method: "POST",
      body: JSON.stringify({ trip_id: tripId }),
      headers: editHeaders(tripId),
      timeoutMs: 15_000,
      retries: 0,
    }),

  getPreferences: () => request<PreferenceMemory>("/api/account/preferences", { timeoutMs: 15_000, retries: 0 }),

  updatePreferences: (update: PreferenceMemoryUpdate) =>
    request<PreferenceMemory>("/api/account/preferences", {
      method: "PUT",
      body: JSON.stringify(update),
      timeoutMs: 15_000,
      retries: 0,
    }),

  disablePreferenceMemory: () =>
    request<PreferenceMemory>("/api/account/preferences/disable", {
      method: "POST",
      timeoutMs: 15_000,
      retries: 0,
    }),

  deletePreferences: () =>
    request<PreferenceMemory>("/api/account/preferences", {
      method: "DELETE",
      timeoutMs: 15_000,
      retries: 0,
    }),

  deleteAccount: async () => {
    const result = await request<{ deleted: boolean }>("/api/account/me", {
      method: "DELETE",
      timeoutMs: 15_000,
      retries: 0,
    });
    if (typeof window !== "undefined") window.localStorage.removeItem(ACCOUNT_TOKEN_STORAGE_KEY);
    return result;
  },

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

  /** Generate a canonical multi-city route with explicit stays and legs. */
  generateMultiCityTrip: async (data: MultiCityTripRequest) => {
    let editToken: string | null = null;
    const trip = await request<MultiCityTrip>("/api/multi-city/generate", {
      method: "POST",
      body: JSON.stringify(data),
      timeoutMs: 90_000,
      retries: 1,
      onResponse: (response) => {
        editToken = response.headers.get(EDIT_TOKEN_HEADER);
      },
    });
    saveEditToken(trip.id, editToken);
    return trip;
  },

  getMultiCityTrip: (tripId: string) =>
    request<MultiCityTrip>(`/api/multi-city/${encodeURIComponent(tripId)}`),

  reorderMultiCityTrip: async (tripId: string, destinationStayIds: string[]) => {
    const trip = await request<MultiCityTrip>(`/api/multi-city/${encodeURIComponent(tripId)}/reorder`, {
      method: "POST",
      body: JSON.stringify({ destination_stay_ids: destinationStayIds }),
      headers: editHeaders(tripId),
      timeoutMs: 90_000,
      retries: 0,
    });
    return trip;
  },

  updateMultiCityStay: (tripId: string, stayId: string, update: { nights?: number; notes?: string | null }) =>
    request<MultiCityTrip>(`/api/multi-city/${encodeURIComponent(tripId)}/stays/${encodeURIComponent(stayId)}`, {
      method: "PATCH",
      body: JSON.stringify(update),
      headers: editHeaders(tripId),
      timeoutMs: 30_000,
      retries: 0,
    }),

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
  getTrip: (tripId: string) => request<Itinerary>(`/api/trips/${tripId}`),

  /** Get share URL for a trip */
  shareTrip: (tripId: string) =>
    request<{ share_url: string; trip_id: string }>(
      `/api/trips/${tripId}/share`,
      { method: "POST" }
    ),

  refineTrip: (tripId: string, instruction: string) =>
    request<Itinerary>(`/api/trips/${tripId}/refine`, {
      method: "POST",
      body: JSON.stringify({ instruction }),
      headers: editHeaders(tripId),
    }),

  undoTrip: (tripId: string) =>
    request<Itinerary>(`/api/trips/${tripId}/undo`, {
      method: "POST",
      headers: editHeaders(tripId),
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
    }),

  generatePackingList: (tripId: string) =>
    request<PackingItem[]>(`/api/trips/${tripId}/packing-list`, {
      method: "POST",
      headers: editHeaders(tripId),
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
  health: () => request<{ status: string; services: Record<string, string> }>("/health"),

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

/** Get vibe emoji */
export function getVibeEmoji(vibe: TravelVibe): string {
  const map: Record<TravelVibe, string> = {
    adventure: "🏔️",
    culture: "🏛️",
    food: "🍛",
    relaxation: "🧘",
    spiritual: "🛕",
    nightlife: "🌃",
  };
  return map[vibe] || "✨";
}

export { ApiError };
