"""
Pydantic models for the AI Travel Itinerary Planner.
All monetary values are in INR (₹).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator


# ── Enums ──────────────────────────────────────────────────────────────

class TravelVibe(str, Enum):
    ADVENTURE = "adventure"
    CULTURE = "culture"
    FOOD = "food"
    RELAXATION = "relaxation"
    SPIRITUAL = "spiritual"
    NIGHTLIFE = "nightlife"


class TransportMode(str, Enum):
    FLIGHT = "flight"
    TRAIN = "train"
    ROAD = "road"


class AccommodationPreference(str, Enum):
    BUDGET = "budget"
    STANDARD = "standard"
    COMFORT = "comfort"


class TravelPreference(str, Enum):
    CHEAPEST = "cheapest"
    FASTEST = "fastest"
    BALANCED = "balanced"


class TripPace(str, Enum):
    RELAXED = "relaxed"
    BALANCED = "balanced"
    PACKED = "packed"


class DietaryPreference(str, Enum):
    VEGETARIAN = "vegetarian"
    NON_VEGETARIAN = "non_vegetarian"


class WeatherSeverity(str, Enum):
    GREAT = "great"        # Clear / sunny
    OKAY = "okay"          # Partly cloudy / mild
    INDOOR = "indoor"      # Rain / storm — indoor backup recommended


class DataStatus(str, Enum):
    """How trustworthy and current a travel fact is."""

    LIVE = "live"
    RECENTLY_VERIFIED = "recently_verified"
    SCHEDULE_ONLY = "schedule_only"
    ESTIMATED = "estimated"
    STATIC_REFERENCE = "static_reference"
    UNAVAILABLE = "unavailable"


class DataProvenance(BaseModel):
    """Provider, freshness, and disclosure metadata for an external fact."""

    provider: str = "not_provided"
    status: DataStatus = DataStatus.UNAVAILABLE
    retrieved_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    confidence: Optional[float] = Field(None, ge=0, le=1)
    source_reference: Optional[str] = None
    disclaimer: str = "Provider provenance is unavailable; verify before booking."

    @model_validator(mode="after")
    def validate_freshness_window(self) -> "DataProvenance":
        if self.status in {DataStatus.LIVE, DataStatus.RECENTLY_VERIFIED} and not self.retrieved_at:
            raise ValueError("live or recently_verified facts require retrieved_at")
        if self.retrieved_at and self.expires_at and self.expires_at <= self.retrieved_at:
            raise ValueError("expires_at must be later than retrieved_at")
        return self

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def is_stale(self, now: Optional[datetime] = None) -> bool:
        """Return whether this fact has passed its freshness window."""

        if self.expires_at is None:
            return False
        current = self._as_utc(now or datetime.now(timezone.utc))
        return self._as_utc(self.expires_at) <= current

    def effective_status(self, now: Optional[datetime] = None) -> DataStatus:
        """Treat expired facts as unavailable to live-claim consumers."""

        if self.status == DataStatus.UNAVAILABLE or self.is_stale(now):
            return DataStatus.UNAVAILABLE
        return self.status


def _unavailable_provenance() -> DataProvenance:
    return DataProvenance()


# ── Request Models ─────────────────────────────────────────────────────

class TripRequest(BaseModel):
    origin: str = Field(..., description="Origin city name (India)")
    destination: str = Field(..., description="Destination city name (India)")
    start_date: date = Field(..., description="Trip start date")
    end_date: date = Field(..., description="Trip end date")
    budget: int = Field(..., ge=1000, le=1000000, description="Total budget in INR")
    vibes: list[TravelVibe] = Field(
        default=[TravelVibe.CULTURE],
        description="Travel vibes/preferences",
    )
    transport_mode: Optional[TransportMode] = Field(
        None,
        description="Transport mode selected by the traveller; omit to use the recommendation",
    )
    accommodation_preference: AccommodationPreference = Field(
        AccommodationPreference.BUDGET,
        description="Estimated stay tier used for the trip budget",
    )
    adults: int = Field(2, ge=1, le=20, description="Number of adult travellers")
    children: int = Field(0, ge=0, le=20, description="Number of child travellers")
    travel_preference: TravelPreference = TravelPreference.BALANCED
    pace: TripPace = TripPace.BALANCED
    dietary_preference: Optional[DietaryPreference] = None
    senior_citizens: int = Field(0, ge=0, le=20)
    accessibility_requirements: Optional[str] = Field(None, max_length=500)
    mandatory_places: list[str] = Field(default_factory=list, max_length=20)
    excluded_places: list[str] = Field(default_factory=list, max_length=50)
    free_text_notes: Optional[str] = Field(None, max_length=2_000)
    allow_early_morning_travel: bool = False
    allow_late_night_travel: bool = False

    @model_validator(mode="after")
    def validate_trip_constraints(self) -> "TripRequest":
        if self.origin.strip().casefold() == self.destination.strip().casefold():
            raise ValueError("Origin and destination must be different cities")
        if self.start_date < date.today():
            raise ValueError("Departure date cannot be in the past")
        if self.end_date < self.start_date:
            raise ValueError("Return date cannot be before departure date")
        if (self.end_date - self.start_date).days + 1 > 14:
            raise ValueError("Trips can be no longer than 14 days")
        travellers = self.adults + self.children
        if self.budget < travellers * 1_500:
            raise ValueError(
                f"Budget is too low for {travellers} traveller(s); enter at least ₹{travellers * 1_500:,}"
            )
        if self.senior_citizens > self.adults:
            raise ValueError("Senior citizens cannot exceed the number of adults")
        return self


class TripIntent(BaseModel):
    """Structured, provider-neutral planning intent for the constraint engine."""

    origin: str
    destinations: list[str] = Field(..., min_length=1, max_length=5)
    start_date: date
    end_date: date
    travellers: int = Field(..., ge=1, le=40)
    children: int = Field(0, ge=0, le=20)
    senior_travellers: int = Field(0, ge=0, le=20)
    budget: int = Field(..., ge=1_000, le=1_000_000)
    currency: str = Field("INR", min_length=3, max_length=3)
    travel_style: list[TravelVibe] = Field(default_factory=list)
    pace: TripPace = TripPace.BALANCED
    interests: list[TravelVibe] = Field(default_factory=list)
    diet: Optional[DietaryPreference] = None
    accessibility_requirements: Optional[str] = Field(None, max_length=500)
    preferred_transport: Optional[TransportMode] = None
    hotel_preference: AccommodationPreference = AccommodationPreference.BUDGET
    early_departure_allowed: bool = False
    late_arrival_allowed: bool = False
    mandatory_places: list[str] = Field(default_factory=list, max_length=20)
    excluded_places: list[str] = Field(default_factory=list, max_length=50)
    free_text_notes: str = Field("", max_length=2_000)

    @model_validator(mode="after")
    def validate_intent(self) -> "TripIntent":
        if self.end_date < self.start_date:
            raise ValueError("Return date cannot be before departure date")
        if (self.end_date - self.start_date).days + 1 > 14:
            raise ValueError("Trips can be no longer than 14 days")
        if self.children + self.senior_travellers > self.travellers:
            raise ValueError("Children and senior travellers cannot exceed total travellers")
        if self.budget < self.travellers * 1_500:
            raise ValueError(
                f"Budget is too low for {self.travellers} traveller(s); enter at least ₹{self.travellers * 1_500:,}"
            )
        if not self.destinations or any(not destination.strip() for destination in self.destinations):
            raise ValueError("At least one destination is required")
        if self.currency != "INR":
            raise ValueError("Only INR planning is currently supported")
        return self

    @classmethod
    def from_request(cls, request: TripRequest) -> "TripIntent":
        """Translate the current single-destination API request into intent."""

        return cls(
            origin=request.origin,
            destinations=[request.destination],
            start_date=request.start_date,
            end_date=request.end_date,
            travellers=request.adults + request.children,
            children=request.children,
            senior_travellers=request.senior_citizens,
            budget=request.budget,
            travel_style=list(request.vibes),
            pace=request.pace,
            interests=list(request.vibes),
            diet=request.dietary_preference,
            accessibility_requirements=request.accessibility_requirements,
            preferred_transport=request.transport_mode,
            hotel_preference=request.accommodation_preference,
            early_departure_allowed=request.allow_early_morning_travel,
            late_arrival_allowed=request.allow_late_night_travel,
            mandatory_places=list(request.mandatory_places),
            excluded_places=list(request.excluded_places),
            free_text_notes=request.free_text_notes or "",
        )


# ── Geo Models ─────────────────────────────────────────────────────────

class GeoPoint(BaseModel):
    lat: float
    lng: float


class CityInfo(BaseModel):
    name: str
    state: Optional[str] = None
    coordinates: GeoPoint
    iata_code: Optional[str] = None
    station_code: Optional[str] = None
    provenance: DataProvenance = Field(default_factory=_unavailable_provenance)


class DestinationPhoto(BaseModel):
    url: str
    alt: str
    photographer_name: Optional[str] = None
    photographer_url: Optional[str] = None
    provenance: DataProvenance = Field(default_factory=_unavailable_provenance)


class FestivalEvent(BaseModel):
    name: str
    start_date: date
    end_date: date
    description: str
    travel_tip: str


class PackingItem(BaseModel):
    item: str
    reason: str
    category: str = "essentials"


# ── Transport Models ───────────────────────────────────────────────────

class TransportOption(BaseModel):
    mode: TransportMode
    provider: str = Field(..., description="Airline or train name")
    code: Optional[str] = Field(None, description="Flight number or train number")
    price: int = Field(..., description="Price in INR")
    duration_minutes: int
    departure_time: Optional[str] = None
    arrival_time: Optional[str] = None
    departure_city: str
    arrival_city: str
    is_recommended: bool = False
    is_fallback: bool = Field(False, description="True if this is from static fallback data")
    field_provenance: dict[str, str] = Field(
        default_factory=dict,
        description="Per-field source labels; transport cards must not imply all data is live",
    )
    field_data_provenance: dict[str, DataProvenance] = Field(
        default_factory=dict,
        description="Per-field provider and freshness metadata",
    )
    provenance: DataProvenance = Field(default_factory=_unavailable_provenance)
    availability_status: str = "Not checked"
    last_checked_at: Optional[datetime] = None

    @model_validator(mode="after")
    def prevent_live_fallback_claims(self) -> "TransportOption":
        live_statuses = {DataStatus.LIVE, DataStatus.RECENTLY_VERIFIED}
        if self.is_fallback and self.provenance.status in live_statuses:
            raise ValueError("Fallback transport cannot be marked live/recently_verified")
        fare_provenance = self.field_data_provenance.get("fare")
        if self.is_fallback and fare_provenance and fare_provenance.status in live_statuses:
            raise ValueError("Fallback transport fare cannot be marked live/recently_verified")
        return self


# ── POI Models ─────────────────────────────────────────────────────────

class POI(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    category: str
    coordinates: GeoPoint
    osm_tags: Optional[dict] = None
    estimated_visit_minutes: int = 60
    estimated_cost: int = 0
    description: Optional[str] = None
    opening_hours: Optional[str] = None
    rating: Optional[float] = None
    provenance: DataProvenance = Field(default_factory=_unavailable_provenance)
    field_provenance: dict[str, DataProvenance] = Field(default_factory=dict)


# ── Weather Models ─────────────────────────────────────────────────────

class DayWeather(BaseModel):
    date: date
    temp_min: float
    temp_max: float
    condition: str  # e.g. "Clear", "Rain", "Clouds"
    icon: str       # OpenWeatherMap icon code
    rain_probability: float = 0.0
    severity: WeatherSeverity = WeatherSeverity.GREAT
    summary: str = ""
    alerts: list[str] = Field(default_factory=list, max_length=8)
    provenance: DataProvenance = Field(default_factory=_unavailable_provenance)


# ── Itinerary Models ──────────────────────────────────────────────────

class Activity(BaseModel):
    poi: POI
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    estimated_cost: int = 0
    notes: Optional[str] = None
    is_backup: bool = Field(False, description="True if this is a weather-backup activity")
    is_locked: bool = Field(False, description="True when the traveller wants this stop protected from edits")


class MealRecommendation(BaseModel):
    name: str
    cuisine: Optional[str] = None
    meal_type: str  # breakfast, lunch, dinner, snack
    estimated_cost: int
    location: Optional[GeoPoint] = None
    notes: Optional[str] = None
    provenance: DataProvenance = Field(default_factory=_unavailable_provenance)
    field_provenance: dict[str, DataProvenance] = Field(default_factory=dict)


class DayPlan(BaseModel):
    day_number: int
    date: date
    weather: Optional[DayWeather] = None
    transport: Optional[TransportOption] = None
    activities: list[Activity] = []
    meals: list[MealRecommendation] = []
    backup_activities: list[Activity] = []
    day_budget: int = 0
    day_spent: int = 0
    local_transport_minutes: int = 0
    local_transport_cost: int = 0
    notes: Optional[str] = None


class RouteSegment(BaseModel):
    """A segment of the route between two points, for map rendering."""
    from_point: GeoPoint
    to_point: GeoPoint
    geometry: Optional[list[list[float]]] = None  # [[lng, lat], ...]
    distance_km: float = 0
    duration_minutes: float = 0
    day_number: Optional[int] = None
    provenance: DataProvenance = Field(default_factory=_unavailable_provenance)


class BudgetBreakdown(BaseModel):
    outbound_transport: int = 0
    return_transport: int = 0
    transport: int = 0
    food: int = 0
    activities: int = 0
    accommodation: int = 0
    local_transport: int = 0
    taxes_buffer: int = 0
    miscellaneous: int = 0
    total_estimated: int = 0
    remaining: int = 0
    provenance: DataProvenance = Field(default_factory=_unavailable_provenance)


class Itinerary(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    origin: CityInfo
    destination: CityInfo
    start_date: date
    end_date: date
    total_days: int
    vibes: list[TravelVibe]
    accommodation_preference: AccommodationPreference = AccommodationPreference.BUDGET
    adults: int = 2
    children: int = 0
    travel_preference: TravelPreference = TravelPreference.BALANCED
    pace: TripPace = TripPace.BALANCED
    dietary_preference: Optional[DietaryPreference] = None
    senior_citizens: int = 0
    accessibility_requirements: Optional[str] = None
    mandatory_places: list[str] = Field(default_factory=list)
    excluded_places: list[str] = Field(default_factory=list)
    free_text_notes: Optional[str] = None
    allow_early_morning_travel: bool = False
    allow_late_night_travel: bool = False
    transport_options: list[TransportOption] = []
    selected_transport: Optional[TransportOption] = None
    day_plans: list[DayPlan] = []
    budget: BudgetBreakdown
    route_segments: list[RouteSegment] = []
    weather_forecast: list[DayWeather] = []
    destination_photos: list[DestinationPhoto] = []
    festivals: list[FestivalEvent] = []
    packing_list: list[PackingItem] = []
    share_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    generation_notes: list[str] = Field(
        default=[],
        description="Notes about the generation process (e.g., API fallbacks used)",
    )


# ── Share Models ───────────────────────────────────────────────────────

class TripShare(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    itinerary: Itinerary
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ── Response Models ────────────────────────────────────────────────────

class GenerationStatus(BaseModel):
    step: str
    message: str
    progress: int  # 0-100


class CitySearchResult(BaseModel):
    name: str
    state: Optional[str] = None
    display_name: str
    coordinates: GeoPoint
