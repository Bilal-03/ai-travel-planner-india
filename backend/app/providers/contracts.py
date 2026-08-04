"""Provider-neutral request, response, and adapter contracts.

Provider-specific payloads are deliberately not part of these models. Adapter
implementations normalize them into the existing itinerary-domain models before
the services return anything to an API or the planner.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field, field_validator

from app.models.trip import (
    DataProvenance,
    DataStatus,
    DayWeather,
    GeoPoint,
    POI,
    RouteSegment,
    TransportMode,
    TransportOption,
)


class FlightSearchRequest(BaseModel):
    origin: str = Field(min_length=2, max_length=120)
    destination: str = Field(min_length=2, max_length=120)
    departure_date: str = Field(min_length=8, max_length=32)
    max_price: int | None = Field(default=None, ge=0)
    distance_km: float | None = Field(default=None, ge=0)


class RailSearchRequest(BaseModel):
    origin: str = Field(min_length=2, max_length=120)
    destination: str = Field(min_length=2, max_length=120)
    travel_date: str | None = Field(default=None, max_length=32)
    distance_km: float | None = Field(default=None, ge=0)


class PlaceSearchRequest(BaseModel):
    coordinates: GeoPoint
    vibes: list[str] = Field(default_factory=list, max_length=20)
    radius: int = Field(default=10_000, ge=100, le=50_000)
    limit: int = Field(default=30, ge=1, le=100)
    city: str | None = Field(default=None, max_length=120)


class RouteRequest(BaseModel):
    from_point: GeoPoint
    to_point: GeoPoint


class WeatherRequest(BaseModel):
    coordinates: GeoPoint
    start_date: str
    end_date: str


class ConfirmedOffer(BaseModel):
    """Normalized confirmation metadata; booking remains outside this phase."""

    offer_id: str
    provider: str
    status: DataStatus
    expires_at: str | None = None
    booking_reference: str | None = None
    provenance: DataProvenance


class FlightOffer(TransportOption):
    """A normalized flight result safe to pass into itinerary services."""

    @field_validator("mode")
    @classmethod
    def require_flight_mode(cls, value: TransportMode) -> TransportMode:
        if value != TransportMode.FLIGHT:
            raise ValueError("Flight provider returned a non-flight option")
        return value


class RailOption(TransportOption):
    """A normalized rail schedule; fare and seats may remain unavailable."""

    @field_validator("mode")
    @classmethod
    def require_train_mode(cls, value: TransportMode) -> TransportMode:
        if value != TransportMode.TRAIN:
            raise ValueError("Rail provider returned a non-train option")
        return value


class RailAvailability(BaseModel):
    option_id: str
    travel_date: str | None = None
    availability_status: str = "Not available"
    fare: int | None = Field(default=None, ge=0)
    provenance: DataProvenance = Field(default_factory=DataProvenance)


class FlightProvider(Protocol):
    async def search(self, request: FlightSearchRequest) -> list[FlightOffer]: ...

    async def confirm(self, offer_id: str) -> ConfirmedOffer | None: ...


class RailProvider(Protocol):
    async def search_schedules(self, request: RailSearchRequest) -> list[RailOption]: ...

    async def search_availability(self, request: RailSearchRequest) -> list[RailAvailability]: ...


class PlaceProvider(Protocol):
    async def search(self, request: PlaceSearchRequest) -> list[POI]: ...


class RouteProvider(Protocol):
    async def route(self, request: RouteRequest) -> RouteSegment | None: ...


class WeatherProvider(Protocol):
    async def forecast(self, request: WeatherRequest) -> list[DayWeather]: ...
