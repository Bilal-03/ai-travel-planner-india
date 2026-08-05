"""Phase 1 normalized workspace contract coverage."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.models.trip import (
    BudgetBreakdown,
    CityInfo,
    DataProvenance,
    DataStatus,
    GeoPoint,
    Itinerary,
    ItineraryItem,
    ItineraryItemType,
    Place,
    ResearchEvent,
    ResearchEventStatus,
    ResearchEventType,
    SourceKind,
    TransportMode,
    TripIntent,
    TripPreferences,
    TripRequest,
    TravelPace,
)


def _request() -> TripRequest:
    start = date.today() + timedelta(days=30)
    return TripRequest(
        origin="Delhi",
        destination="Udaipur",
        start_date=start,
        end_date=start + timedelta(days=2),
        budget=40_000,
        members=2,
        preferences=TripPreferences(
            experiences=["lakes", "heritage"],
            pace=TravelPace.RELAXED,
            transport_preferences=[TransportMode.TRAIN],
            dietary_preferences=["vegetarian"],
        ),
    )


def test_preferences_are_preserved_when_request_becomes_intent():
    request = _request()
    intent = TripIntent.from_request(request)

    assert intent.preferences.pace == TravelPace.RELAXED
    assert intent.preferences.experiences == ["lakes", "heritage"]
    assert intent.preferences.transport_preferences == [TransportMode.TRAIN]


def test_normalized_place_and_editable_item_keep_source_references():
    retrieved_at = datetime.now(timezone.utc)
    source = DataProvenance(
        provider="official-tourism",
        status=DataStatus.RECENTLY_VERIFIED,
        retrieved_at=retrieved_at,
        source_reference="https://example.test/udaipur",
        disclaimer="Verify local conditions before departure.",
    )
    place = Place(
        id="place-city-palace",
        name="City Palace",
        category="heritage",
        coordinates=GeoPoint(lat=24.5764, lng=73.6835),
        city="Udaipur",
        state="Rajasthan",
        provider_ids={"osm": "way/123"},
        provenance=source,
    )
    item = ItineraryItem(
        item_type=ItineraryItemType.PLACE_VISIT,
        title=place.name,
        day_number=1,
        position=0,
        place_id=place.id,
        coordinates=place.coordinates,
        duration_minutes=90,
        source_ids=["source-1"],
        provenance=source,
        is_locked=True,
    )

    assert item.place_id == place.id
    assert item.is_locked
    assert item.provenance.effective_status() == DataStatus.RECENTLY_VERIFIED


def test_research_events_are_bounded_and_typed():
    event = ResearchEvent(
        event_type=ResearchEventType.FOUND_PLACES,
        status=ResearchEventStatus.COMPLETE,
        message="Found 4 heritage places near Udaipur.",
        query="Udaipur heritage places",
        result_count=4,
        source_ids=["source-1"],
    )

    assert event.event_type.value == "found_places"
    assert event.status.value == "complete"
    assert event.result_count == 4

    with pytest.raises(ValidationError):
        ItineraryItem(item_type="not-a-plan-item", title="Invalid")


def test_existing_itinerary_payloads_gain_empty_workspace_collections():
    future = date.today() + timedelta(days=14)
    itinerary = Itinerary(
        origin=CityInfo(name="Delhi", coordinates=GeoPoint(lat=28.6139, lng=77.2090)),
        destination=CityInfo(name="Udaipur", coordinates=GeoPoint(lat=24.5854, lng=73.7125)),
        start_date=future,
        end_date=future + timedelta(days=1),
        total_days=2,
        budget=BudgetBreakdown(total_estimated=10_000, remaining=30_000),
    )

    assert itinerary.places == []
    assert itinerary.items == []
    assert itinerary.sources == []
    assert itinerary.research_events == []


def test_phase1_migration_has_normalized_projection_tables():
    migration = (Path(__file__).parents[1] / "migrations" / "009_phase1_workspace_foundation.sql").read_text()

    for table in (
        "places",
        "place_provider_links",
        "trip_intents",
        "trip_sources",
        "trip_research_events",
        "trip_itinerary_items",
    ):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in migration

    assert "'place_visit', 'stay', 'flight', 'train'" in migration
    assert "status IN ('pending', 'complete', 'warning', 'error')" in migration
    assert "REFERENCES trips(id) ON DELETE CASCADE" in migration
