"""Phase 0 baseline coverage for the existing trip-generation orchestration.

The test deliberately replaces external providers and Gemini with deterministic
fixtures. It exercises the current planner's real canonicalization, scheduling,
validation, budget, and response-model path without changing application code
or depending on live APIs.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from app.models.trip import (
    CityInfo,
    GeoPoint,
    RouteSegment,
    TransportMode,
    TransportOption,
    TripRequest,
)
from app.services import gemini_planner
from app.services.india_cities import search_local_cities

FIXTURE_DIR = Path(__file__).parent / "fixtures"
REQUEST_FIXTURES = json.loads((FIXTURE_DIR / "baseline_trip_requests.json").read_text())
RESPONSE_FIXTURES = json.loads(
    (FIXTURE_DIR / "baseline_itinerary_responses.json").read_text()
)
REQUESTS_BY_ID = {item["case_id"]: item for item in REQUEST_FIXTURES["trips"]}
RESPONSES_BY_ID = {
    item["case_id"]: item["snapshot"] for item in RESPONSE_FIXTURES["response_slices"]
}


def _request_from_fixture(record: dict) -> TripRequest:
    start_date = datetime.now(timezone.utc).date() + timedelta(
        days=record["start_date_offset_days"]
    )
    payload = {
        key: value
        for key, value in record.items()
        if key not in {"case_id", "label", "start_date_offset_days", "duration_days"}
    }
    payload["start_date"] = start_date
    payload["end_date"] = start_date + timedelta(days=record["duration_days"] - 1)
    return TripRequest(**payload)


def _city_info(city_name: str) -> CityInfo:
    result = search_local_cities(city_name, limit=1)[0]
    return CityInfo(
        name=result["name"],
        state=result["state"],
        coordinates=GeoPoint(**result["coordinates"]),
    )


def _transport_options(origin: str, destination: str) -> list[TransportOption]:
    checked_at = datetime(2026, 8, 4, tzinfo=timezone.utc)
    common = {
        "departure_city": origin,
        "arrival_city": destination,
        "is_fallback": True,
        "field_provenance": {
            "fare": "Estimated fixture fare",
            "schedule": "Static fixture schedule reference",
            "availability": "Not available",
        },
        "availability_status": "Not available",
        "last_checked_at": checked_at,
    }
    return [
        TransportOption(
            mode=TransportMode.FLIGHT,
            provider="Fixture flight",
            price=5000,
            duration_minutes=120,
            **common,
        ),
        TransportOption(
            mode=TransportMode.TRAIN,
            provider="Fixture train",
            price=1500,
            duration_minutes=360,
            **common,
        ),
        TransportOption(
            mode=TransportMode.ROAD,
            provider="Fixture road estimate",
            price=3000,
            duration_minutes=480,
            **common,
        ),
    ]


def _approved_pois(destination: CityInfo, count: int = 8) -> list[dict]:
    return [
        {
            "name": f"{destination.name} baseline place {index}",
            "category": "attraction",
            "coordinates": {
                "lat": destination.coordinates.lat + index * 0.001,
                "lng": destination.coordinates.lng + index * 0.001,
            },
            "estimated_visit_minutes": 60,
            "estimated_cost": 100,
            "opening_hours": None,
            "osm_tags": {"source": "phase_0_fixture"},
        }
        for index in range(1, count + 1)
    ]


def _fixture_plan(request: TripRequest, pois: list[dict]) -> dict:
    total_days = (request.end_date - request.start_date).days + 1
    day_plans = []
    for day_number in range(1, total_days + 1):
        poi = pois[day_number - 1]
        day_plans.append(
            {
                "day_number": day_number,
                "date": (
                    request.start_date + timedelta(days=day_number - 1)
                ).isoformat(),
                "notes": f"Day {day_number}: {poi['name']}",
                "activities": [
                    {
                        "name": poi["name"],
                        "category": poi["category"],
                        "lat": poi["coordinates"]["lat"],
                        "lng": poi["coordinates"]["lng"],
                        "start_time": "09:00",
                        "end_time": "10:00",
                        "estimated_cost": poi["estimated_cost"],
                        "notes": "Deterministic Phase 0 fixture activity",
                        "is_backup": False,
                    }
                ],
                "meals": [
                    {
                        "name": "Suggested meal type: fixture breakfast",
                        "meal_type": "breakfast",
                        "estimated_cost": 150,
                    },
                    {
                        "name": "Suggested meal type: fixture lunch",
                        "meal_type": "lunch",
                        "estimated_cost": 300,
                    },
                    {
                        "name": "Suggested meal type: fixture dinner",
                        "meal_type": "dinner",
                        "estimated_cost": 400,
                    },
                ],
                "backup_activities": [],
            }
        )
    return {"day_plans": day_plans, "tips": ["Phase 0 deterministic fixture"]}


async def _generate_with_fixtures(
    monkeypatch: pytest.MonkeyPatch, request: TripRequest
):
    origin = _city_info(request.origin)
    destination = _city_info(request.destination)
    pois = _approved_pois(destination)
    transport = _transport_options(origin.name, destination.name)

    async def fake_geocode(city: str):
        return _city_info(city)

    async def fake_transport(*_args, **_kwargs):
        return transport

    async def fake_pois(*_args, **_kwargs):
        return pois

    async def fake_weather(*_args, **_kwargs):
        return []

    async def fake_photos(*_args, **_kwargs):
        return []

    async def fake_gemini(_prompt: str, _system: str = gemini_planner.SYSTEM_PROMPT):
        return _fixture_plan(request, pois)

    async def fake_feasibility(
        stops: list[GeoPoint],
        durations: list[int],
        max_day_hours: float = 12.0,
    ):
        segments = [
            RouteSegment(
                from_point=stops[index],
                to_point=stops[index + 1],
                distance_km=2,
                duration_minutes=15,
            )
            for index in range(len(stops) - 1)
        ]
        total_hours = (
            sum(durations) + sum(segment.duration_minutes for segment in segments)
        ) / 60
        return total_hours <= max_day_hours, round(total_hours, 1), segments

    monkeypatch.setattr(gemini_planner, "geocode_to_city_info", fake_geocode)
    monkeypatch.setattr(gemini_planner, "search_transport", fake_transport)
    monkeypatch.setattr(gemini_planner, "discover_pois", fake_pois)
    monkeypatch.setattr(gemini_planner, "get_forecast", fake_weather)
    monkeypatch.setattr(gemini_planner, "get_destination_photos", fake_photos)
    monkeypatch.setattr(gemini_planner, "_call_gemini", fake_gemini)
    monkeypatch.setattr(gemini_planner, "validate_day_feasibility", fake_feasibility)

    return await gemini_planner.generate_itinerary(request)


@pytest.mark.parametrize("case_id", sorted(REQUESTS_BY_ID))
def test_baseline_request_fixtures_are_valid(case_id: str):
    request = _request_from_fixture(REQUESTS_BY_ID[case_id])
    expected_days = REQUESTS_BY_ID[case_id]["duration_days"]

    assert request.origin != request.destination
    assert request.end_date == request.start_date + timedelta(days=expected_days - 1)
    assert (request.end_date - request.start_date).days + 1 <= 14
    assert request.budget >= (request.adults + request.children) * 1_500


@pytest.mark.parametrize("case_id", sorted(REQUESTS_BY_ID))
def test_baseline_generation_matches_response_fixture(
    monkeypatch: pytest.MonkeyPatch, case_id: str
):
    request = _request_from_fixture(REQUESTS_BY_ID[case_id])
    itinerary = asyncio.run(_generate_with_fixtures(monkeypatch, request))
    snapshot = RESPONSES_BY_ID[case_id]

    actual = {
        "origin": itinerary.origin.name,
        "destination": itinerary.destination.name,
        "total_days": itinerary.total_days,
        "day_numbers": [day.day_number for day in itinerary.day_plans],
        "selected_transport_mode": itinerary.selected_transport.mode.value
        if itinerary.selected_transport
        else None,
        "transport_option_modes": [
            option.mode.value for option in itinerary.transport_options
        ],
        "activity_counts": [len(day.activities) for day in itinerary.day_plans],
        "meal_counts": [len(day.meals) for day in itinerary.day_plans],
    }

    assert actual == snapshot
    assert all(option.is_fallback for option in itinerary.transport_options)
    assert all(option.field_provenance for option in itinerary.transport_options)
    assert itinerary.budget.total_estimated > 0
    assert (
        itinerary.budget.remaining == request.budget - itinerary.budget.total_estimated
    )
    assert all(
        any(
            activity.poi.name.endswith(f"baseline place {index}")
            for index in range(1, 9)
        )
        for day in itinerary.day_plans
        for activity in day.activities
    )
