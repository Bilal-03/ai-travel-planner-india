"""Feature-flagged provider gateway and legacy adapter shims.

The gateway owns provider selection and resilience. The callback adapters keep
the current service implementations as the default providers while exposing a
stable interface for future Amadeus, Duffel, Google, Mapbox, and contracted
Indian travel adapters.
"""

from __future__ import annotations

from typing import Awaitable, Callable, Optional

from app.config import Settings, settings
from app.models.trip import DayWeather, POI, RouteSegment
from app.providers.contracts import (
    BusOption,
    BusProvider,
    BusSearchRequest,
    ConfirmedOffer,
    FlightOffer,
    FlightProvider,
    FlightSearchRequest,
    HotelOffer,
    HotelProvider,
    HotelSearchRequest,
    PlaceProvider,
    PlaceSearchRequest,
    RailAvailability,
    RailOption,
    RailProvider,
    RailSearchRequest,
    RouteProvider,
    RouteRequest,
    WeatherProvider,
    WeatherRequest,
)
from app.providers.resilience import CircuitBreaker, ProviderExecutor, RetryPolicy


def _normalise_provider(value: str | None, default: str = "none") -> str:
    return (value or default).strip().casefold()


class CallbackFlightProvider:
    def __init__(self, callback: Callable[[FlightSearchRequest], Awaitable[list[dict]]], executor: ProviderExecutor):
        self._callback = callback
        self._executor = executor

    async def search(self, request: FlightSearchRequest) -> list[FlightOffer]:
        async def operation() -> list[FlightOffer]:
            return [FlightOffer.model_validate(item) for item in await self._callback(request)]

        return await self._executor.execute(operation)

    async def confirm(self, offer_id: str) -> ConfirmedOffer | None:
        return None


class CallbackRailProvider:
    def __init__(self, callback: Callable[[RailSearchRequest], Awaitable[list[dict]]], executor: ProviderExecutor):
        self._callback = callback
        self._executor = executor

    async def search_schedules(self, request: RailSearchRequest) -> list[RailOption]:
        async def operation() -> list[RailOption]:
            return [RailOption.model_validate(item) for item in await self._callback(request)]

        return await self._executor.execute(operation)

    async def search_availability(self, request: RailSearchRequest) -> list[RailAvailability]:
        # The current RailRadar integration is schedule-only by contract.
        return []


class CallbackPlaceProvider:
    def __init__(self, callback: Callable[[PlaceSearchRequest], Awaitable[list[dict]]], executor: ProviderExecutor):
        self._callback = callback
        self._executor = executor

    async def search(self, request: PlaceSearchRequest) -> list[POI]:
        async def operation() -> list[POI]:
            return [POI.model_validate(item) for item in await self._callback(request)]

        return await self._executor.execute(operation)


class CallbackRouteProvider:
    def __init__(self, callback: Callable[[RouteRequest], Awaitable[dict | None]], executor: ProviderExecutor):
        self._callback = callback
        self._executor = executor

    async def route(self, request: RouteRequest) -> RouteSegment | None:
        async def operation() -> RouteSegment | None:
            result = await self._callback(request)
            return RouteSegment.model_validate(result) if result else None

        return await self._executor.execute(operation)


class CallbackWeatherProvider:
    def __init__(self, callback: Callable[[WeatherRequest], Awaitable[list[dict]]], executor: ProviderExecutor):
        self._callback = callback
        self._executor = executor

    async def forecast(self, request: WeatherRequest) -> list[DayWeather]:
        async def operation() -> list[DayWeather]:
            return [DayWeather.model_validate(item) for item in await self._callback(request)]

        return await self._executor.execute(operation)


class EmptyFlightProvider:
    async def search(self, request: FlightSearchRequest) -> list[FlightOffer]:
        return []

    async def confirm(self, offer_id: str) -> ConfirmedOffer | None:
        return None


class EmptyHotelProvider:
    async def search(self, request: HotelSearchRequest) -> list[HotelOffer]:
        return []

    async def confirm(self, offer_id: str) -> ConfirmedOffer | None:
        return None


class EmptyRailProvider:
    async def search_schedules(self, request: RailSearchRequest) -> list[RailOption]:
        return []

    async def search_availability(self, request: RailSearchRequest) -> list[RailAvailability]:
        return []


class EmptyBusProvider:
    async def search(self, request: BusSearchRequest) -> list[BusOption]:
        return []


class EmptyPlaceProvider:
    async def search(self, request: PlaceSearchRequest) -> list[POI]:
        return []


class EmptyRouteProvider:
    async def route(self, request: RouteRequest) -> RouteSegment | None:
        return None


class EmptyWeatherProvider:
    async def forecast(self, request: WeatherRequest) -> list[DayWeather]:
        return []


class ProviderGateway:
    """Select one adapter per travel-data domain and wrap external calls safely."""

    def __init__(self, config: Settings | None = None) -> None:
        self.config = config or settings
        policy = RetryPolicy(
            timeout_seconds=self.config.provider_timeout_seconds,
            max_retries=self.config.provider_max_retries,
            backoff_seconds=self.config.provider_retry_backoff_seconds,
        )
        self._executors = {
            domain: ProviderExecutor(
                policy=policy,
                circuit=CircuitBreaker(
                    failure_threshold=self.config.provider_circuit_failure_threshold,
                    cooldown_seconds=self.config.provider_circuit_cooldown_seconds,
                ),
            )
            for domain in ("flight", "hotel", "rail", "bus", "places", "routes", "weather")
        }

    def selected_providers(self) -> dict[str, str]:
        return {
            "flight": _normalise_provider(self.config.flight_provider, "legacy"),
            "hotel": _normalise_provider(self.config.hotel_provider),
            "places": _normalise_provider(self.config.places_provider, "overpass"),
            "routes": _normalise_provider(self.config.routes_provider, "osrm"),
            "rail": _normalise_provider(self.config.rail_provider, "legacy"),
            "bus": _normalise_provider(self.config.bus_provider),
            "weather": _normalise_provider(self.config.weather_provider, "openweather"),
        }

    def flight_provider(self, callback: Callable[[FlightSearchRequest], Awaitable[list[dict]]]) -> FlightProvider:
        selected = self.selected_providers()["flight"]
        if selected in {"legacy", "skyscanner"}:
            return CallbackFlightProvider(callback, self._executors["flight"])
        return EmptyFlightProvider()

    def hotel_provider(self) -> HotelProvider:
        # No hotel inventory is shown until a contracted adapter is added.
        return EmptyHotelProvider()

    def rail_provider(self, callback: Callable[[RailSearchRequest], Awaitable[list[dict]]]) -> RailProvider:
        selected = self.selected_providers()["rail"]
        if selected in {"legacy", "railradar"}:
            return CallbackRailProvider(callback, self._executors["rail"])
        return EmptyRailProvider()

    def bus_provider(self) -> BusProvider:
        # Do not invent operators or schedules while BUS_PROVIDER is unset.
        return EmptyBusProvider()

    def places_provider(self, callback: Callable[[PlaceSearchRequest], Awaitable[list[dict]]]) -> PlaceProvider:
        selected = self.selected_providers()["places"]
        if selected in {"legacy", "overpass", "osm"}:
            return CallbackPlaceProvider(callback, self._executors["places"])
        return EmptyPlaceProvider()

    def routes_provider(self, callback: Callable[[RouteRequest], Awaitable[dict | None]]) -> RouteProvider:
        selected = self.selected_providers()["routes"]
        if selected in {"legacy", "osrm"}:
            return CallbackRouteProvider(callback, self._executors["routes"])
        return EmptyRouteProvider()

    def weather_provider(self, callback: Callable[[WeatherRequest], Awaitable[list[dict]]]) -> WeatherProvider:
        selected = self.selected_providers()["weather"]
        if selected in {"legacy", "openweather"}:
            return CallbackWeatherProvider(callback, self._executors["weather"])
        return EmptyWeatherProvider()


_gateway: Optional[ProviderGateway] = None


def get_provider_gateway() -> ProviderGateway:
    global _gateway
    if _gateway is None:
        _gateway = ProviderGateway()
    return _gateway


def reset_provider_gateway() -> None:
    """Reset the lazy singleton for tests and controlled runtime reconfiguration."""

    global _gateway
    _gateway = None
