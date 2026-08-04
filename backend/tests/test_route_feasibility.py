"""Regression tests for complete POI-to-POI feasibility checking."""

import asyncio
from datetime import date, timedelta

from app.models.trip import GeoPoint, RouteSegment, TripRequest
from app.services import gemini_planner, routing


def test_feasibility_routes_every_consecutive_stop(monkeypatch):
    calls: list[tuple[GeoPoint, GeoPoint]] = []

    async def fake_segment(origin: GeoPoint, destination: GeoPoint) -> RouteSegment:
        calls.append((origin, destination))
        return RouteSegment(
            from_point=origin,
            to_point=destination,
            distance_km=2,
            duration_minutes=20,
        )

    monkeypatch.setattr(routing, "get_route_segment", fake_segment)
    stops = [GeoPoint(lat=28.0, lng=77.0 + index * 0.01) for index in range(4)]
    feasible, total_hours, segments = asyncio.run(
        routing.validate_day_feasibility(stops, [60, 60, 60, 60])
    )

    assert feasible
    assert total_hours == 5.0
    assert len(calls) == len(stops) - 1
    assert len(segments) == len(stops) - 1
    assert calls == list(zip(stops, stops[1:]))


def test_plan_validation_rejects_overlap_opening_hour_and_summary_mismatch(monkeypatch):
    start = date.today() + timedelta(days=5)
    request = TripRequest(
        origin="Delhi",
        destination="Jaipur",
        start_date=start,
        end_date=start,
        budget=10_000,
        members=2,
    )
    poi_a = {
        "name": "City Museum",
        "category": "museum",
        "coordinates": {"lat": 26.9, "lng": 75.8},
        "estimated_visit_minutes": 90,
        "opening_hours": "10:00-17:00",
    }
    poi_b = {
        "name": "Amber Fort",
        "category": "fort",
        "coordinates": {"lat": 27.0, "lng": 75.9},
        "estimated_visit_minutes": 60,
        "opening_hours": "09:00-18:00",
    }

    async def routes(stops, _durations):
        return True, 3.0, [
            RouteSegment(from_point=stops[0], to_point=stops[1], distance_km=8, duration_minutes=30)
        ]

    monkeypatch.setattr(gemini_planner, "validate_day_feasibility", routes)
    plan = {
        "day_plans": [{
            "day_number": 1,
            "notes": "Last-minute shopping before departure",
            "meals": [{"name": "Suggested meal type: thali"}, {"name": "Suggested meal type: kachori"}],
            "activities": [
                {"name": "City Museum", "start_time": "09:30", "end_time": "10:30"},
                {"name": "Amber Fort", "start_time": "10:20", "end_time": "11:20"},
            ],
        }]
    }

    issues, segments, local_transport = asyncio.run(
        gemini_planner._validate_plan(plan, request, [poi_a, poi_b])
    )

    assert any("summary describes" in issue for issue in issues)
    assert any("overlapping" in issue for issue in issues)
    assert any("outside its listed opening hours" in issue for issue in issues)
    assert any("insufficient travel time" in issue for issue in issues)
    assert segments[0].day_number == 1
    assert local_transport[1][0] == 30
