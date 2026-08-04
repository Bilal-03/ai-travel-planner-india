"""Deterministic multi-city planner and scoped route-edit operations.

The existing Gemini planner remains the single-destination path. Phase 6 uses
the same provider-backed facts, but composes them into a durable aggregate so
stays, legs, and visits can be edited independently.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from collections.abc import Awaitable, Callable
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from app.models.trip import (
    BudgetBreakdown,
    CityInfo,
    DataProvenance,
    DataStatus,
    DestinationStay,
    DayWeather,
    ItineraryDay,
    MealRecommendation,
    MultiCityTripRequest,
    POI,
    TransportMode,
    TransportSelection,
    TravelLeg,
    Trip,
    Visit,
    WeatherSeverity,
)
from app.services.geocoding import geocode_to_city_info, haversine_distance
from app.services.poi_discovery import discover_pois
from app.services.transport import search_transport
from app.services.weather import get_forecast

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[str, str, int], Awaitable[None] | None]

def _estimate_provenance(disclaimer: str) -> DataProvenance:
    return DataProvenance(
        provider="YatraAI multi-city planner",
        status=DataStatus.ESTIMATED,
        retrieved_at=datetime.now(timezone.utc),
        confidence=0.55,
        source_reference="app://yatraai-multi-city-planner",
        disclaimer=disclaimer,
    )


async def _report(progress: Optional[ProgressCallback], step: str, message: str, percent: int) -> None:
    if not progress:
        return
    result = progress(step, message, percent)
    if inspect.isawaitable(result):
        await result


def _duration_label(minutes: int) -> str:
    hours, remainder = divmod(max(0, minutes), 60)
    return f"{hours}:{remainder:02d}"


def _next_time(start: str, duration_minutes: int) -> str:
    hour, minute = (int(part) for part in start.split(":"))
    total = hour * 60 + minute + max(30, duration_minutes)
    return f"{min(23, total // 60):02d}:{total % 60:02d}"


def _select_transport_offer(options, preferred_mode: Optional[TransportMode]):
    if not options:
        return None
    if preferred_mode:
        preferred = next((option for option in options if option.mode == preferred_mode), None)
        if preferred:
            return preferred
    return next((option for option in options if option.is_recommended), options[0])


async def _build_transport(
    origin: CityInfo,
    stays: list[DestinationStay],
    request: MultiCityTripRequest,
) -> tuple[list[TravelLeg], list[TransportSelection]]:
    endpoints: list[tuple[CityInfo, CityInfo, date, str | None, str | None]] = []
    first = stays[0]
    endpoints.append((origin, first.city, request.start_date, None, first.id))
    for previous, current in zip(stays, stays[1:]):
        endpoints.append((previous.city, current.city, current.arrival_date, previous.id, current.id))
    last = stays[-1]
    endpoints.append((last.city, origin, request.end_date, last.id, None))

    async def one_leg(endpoint: tuple[CityInfo, CityInfo, date, str | None, str | None]):
        from_city, to_city, leg_date, from_stay_id, to_stay_id = endpoint
        distance = haversine_distance(from_city.coordinates, to_city.coordinates)
        try:
            options = await search_transport(
                from_city.name,
                to_city.name,
                leg_date.isoformat(),
                max(1_000, request.budget // max(1, len(endpoints))),
                distance,
            )
        except Exception as error:  # provider failures must not erase the route graph
            logger.warning("Multi-city transport lookup failed for %s → %s: %s", from_city.name, to_city.name, error)
            options = []
        selected = _select_transport_offer(options, request.transport_mode)
        mode = selected.mode if selected else (request.transport_mode or TransportMode.ROAD)
        leg = TravelLeg(
            origin=from_city,
            destination=to_city,
            date=leg_date,
            mode=mode,
            selected_offer=selected,
            alternatives=[option for option in options if option is not selected],
            duration_minutes=selected.duration_minutes if selected else 0,
            fare=selected.price if selected else 0,
            origin_stay_id=from_stay_id,
            destination_stay_id=to_stay_id,
            provenance=(selected.provenance if selected else _estimate_provenance(
                "No transport offer was returned; verify the leg before booking."
            )),
        )
        return leg, TransportSelection(
            leg_id=leg.id,
            selected_offer=selected,
            alternatives=leg.alternatives,
            provenance=leg.provenance,
        )

    results = await asyncio.gather(*(one_leg(endpoint) for endpoint in endpoints))
    return [result[0] for result in results], [result[1] for result in results]


async def _fetch_stay_facts(stays: list[DestinationStay], request: MultiCityTripRequest):
    vibes = [vibe.value for vibe in request.vibes]

    async def facts_for(stay: DestinationStay):
        try:
            poi_data, weather_data = await asyncio.gather(
                discover_pois(
                    stay.city.coordinates.lat,
                    stay.city.coordinates.lng,
                    vibes,
                    city=stay.city.name,
                    limit=12,
                ),
                get_forecast(
                    stay.city.coordinates.lat,
                    stay.city.coordinates.lng,
                    stay.arrival_date.isoformat(),
                    stay.departure_date.isoformat(),
                ),
                return_exceptions=True,
            )
        except Exception as error:  # defensive: one city must not cancel the route
            logger.warning("Multi-city facts failed for %s: %s", stay.city.name, error)
            return [], []
        if isinstance(poi_data, Exception):
            logger.warning("POI discovery failed for %s: %s", stay.city.name, poi_data)
            poi_data = []
        if isinstance(weather_data, Exception):
            logger.warning("Weather lookup failed for %s: %s", stay.city.name, weather_data)
            weather_data = []
        return poi_data, weather_data

    return await asyncio.gather(*(facts_for(stay) for stay in stays))


def _make_visits_and_weather(
    stays: list[DestinationStay],
    facts,
) -> tuple[list[Visit], dict[tuple[str, date], DayWeather]]:
    visits: list[Visit] = []
    weather_by_stay_date: dict[tuple[str, date], DayWeather] = {}
    for stay, (poi_data, weather_data) in zip(stays, facts):
        pois: list[POI] = []
        for item in poi_data or []:
            try:
                pois.append(POI.model_validate(item))
            except ValueError:
                continue
        for item in weather_data or []:
            try:
                weather = DayWeather.model_validate(item)
            except ValueError:
                continue
            weather_by_stay_date[(stay.id, weather.date)] = weather
        for day_offset in range(stay.nights):
            visit_date = stay.arrival_date + timedelta(days=day_offset)
            if not pois:
                continue
            poi = pois[day_offset % len(pois)]
            visits.append(
                Visit(
                    stay_id=stay.id,
                    date=visit_date,
                    poi=poi,
                    start_time="10:00",
                    end_time=_next_time("10:00", poi.estimated_visit_minutes),
                    estimated_cost=poi.estimated_cost,
                    notes=f"Keep this {stay.city.name} visit flexible until opening hours are rechecked.",
                )
            )
    return visits, weather_by_stay_date


def _build_days(
    trip_start: date,
    trip_end: date,
    stays: list[DestinationStay],
    legs: list[TravelLeg],
    visits: list[Visit],
    weather_by_stay_date: dict[tuple[str, date], DayWeather],
    travellers: int,
) -> list[ItineraryDay]:
    days: list[ItineraryDay] = []
    leg_by_date = {leg.date: leg for leg in legs}
    for index in range((trip_end - trip_start).days + 1):
        current_date = trip_start + timedelta(days=index)
        stay = next(
            (candidate for candidate in stays if candidate.arrival_date <= current_date < candidate.departure_date),
            None,
        )
        day_visits = [visit for visit in visits if visit.date == current_date and (not stay or visit.stay_id == stay.id)]
        weather = weather_by_stay_date.get((stay.id, current_date)) if stay else None
        leg = leg_by_date.get(current_date)
        activity_cost = sum(visit.estimated_cost for visit in day_visits)
        food_cost = 400 * travellers
        meals = [
            MealRecommendation(
                name="Suggested local meal",
                cuisine=None,
                meal_type="lunch",
                estimated_cost=food_cost,
                notes="Choose a current, well-reviewed restaurant after arrival.",
                provenance=_estimate_provenance("Meal pricing is a planning estimate; verify menus locally."),
            )
        ]
        day_budget = food_cost + activity_cost
        days.append(
            ItineraryDay(
                day_number=index + 1,
                date=current_date,
                stay_id=stay.id if stay else None,
                destination=stay.city if stay else None,
                weather=weather,
                visits=day_visits,
                meals=meals,
                travel_leg_id=leg.id if leg else None,
                day_budget=day_budget,
                day_spent=activity_cost,
                notes=(
                    f"Travel leg: {leg.origin.name} → {leg.destination.name}."
                    if leg else ("Return to the origin city." if current_date == trip_end else None)
                ),
            )
        )
    return days


def _build_budget(
    request: MultiCityTripRequest,
    legs: list[TravelLeg],
    visits: list[Visit],
) -> BudgetBreakdown:
    travellers = request.adults + request.children
    transport = sum(leg.fare for leg in legs)
    activities = sum(visit.estimated_cost for visit in visits)
    food = request.adults + request.children
    food *= ((request.end_date - request.start_date).days + 1) * 400
    local_transport = ((request.end_date - request.start_date).days + 1) * travellers * 150
    subtotal = transport + activities + food + local_transport
    taxes_buffer = round(subtotal * 0.05)
    total = subtotal + taxes_buffer
    return BudgetBreakdown(
        outbound_transport=legs[0].fare if legs else 0,
        return_transport=legs[-1].fare if legs else 0,
        transport=transport,
        food=food,
        activities=activities,
        local_transport=local_transport,
        taxes_buffer=taxes_buffer,
        total_estimated=total,
        remaining=request.budget - total,
        provenance=_estimate_provenance(
            "Multi-city transport, food, activity, and local-travel amounts are planning estimates; verify live prices before booking."
        ),
    )


async def generate_multi_city_trip(
    request: MultiCityTripRequest,
    progress: Optional[ProgressCallback] = None,
) -> Trip:
    """Generate a complete multi-city aggregate from explicit stays."""

    await _report(progress, "starting", "Structuring your multi-city route…", 5)
    city_names = [request.origin] + [stay.destination for stay in request.stays]
    cities = await asyncio.gather(*(geocode_to_city_info(name) for name in city_names))
    if any(city is None for city in cities):
        missing = city_names[next(index for index, city in enumerate(cities) if city is None)]
        raise ValueError(f"Could not locate {missing} in the India destination index")
    origin = cities[0]
    destination_cities = cities[1:]
    assert origin is not None
    cursor = request.start_date
    stays: list[DestinationStay] = []
    for position, (stay_request, city) in enumerate(zip(request.stays, destination_cities)):
        assert city is not None
        departure = cursor + timedelta(days=stay_request.nights)
        stays.append(
            DestinationStay(
                city=city,
                position=position,
                arrival_date=cursor,
                departure_date=departure,
                nights=stay_request.nights,
                notes=stay_request.notes,
                provenance=city.provenance,
            )
        )
        cursor = departure

    await _report(progress, "resolving_locations", "Mapped each stay and travel leg…", 20)
    legs, transport_selections = await _build_transport(origin, stays, request)
    await _report(progress, "fetching_transport", "Collected route options for every leg…", 40)
    facts = await _fetch_stay_facts(stays, request)
    visits, weather = _make_visits_and_weather(stays, facts)
    await _report(progress, "fetching_places", "Collected destination-scoped places and weather…", 60)

    days = _build_days(
        request.start_date,
        request.end_date,
        stays,
        legs,
        visits,
        weather,
        request.adults + request.children,
    )
    budget = _build_budget(request, legs, visits)
    await _report(progress, "optimising", "Assembled independently editable stays, visits, and legs…", 80)

    return Trip(
        origin=origin,
        destination_stays=stays,
        travel_legs=legs,
        itinerary_days=days,
        visits=visits,
        transport_selections=transport_selections,
        start_date=request.start_date,
        end_date=request.end_date,
        total_days=(request.end_date - request.start_date).days + 1,
        vibes=request.vibes,
        adults=request.adults,
        children=request.children,
        travel_preference=request.travel_preference,
        pace=request.pace,
        dietary_preference=request.dietary_preference,
        senior_citizens=request.senior_citizens,
        accessibility_requirements=request.accessibility_requirements,
        budget=budget,
        generation_notes=[
            "Each destination stay has a stable identity; changing the route does not require rebuilding unrelated place visits.",
            "Transport values are estimates or provider references and must be verified before booking.",
        ],
    )


def _shift_visit_dates(trip: Trip, old_stays: dict[str, DestinationStay]) -> None:
    for visit in trip.visits:
        old_stay = old_stays.get(visit.stay_id)
        current_stay = next((stay for stay in trip.destination_stays if stay.id == visit.stay_id), None)
        if not old_stay or not current_stay:
            continue
        offset = (visit.date - old_stay.arrival_date).days
        visit.date = current_stay.arrival_date + timedelta(days=max(0, offset))


def _preserved_weather(trip: Trip, old_stays: dict[str, DestinationStay]) -> dict[tuple[str, date], DayWeather]:
    preserved: dict[tuple[str, date], DayWeather] = {}
    for day in trip.itinerary_days:
        if not day.weather or not day.stay_id or day.stay_id not in old_stays:
            continue
        old_stay = old_stays[day.stay_id]
        new_stay = next((stay for stay in trip.destination_stays if stay.id == day.stay_id), None)
        if not new_stay:
            continue
        offset = (day.date - old_stay.arrival_date).days
        weather = deepcopy(day.weather)
        weather.date = new_stay.arrival_date + timedelta(days=max(0, offset))
        preserved[(new_stay.id, weather.date)] = weather
    return preserved


def _rebuild_days_without_regenerating_visits(trip: Trip, old_stays: dict[str, DestinationStay]) -> None:
    weather = _preserved_weather(trip, old_stays)
    trip.itinerary_days = _build_days(
        trip.start_date,
        trip.end_date,
        trip.destination_stays,
        trip.travel_legs,
        trip.visits,
        weather,
        trip.adults + trip.children,
    )


def _reprice_after_edit(trip: Trip, old_budget_limit: int) -> None:
    transport = sum(leg.fare for leg in trip.travel_legs)
    activities = sum(visit.estimated_cost for visit in trip.visits)
    food = trip.adults + trip.children
    food *= trip.total_days * 400
    local_transport = trip.total_days * (trip.adults + trip.children) * 150
    subtotal = transport + activities + food + local_transport
    taxes = round(subtotal * 0.05)
    total = subtotal + taxes
    trip.budget = trip.budget.model_copy(update={
        "outbound_transport": trip.travel_legs[0].fare if trip.travel_legs else 0,
        "return_transport": trip.travel_legs[-1].fare if trip.travel_legs else 0,
        "transport": transport,
        "activities": activities,
        "food": food,
        "local_transport": local_transport,
        "taxes_buffer": taxes,
        "total_estimated": total,
        "remaining": old_budget_limit - total,
    })


async def reorder_multi_city_trip(trip: Trip, destination_stay_ids: list[str]) -> Trip:
    """Reorder stays, shifting local visits and rebuilding only the leg graph."""

    current_ids = [stay.id for stay in trip.destination_stays]
    if len(destination_stay_ids) != len(current_ids) or set(destination_stay_ids) != set(current_ids):
        raise ValueError("Reorder must include every destination stay exactly once")
    old_stays = {stay.id: stay.model_copy(deep=True) for stay in trip.destination_stays}
    trip = trip.model_copy(deep=True)
    trip.destination_stays = [
        next(stay for stay in trip.destination_stays if stay.id == stay_id)
        for stay_id in destination_stay_ids
    ]
    cursor = trip.start_date
    for position, stay in enumerate(trip.destination_stays):
        stay.position = position
        stay.arrival_date = cursor
        stay.departure_date = cursor + timedelta(days=stay.nights)
        cursor = stay.departure_date
    trip.end_date = cursor
    trip.total_days = (trip.end_date - trip.start_date).days + 1
    _shift_visit_dates(trip, old_stays)
    request = MultiCityTripRequest(
        origin=trip.origin.name,
        stays=[{"destination": stay.city.name, "nights": stay.nights, "notes": stay.notes} for stay in trip.destination_stays],
        start_date=trip.start_date,
        budget=max(1_000, trip.budget.total_estimated + max(0, trip.budget.remaining)),
        vibes=trip.vibes,
        transport_mode=None,
        adults=trip.adults,
        children=trip.children,
        travel_preference=trip.travel_preference,
        pace=trip.pace,
        dietary_preference=trip.dietary_preference,
        senior_citizens=trip.senior_citizens,
        accessibility_requirements=trip.accessibility_requirements,
    )
    trip.travel_legs, trip.transport_selections = await _build_transport(trip.origin, trip.destination_stays, request)
    _rebuild_days_without_regenerating_visits(trip, old_stays)
    _reprice_after_edit(trip, request.budget)
    trip.generation_notes.append("Destination order changed; visits and stay identities were preserved while affected legs were recalculated.")
    return trip


def update_multi_city_stay(
    trip: Trip,
    stay_id: str,
    *,
    nights: Optional[int] = None,
    notes: Optional[str] = None,
) -> Trip:
    """Edit one stay in place without rediscovering unrelated destinations."""

    if nights is not None and not 1 <= nights <= 14:
        raise ValueError("Stay nights must be between 1 and 14")
    old_stays = {stay.id: stay.model_copy(deep=True) for stay in trip.destination_stays}
    updated = trip.model_copy(deep=True)
    selected = next((stay for stay in updated.destination_stays if stay.id == stay_id), None)
    if not selected:
        raise ValueError("Destination stay not found")
    if nights is not None:
        selected.nights = nights
    if notes is not None:
        selected.notes = notes
    if sum(stay.nights for stay in updated.destination_stays) + 1 > 14:
        raise ValueError("Multi-city trips can be no longer than 14 days")
    cursor = updated.start_date
    for stay in updated.destination_stays:
        stay.arrival_date = cursor
        stay.departure_date = cursor + timedelta(days=stay.nights)
        cursor = stay.departure_date
    updated.end_date = cursor
    updated.total_days = (updated.end_date - updated.start_date).days + 1
    _shift_visit_dates(updated, old_stays)
    leg_dates = [updated.start_date] + [stay.arrival_date for stay in updated.destination_stays[1:]] + [updated.end_date]
    for leg, leg_date in zip(updated.travel_legs, leg_dates):
        leg.date = leg_date
    _rebuild_days_without_regenerating_visits(updated, old_stays)
    _reprice_after_edit(updated, trip.budget.total_estimated + max(0, trip.budget.remaining))
    updated.generation_notes.append(f"Only the {selected.city.name} stay was edited; unrelated place visits were retained.")
    return updated
