/**
 * API client for the FastAPI backend.
 * Type-safe request/response handling with error management.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const EDIT_TOKEN_HEADER = "X-Trip-Edit-Token";

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
}

export interface Activity {
  poi: POI;
  start_time: string | null;
  end_time: string | null;
  estimated_cost: number;
  notes: string | null;
  is_backup: boolean;
}

export interface MealRecommendation {
  name: string;
  cuisine: string | null;
  meal_type: string;
  estimated_cost: number;
  notes: string | null;
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
}

export interface RouteSegment {
  from_point: GeoPoint;
  to_point: GeoPoint;
  geometry: number[][] | null;
  distance_km: number;
  duration_minutes: number;
  day_number: number | null;
}

export interface CityInfo {
  name: string;
  state: string | null;
  coordinates: GeoPoint;
  iata_code: string | null;
  station_code: string | null;
}

export interface DestinationPhoto {
  url: string;
  alt: string;
  photographer_name: string | null;
  photographer_url: string | null;
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

export interface GenerationStatus {
  step: string;
  message: string;
  progress: number;
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
