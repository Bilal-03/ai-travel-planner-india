"""Phase 5 transport and stay discovery contracts."""

from __future__ import annotations

import asyncio
from datetime import date, timedelta

from fastapi import Response

from app.api import stays as stays_api
from app.api import trips as trips_api
from app.models.trip import BudgetBreakdown, CityInfo, DayPlan, GeoPoint, Itinerary, StayOption, TransportMode, TransportOption
from app.services.gemini_planner import select_transport_for_itinerary
from app.services.stays import add_stay_to_itinerary, remove_stay_from_itinerary, search_stays


def _itinerary() -> Itinerary:
    start = date.today() + timedelta(days=40)
    return Itinerary(
        id="phase5-trip",
        origin=CityInfo(name="Delhi", state="Delhi", coordinates=GeoPoint(lat=28.6139, lng=77.2090)),
        destination=CityInfo(name="Jaipur", state="Rajasthan", coordinates=GeoPoint(lat=26.9124, lng=75.7873)),
        start_date=start,
        end_date=start + timedelta(days=2),
        total_days=3,
        members=2,
        day_plans=[
            DayPlan(day_number=1, date=start, day_budget=2_000),
            DayPlan(day_number=2, date=start + timedelta(days=1), day_budget=2_000),
            DayPlan(day_number=3, date=start + timedelta(days=2), day_budget=2_000),
        ],
        budget=BudgetBreakdown(total_estimated=2_000, remaining=18_000),
    )


def test_stay_search_returns_stable_area_estimates_with_disclosure():
    start = date.today() + timedelta(days=40)
    first = search_stays(city="Jaipur", check_in=start, check_out=start + timedelta(days=2), members=2, hotel_style="standard")
    second = search_stays(city="Jaipur", check_in=start, check_out=start + timedelta(days=2), members=2, hotel_style="standard")

    assert len(first) == 3
    assert [option.id for option in first] == [option.id for option in second]
    assert all(option.is_fallback for option in first)
    assert all(option.provenance.status.value == "estimated" for option in first)
    assert all(option.nights == 2 and option.total_price == option.nightly_price * 2 for option in first)
    assert all("confirmed" in option.provenance.disclaimer.lower() for option in first)


def test_stay_can_be_added_and_removed_with_budget_reversal():
    itinerary = _itinerary()
    stay = search_stays(
        city="Jaipur",
        check_in=itinerary.start_date,
        check_out=itinerary.end_date,
        members=itinerary.members,
    )[0]

    added, changed = add_stay_to_itinerary(itinerary, stay)
    assert changed is True
    assert added.items[0].item_type.value == "stay"
    assert added.items[0].metadata["stay_id"] == stay.id
    assert added.budget.stay == stay.total_price
    assert added.budget.total_estimated == 2_000 + stay.total_price
    assert added.budget.remaining == 18_000 - stay.total_price

    duplicate, duplicate_changed = add_stay_to_itinerary(added, stay)
    assert duplicate_changed is False
    assert len(duplicate.items) == 1

    removed, removed_changed = remove_stay_from_itinerary(added, stay.id)
    assert removed_changed is True
    assert removed.items == []
    assert removed.budget.stay == 0
    assert removed.budget.total_estimated == 2_000
    assert removed.budget.remaining == 18_000


def test_stay_search_endpoint_returns_date_aware_results():
    start = date.today() + timedelta(days=40)
    result = asyncio.run(stays_api.search_stays_endpoint(
        city="Jaipur",
        check_in=start,
        check_out=start + timedelta(days=1),
        members=2,
        hotel_style="budget",
    ))

    assert isinstance(result[0], StayOption)
    assert result[0].check_in == start
    assert result[0].check_out == start + timedelta(days=1)
    assert result[0].rooms == 1


def test_transport_selection_can_promote_a_fresh_search_result():
    itinerary = _itinerary()
    option = TransportOption(
        mode=TransportMode.TRAIN,
        provider="Indian Railways fare estimate",
        code="12956",
        price=1_200,
        duration_minutes=300,
        departure_city="Delhi",
        arrival_city="Jaipur",
    )

    updated = select_transport_for_itinerary(
        itinerary,
        option.mode,
        option.provider,
        option.code,
        option,
    )

    assert updated.selected_transport is not None
    assert updated.selected_transport.code == "12956"
    assert any(candidate.code == "12956" for candidate in updated.transport_options)


def test_transport_reselection_preserves_a_saved_stay_budget_line():
    itinerary = _itinerary()
    stay = search_stays(
        city="Jaipur",
        check_in=itinerary.start_date,
        check_out=itinerary.end_date,
        members=itinerary.members,
    )[0]
    itinerary, _ = add_stay_to_itinerary(itinerary, stay)
    option = TransportOption(
        mode=TransportMode.TRAIN,
        provider="Indian Railways fare estimate",
        code="12956",
        price=1_200,
        duration_minutes=300,
        departure_city="Delhi",
        arrival_city="Jaipur",
    )

    updated = select_transport_for_itinerary(
        itinerary,
        option.mode,
        option.provider,
        option.code,
        option,
    )

    assert updated.budget.stay == stay.total_price
    assert updated.budget.total_estimated >= stay.total_price


def test_add_stay_http_action_persists_and_records_revision(monkeypatch):
    itinerary = _itinerary()
    stay = search_stays(
        city="Jaipur",
        check_in=itinerary.start_date,
        check_out=itinerary.end_date,
        members=itinerary.members,
    )[0]
    persisted: list[Itinerary] = []

    async def fake_get_trip(_trip_id):
        return itinerary

    async def fake_update_trip(updated):
        persisted.append(updated)

    async def fake_current_version(_trip_id):
        return 4

    async def fake_analytics(_event):
        return None

    monkeypatch.setattr(trips_api, "get_trip", fake_get_trip)
    monkeypatch.setattr(trips_api, "update_trip", fake_update_trip)
    monkeypatch.setattr(trips_api, "_current_version", fake_current_version)
    monkeypatch.setattr(trips_api, "_record_analytics", fake_analytics)

    result = asyncio.run(trips_api.add_trip_stay(
        "phase5-trip",
        trips_api.StaySelectionRequest(stay=stay),
        Response(),
        if_match=None,
    ))

    assert result.items[0].metadata["stay_id"] == stay.id
    assert persisted and persisted[0].budget.stay == stay.total_price
