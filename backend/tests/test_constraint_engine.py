"""Deterministic scheduling and scoped-refinement coverage."""

from __future__ import annotations

from datetime import date, timedelta

from app.models.trip import TripIntent, TripRequest
from app.services.constraint_engine import (
    ConstraintEngine,
    ConstraintSeverity,
    PLAN_PROFILES,
    RefinementAction,
    apply_scoped_refinement,
    parse_refinement_instruction,
)


def _intent(**overrides) -> TripIntent:
    start = date.today() + timedelta(days=30)
    payload = {
        "origin": "Delhi",
        "destination": "Jaipur",
        "start_date": start,
        "end_date": start + timedelta(days=1),
        "members": 2,
        "budget": 30_000,
        "planning_notes": "heritage places",
    }
    payload.update(overrides)
    return TripIntent(**payload)


def _poi(name: str, category: str, lat: float, cost: int = 100, **extra) -> dict:
    return {
        "id": name.casefold().replace(" ", "-"),
        "name": name,
        "category": category,
        "coordinates": {"lat": lat, "lng": 75.8},
        "estimated_visit_minutes": 60,
        "estimated_cost": cost,
        **extra,
    }


def test_trip_request_maps_to_structured_intent():
    request = TripRequest(
        origin="Delhi",
        destination="Jaipur",
        start_date=date.today() + timedelta(days=10),
        end_date=date.today() + timedelta(days=11),
        budget=20_000,
        members=3,
        planning_notes="Prefer step-free places and frequent breaks",
    )

    intent = TripIntent.from_request(request)

    assert intent.destination == "Jaipur"
    assert intent.members == 3
    assert "frequent breaks" in intent.planning_notes


def test_engine_prefers_indoor_places_in_bad_weather_and_respects_opening_hours():
    intent = _intent()
    weather = [
        {"date": intent.start_date.isoformat(), "severity": "indoor"},
        {"date": (intent.start_date + timedelta(days=1)).isoformat(), "severity": "great"},
    ]
    candidates = [
        _poi("City Museum", "museum", 26.90, opening_hours="10:00-17:00"),
        _poi("Riverside Park", "park", 26.91),
        _poi("Amber Fort", "fort", 26.92),
    ]

    plan = ConstraintEngine({("City Museum", "Riverside Park"): 30}).optimize(intent, candidates, weather=weather)

    museum = next(stop for stop in plan.activities if stop.poi_name == "City Museum")
    assert museum.day_number == 1
    assert museum.start_time == "10:00"
    assert museum.end_time == "11:00"
    assert all(stop.weather_suitable for day in plan.days if day.day_number == 1 for stop in day.activities)
    assert plan.feasible


def test_plan_profiles_control_activity_density_without_form_preferences():
    intent = _intent()
    candidates = [_poi(f"Place {index}", "attraction", 26.90 + index * 0.001) for index in range(8)]
    focused = ConstraintEngine().optimize(intent, candidates, profile=PLAN_PROFILES[0])
    full = ConstraintEngine().optimize(intent, candidates, profile=PLAN_PROFILES[2])

    assert all(len(day.activities) <= PLAN_PROFILES[0].max_activities for day in focused.days)
    assert sum(len(day.activities) for day in full.days) >= sum(len(day.activities) for day in focused.days)


def test_engine_reports_warning_for_unavoidable_outdoor_weather():
    intent = _intent()
    weather = [
        {"date": intent.start_date.isoformat(), "severity": "indoor"},
        {"date": (intent.start_date + timedelta(days=1)).isoformat(), "severity": "indoor"},
    ]
    plan = ConstraintEngine().optimize(intent, [_poi("Open Air Viewpoint", "viewpoint", 26.9)], weather=weather)

    assert any(issue.code == "weather_unsuitable" and issue.severity == ConstraintSeverity.WARNING for issue in plan.issues)


def test_refinement_parser_and_scoped_edit_preserve_unrelated_days():
    instruction = parse_refinement_instruction("Make day two less crowded")
    assert instruction.action == RefinementAction.REDUCE_LOAD
    assert instruction.day_number == 2

    plan = {
        "day_plans": [
            {"day_number": 1, "notes": "Keep this exactly", "activities": [{"name": "Museum", "estimated_cost": 100}], "backup_activities": []},
            {"day_number": 2, "notes": "Busy day", "activities": [{"name": "Fort", "estimated_cost": 100}, {"name": "Market", "estimated_cost": 500}], "backup_activities": []},
        ],
    }
    original_day_one = plan["day_plans"][0].copy()
    refined, changed_days, changed = apply_scoped_refinement(plan, instruction)

    assert changed
    assert changed_days == {2}
    assert refined["day_plans"][0] == original_day_one
    assert len(refined["day_plans"][1]["activities"]) == 1
    assert refined["day_plans"][1]["backup_activities"][0]["name"] == "Market"
    transport_change = parse_refinement_instruction("Change from flight to train")
    assert transport_change.action == RefinementAction.CHANGE_TRANSPORT
    assert transport_change.transport_mode == "train"
