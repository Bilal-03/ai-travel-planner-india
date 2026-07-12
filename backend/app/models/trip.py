"""
Pydantic models for the AI Travel Itinerary Planner.
All monetary values are in INR (₹).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


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


class WeatherSeverity(str, Enum):
    GREAT = "great"        # Clear / sunny
    OKAY = "okay"          # Partly cloudy / mild
    INDOOR = "indoor"      # Rain / storm — indoor backup recommended


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


# ── Itinerary Models ──────────────────────────────────────────────────

class Activity(BaseModel):
    poi: POI
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    estimated_cost: int = 0
    notes: Optional[str] = None
    is_backup: bool = Field(False, description="True if this is a weather-backup activity")


class MealRecommendation(BaseModel):
    name: str
    cuisine: Optional[str] = None
    meal_type: str  # breakfast, lunch, dinner, snack
    estimated_cost: int
    location: Optional[GeoPoint] = None
    notes: Optional[str] = None


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
    notes: Optional[str] = None


class RouteSegment(BaseModel):
    """A segment of the route between two points, for map rendering."""
    from_point: GeoPoint
    to_point: GeoPoint
    geometry: Optional[list[list[float]]] = None  # [[lng, lat], ...]
    distance_km: float = 0
    duration_minutes: float = 0


class BudgetBreakdown(BaseModel):
    transport: int = 0
    food: int = 0
    activities: int = 0
    accommodation: int = 0
    miscellaneous: int = 0
    total_estimated: int = 0
    remaining: int = 0


class Itinerary(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    origin: CityInfo
    destination: CityInfo
    start_date: date
    end_date: date
    total_days: int
    vibes: list[TravelVibe]
    transport_options: list[TransportOption] = []
    selected_transport: Optional[TransportOption] = None
    day_plans: list[DayPlan] = []
    budget: BudgetBreakdown
    route_segments: list[RouteSegment] = []
    weather_forecast: list[DayWeather] = []
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
