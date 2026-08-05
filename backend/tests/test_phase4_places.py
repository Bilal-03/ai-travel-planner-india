"""Phase 4 place discovery and saved-place workspace contracts."""

from __future__ import annotations

import asyncio
from datetime import date, timedelta

from fastapi import Response

from app.api import search as search_api
from app.api import trips as trips_api
from app.models.trip import BudgetBreakdown, CityInfo, DayPlan, GeoPoint, Itinerary, Place
from app.services.workspace_places import add_place_to_day, normalise_pois_to_places, remove_saved_place, save_place


def _place() -> Place:
    return Place(
        id="place-amber-fort",
        name="Amber Fort",
        category="fort",
        coordinates=GeoPoint(lat=26.9855, lng=75.8513),
        city="Jaipur",
        state="Rajasthan",
        estimated_visit_minutes=180,
        estimated_cost=600,
        description="A heritage fort in the Jaipur hills.",
    )


def _itinerary() -> Itinerary:
    start = date.today() + timedelta(days=40)
    return Itinerary(
        id="phase4-trip",
        origin=CityInfo(name="Delhi", state="Delhi", coordinates=GeoPoint(lat=28.6139, lng=77.2090)),
        destination=CityInfo(name="Jaipur", state="Rajasthan", coordinates=GeoPoint(lat=26.9124, lng=75.7873)),
        start_date=start,
        end_date=start + timedelta(days=1),
        total_days=2,
        members=2,
        day_plans=[
            DayPlan(day_number=1, date=start, day_budget=2_000),
            DayPlan(day_number=2, date=start + timedelta(days=1), day_budget=2_000),
        ],
        budget=BudgetBreakdown(total_estimated=2_000, remaining=2_000),
    )


def test_normalise_places_has_stable_ids_and_search_metadata():
    raw = {
        "name": "Amber Fort",
        "category": "fort",
        "coordinates": {"lat": 26.9855, "lng": 75.8513},
        "estimated_visit_minutes": 180,
        "estimated_cost": 600,
        "opening_hours": "09:00-17:00",
        "osm_tags": {"website": "https://example.test/amber"},
    }

    first = normalise_pois_to_places([raw], city="Jaipur", query="amber")
    second = normalise_pois_to_places([raw], city="Jaipur", query="amber")

    assert first[0].id == second[0].id
    assert first[0].estimated_visit_minutes == 180
    assert first[0].estimated_cost == 600
    assert first[0].official_url == "https://example.test/amber"
    assert first[0].maps_url.startswith("https://www.google.com/maps/search/")


def test_place_search_endpoint_returns_normalized_results(monkeypatch):
    async def fake_discover(**kwargs):
        assert kwargs["city"] == "Jaipur"
        assert "fort" in kwargs["focus_terms"]
        return [{
            "name": "Amber Fort",
            "category": "fort",
            "coordinates": {"lat": 26.9855, "lng": 75.8513},
            "estimated_visit_minutes": 180,
            "estimated_cost": 600,
        }]

    monkeypatch.setattr(search_api, "discover_pois", fake_discover)
    results = asyncio.run(search_api.search_places_endpoint(
        lat=26.9124,
        lng=75.7873,
        city="Jaipur",
        q="fort",
        focus=None,
        radius=15_000,
        limit=24,
    ))

    assert len(results) == 1
    assert results[0].name == "Amber Fort"
    assert results[0].country == "India"


def test_saved_place_can_be_added_to_day_and_removed_without_deleting_visit():
    itinerary = _itinerary()
    place = _place()

    saved, saved_changed = save_place(itinerary, place)
    added, added_changed = add_place_to_day(saved, place_id=place.id, day_number=1)

    assert saved_changed is True
    assert added_changed is True
    assert added.places[0].name == "Amber Fort"
    assert added.day_plans[0].activities[0].poi.name == "Amber Fort"
    assert added.day_plans[0].activities[0].start_time == "09:00"
    assert added.day_plans[0].activities[0].end_time == "12:00"
    assert added.day_plans[0].day_spent == 600
    assert added.budget.activities == 600
    assert added.budget.total_estimated == 2_600
    assert added.budget.remaining == 1_400
    assert added.items[0].place_id == place.id

    removed, removed_changed = remove_saved_place(added, place.id)
    assert removed_changed is True
    assert removed.places == []
    assert removed.day_plans[0].activities[0].poi.name == "Amber Fort"


def test_save_place_http_action_persists_and_records_revision(monkeypatch):
    itinerary = _itinerary()
    persisted: list[Itinerary] = []

    async def fake_get_trip(_trip_id):
        return itinerary

    async def fake_update_trip(updated):
        persisted.append(updated)

    async def fake_current_version(_trip_id):
        return 3

    async def fake_analytics(_event):
        return None

    monkeypatch.setattr(trips_api, "get_trip", fake_get_trip)
    monkeypatch.setattr(trips_api, "update_trip", fake_update_trip)
    monkeypatch.setattr(trips_api, "_current_version", fake_current_version)
    monkeypatch.setattr(trips_api, "_record_analytics", fake_analytics)

    result = asyncio.run(trips_api.save_trip_place(
        "phase4-trip",
        trips_api.SavePlaceRequest(place=_place()),
        Response(),
        if_match=None,
    ))

    assert result.places[0].id == "place-amber-fort"
    assert persisted and persisted[0].places[0].name == "Amber Fort"
