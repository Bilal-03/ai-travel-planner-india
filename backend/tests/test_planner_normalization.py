"""Regression coverage for malformed and over-optimistic model plans."""

import asyncio
from datetime import date, timedelta

from app.models.trip import GeoPoint, RouteSegment, TripRequest
from app.services import gemini_planner


def _request(days: int = 4) -> TripRequest:
    start = date.today() + timedelta(days=5)
    return TripRequest(
        origin="Delhi",
        destination="Pondicherry",
        start_date=start,
        end_date=start + timedelta(days=days - 1),
        budget=40_000,
        members=2,
    )


def _poi(name: str, lat: float, lng: float, minutes: int = 60) -> dict:
    return {
        "name": name,
        "category": "attraction",
        "coordinates": {"lat": lat, "lng": lng},
        "estimated_visit_minutes": minutes,
        "estimated_cost": 100,
    }


def _meal(name: str = "Suggested meal type: local meal") -> dict:
    return {"name": name, "meal_type": "lunch", "estimated_cost": 300}


def test_canonicalize_maps_coordinate_alias_and_fills_empty_interior_day():
    request = _request()
    approved = [
        _poi("Serenity Beach", 11.9933, 79.8448, 120),
        _poi("Matrimandir", 12.0065, 79.8095, 60),
        _poi("French War Memorial", 11.9315, 79.8357, 60),
    ]
    plan = {
        "day_plans": [
            {
                "day_number": "1",
                "activities": [{
                    "name": "Serenity Beach lookout",
                    "lat": 11.9934,
                    "lng": 79.8447,
                    "start_time": "09:00",
                    "end_time": "11:00",
                }],
                "meals": [_meal()],
            },
            {"day_number": 2, "activities": [], "meals": [_meal()]},
            {"day_number": 3, "activities": [], "meals": [_meal()]},
            {"day_number": 4, "activities": [], "meals": [_meal()]},
        ]
    }

    canonical = gemini_planner._canonicalize_plan(plan, request, approved)

    assert len(canonical["day_plans"]) == 4
    assert canonical["day_plans"][0]["activities"][0]["name"] == "Serenity Beach"
    assert canonical["day_plans"][1]["activities"]
    assert all(len(day["meals"]) >= 2 for day in canonical["day_plans"])


def test_schedule_reflows_activity_after_real_route_time(monkeypatch):
    approved = [
        _poi("Matrimandir", 12.0065, 79.8095, 90),
        _poi("Paradise Beach", 11.8838, 79.8288, 60),
    ]
    plan = {
        "day_plans": [{
            "day_number": 1,
            "activities": [
                {"name": "Matrimandir", "start_time": "09:00", "end_time": "10:30"},
                {"name": "Paradise Beach", "start_time": "10:40", "end_time": "11:40"},
            ],
        }]
    }

    async def fake_feasibility(stops, _durations):
        return True, 4.0, [
            RouteSegment(
                from_point=stops[0],
                to_point=stops[1],
                distance_km=15,
                duration_minutes=50,
            )
        ]

    monkeypatch.setattr(gemini_planner, "validate_day_feasibility", fake_feasibility)
    asyncio.run(gemini_planner._repair_plan_schedule(plan, approved))

    assert plan["day_plans"][0]["activities"][1]["start_time"] == "11:30"


def test_validation_treats_string_last_day_number_as_last_day(monkeypatch):
    request = _request()
    poi = _poi("Matrimandir", 12.0065, 79.8095)
    activities = [{
        "name": poi["name"],
        "lat": poi["coordinates"]["lat"],
        "lng": poi["coordinates"]["lng"],
        "start_time": "09:00",
        "end_time": "10:00",
    }]
    plan = {
        "day_plans": [
            {"day_number": 1, "activities": activities, "meals": [_meal(), _meal()]},
            {"day_number": 2, "activities": activities, "meals": [_meal(), _meal()]},
            {"day_number": 3, "activities": activities, "meals": [_meal(), _meal()]},
            {"day_number": "4", "activities": [], "meals": [_meal(), _meal()]},
        ]
    }

    async def fake_feasibility(_stops, _durations):
        return True, 1.0, []

    monkeypatch.setattr(gemini_planner, "validate_day_feasibility", fake_feasibility)
    issues, _, _ = asyncio.run(gemini_planner._validate_plan(plan, request, [poi]))

    assert not any("Day 4 has no activities planned" in issue for issue in issues)
