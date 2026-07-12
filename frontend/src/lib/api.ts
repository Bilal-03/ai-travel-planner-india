/**
 * API client for the FastAPI backend.
 * Type-safe request/response handling with error management.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

export interface TripRequest {
  origin: string;
  destination: string;
  start_date: string;
  end_date: string;
  budget: number;
  vibes: TravelVibe[];
}

export interface TransportOption {
  mode: "flight" | "train";
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
  notes: string | null;
}

export interface BudgetBreakdown {
  transport: number;
  food: number;
  activities: number;
  accommodation: number;
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
}

export interface CityInfo {
  name: string;
  state: string | null;
  coordinates: GeoPoint;
  iata_code: string | null;
  station_code: string | null;
}

export interface Itinerary {
  id: string;
  origin: CityInfo;
  destination: CityInfo;
  start_date: string;
  end_date: string;
  total_days: number;
  vibes: TravelVibe[];
  transport_options: TransportOption[];
  selected_transport: TransportOption | null;
  day_plans: DayPlan[];
  budget: BudgetBreakdown;
  route_segments: RouteSegment[];
  weather_forecast: DayWeather[];
  share_url: string | null;
  generation_notes: string[];
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
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(body.detail || "Request failed", res.status);
  }

  return res.json();
}

// ── Endpoints ─────────────────────────────────────────────────────────

export const api = {
  /** Search Indian cities for autocomplete */
  searchCities: (query: string) =>
    request<CitySearchResult[]>(`/api/search/cities?q=${encodeURIComponent(query)}`),

  /** Generate a complete AI itinerary */
  generateTrip: (data: TripRequest) =>
    request<Itinerary>("/api/trips/generate", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /** Get a saved trip by ID */
  getTrip: (tripId: string) => request<Itinerary>(`/api/trips/${tripId}`),

  /** Get share URL for a trip */
  shareTrip: (tripId: string) =>
    request<{ share_url: string; trip_id: string }>(
      `/api/trips/${tripId}/share`,
      { method: "POST" }
    ),

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
