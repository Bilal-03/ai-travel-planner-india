"""Phase 6 multi-city graph, scoped edits, and explicit memory tests."""

from __future__ import annotations

import asyncio
from datetime import date, timedelta

from app.models.account import AccountRegistrationRequest, PreferenceMemoryUpdate
from app.models.trip import (
    CityInfo,
    DataProvenance,
    GeoPoint,
    MultiCityTripRequest,
    POI,
    TransportMode,
    TransportOption,
)
from app.services import account_service
from app.services import multi_city_planner as planner


def _request() -> MultiCityTripRequest:
    start = date.today() + timedelta(days=20)
    return MultiCityTripRequest(
        origin="Delhi",
        stays=[
            {"destination": "Jaipur", "nights": 2},
            {"destination": "Jodhpur", "nights": 2},
            {"destination": "Udaipur", "nights": 3},
        ],
        start_date=start,
        budget=60_000,
        vibes=["culture"],
    )


def _city(name: str) -> CityInfo:
    points = {
        "Delhi": (28.6139, 77.2090),
        "Jaipur": (26.9124, 75.7873),
        "Jodhpur": (26.2389, 73.0243),
        "Udaipur": (24.5854, 73.7125),
    }
    lat, lng = points[name]
    return CityInfo(name=name, coordinates=GeoPoint(lat=lat, lng=lng))


def _patch_provider_facts(monkeypatch):
    async def fake_geocode(name: str):
        return _city(name)

    async def fake_transport(origin, destination, travel_date, budget, distance):
        return [TransportOption(
            mode=TransportMode.TRAIN,
            provider="Test schedule reference",
            price=900,
            duration_minutes=240,
            departure_city=origin,
            arrival_city=destination,
            is_recommended=True,
            provenance=DataProvenance(provider="test", status="static_reference", disclaimer="test"),
        )]

    async def fake_pois(lat, lng, vibes, radius=10000, limit=30, city=None):
        return [{
            "id": f"poi-{city}",
            "name": f"{city} landmark",
            "category": "culture",
            "coordinates": {"lat": lat, "lng": lng},
            "estimated_visit_minutes": 90,
            "estimated_cost": 200,
            "description": None,
            "opening_hours": None,
        }]

    async def fake_weather(lat, lng, start_date, end_date):
        return []

    monkeypatch.setattr(planner, "geocode_to_city_info", fake_geocode)
    monkeypatch.setattr(planner, "search_transport", fake_transport)
    monkeypatch.setattr(planner, "discover_pois", fake_pois)
    monkeypatch.setattr(planner, "get_forecast", fake_weather)


def _generated(monkeypatch):
    _patch_provider_facts(monkeypatch)
    return asyncio.run(planner.generate_multi_city_trip(_request()))


def test_three_city_trip_has_explicit_stays_and_return_legs(monkeypatch):
    trip = _generated(monkeypatch)

    assert [stay.city.name for stay in trip.destination_stays] == ["Jaipur", "Jodhpur", "Udaipur"]
    assert len(trip.travel_legs) == 4
    assert (trip.travel_legs[0].origin.name, trip.travel_legs[0].destination.name) == ("Delhi", "Jaipur")
    assert (trip.travel_legs[-1].origin.name, trip.travel_legs[-1].destination.name) == ("Udaipur", "Delhi")
    assert trip.total_days == 8
    assert trip.itinerary_days[-1].destination is None


def test_reordering_recalculates_legs_but_preserves_visits(monkeypatch):
    trip = _generated(monkeypatch)
    original_visit_ids = {visit.id for visit in trip.visits}
    reordered = asyncio.run(planner.reorder_multi_city_trip(
        trip,
        [trip.destination_stays[2].id, trip.destination_stays[0].id, trip.destination_stays[1].id],
    ))

    assert [stay.city.name for stay in reordered.destination_stays] == ["Udaipur", "Jaipur", "Jodhpur"]
    assert (reordered.travel_legs[0].origin.name, reordered.travel_legs[0].destination.name) == ("Delhi", "Udaipur")
    assert (reordered.travel_legs[1].origin.name, reordered.travel_legs[1].destination.name) == ("Udaipur", "Jaipur")
    assert {visit.id for visit in reordered.visits} == original_visit_ids


def test_editing_one_stay_does_not_regenerate_unrelated_visits(monkeypatch):
    trip = _generated(monkeypatch)
    original_pois = {stay_id: {visit.poi.id for visit in trip.visits if visit.stay_id == stay_id} for stay_id in [stay.id for stay in trip.destination_stays]}
    selected = trip.destination_stays[0]
    updated = planner.update_multi_city_stay(trip, selected.id, nights=3)

    assert updated.destination_stays[0].nights == 3
    for stay in updated.destination_stays[1:]:
        assert {visit.poi.id for visit in updated.visits if visit.stay_id == stay.id} == original_pois[stay.id]
    assert updated.destination_stays[0].id == selected.id


def test_preference_memory_is_explicitly_editable_and_deletable():
    session = asyncio.run(account_service.create_anonymous_session())
    upgraded = asyncio.run(account_service.register_account(
        AccountRegistrationRequest(email=f"phase6-{session.account.id}@example.com", display_name="Phase 6"),
        session.access_token,
    ))
    saved = asyncio.run(account_service.update_preferences(
        upgraded.account.id,
        PreferenceMemoryUpdate(preferred_transport=TransportMode.TRAIN, typical_budget_min=10_000),
    ))
    assert saved.preferred_transport == TransportMode.TRAIN
    assert saved.typical_budget_min == 10_000

    disabled = asyncio.run(account_service.update_preferences(
        upgraded.account.id,
        PreferenceMemoryUpdate(memory_enabled=False),
    ))
    assert disabled.memory_enabled is False
    assert disabled.preferred_transport is None

    deleted = asyncio.run(account_service.delete_preferences(upgraded.account.id))
    assert deleted.memory_enabled is True
    asyncio.run(account_service.delete_account(upgraded.account.id))
    assert asyncio.run(account_service.get_account_for_token(upgraded.access_token)) is None

