"""Phase 3 deterministic scheduling and scoped-refinement coverage."""

from __future__ import annotations

from datetime import date, timedelta

from app.models.trip import TripIntent, TripPace, TripRequest, TravelVibe
from app.services.constraint_engine import (
    ConstraintEngine,
    ConstraintSeverity,
    RefinementAction,
    apply_scoped_refinement,
    parse_refinement_instruction,
)


def _intent(**overrides) -> TripIntent:
    start = date.today() + timedelta(days=30)
    payload = {
        "origin": "Delhi",
        "destinations": ["Jaipur"],
        "start_date": start,
        "end_date": start + timedelta(days=1),
        "travellers": 2,
        "budget": 30_000,
        "travel_style": [TravelVibe.CULTURE],
        "interests": [TravelVibe.CULTURE],
        "pace": TripPace.BALANCED,
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
        adults=2,
        children=1,
        senior_citizens=1,
        vibes=[TravelVibe.CULTURE],
        mandatory_places=["Amber Fort"],
        free_text_notes="Prefer step-free stays",
    )

    intent = TripIntent.from_request(request)

    assert intent.destinations == ["Jaipur"]
    assert intent.travellers == 3
    assert intent.senior_travellers == 1
    assert intent.mandatory_places == ["Amber Fort"]
    assert intent.free_text_notes == "Prefer step-free stays"


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

    plan = ConstraintEngine({("City Museum", "Riverside Park"): 30}).optimize(
        intent,
        candidates,
        weather=weather,
    )

    museum = next(stop for stop in plan.activities if stop.poi_name == "City Museum")
    assert museum.day_number == 1
    assert museum.start_time == "10:00"
    assert museum.end_time == "11:00"
    assert all(
        stop.weather_suitable
        for day in plan.days
        if day.day_number == 1
        for stop in day.activities
    )
    assert plan.feasible


def test_engine_handles_mandatory_excluded_accessibility_and_budget_constraints():
    intent = _intent(
        budget=3_000,
        mandatory_places=["Amber Fort"],
        excluded_places=["Riverside"],
        accessibility_requirements="wheelchair access",
    )
    candidates = [
        _poi("Amber Fort", "fort", 26.92, cost=2_000),
        _poi("Riverside Park", "park", 26.91),
        _poi("City Museum", "museum", 26.90, osm_tags={"wheelchair": "yes"}),
    ]

    plan = ConstraintEngine().optimize(intent, candidates)

    assert all(stop.poi_name != "Riverside Park" for stop in plan.activities)
    assert any(issue.code == "mandatory_place_accessibility_unknown" for issue in plan.issues)
    assert any(issue.code == "budget_exceeded" for issue in plan.issues)
    assert not plan.feasible


def test_refinement_parser_and_scoped_edit_preserve_unrelated_days():
    instruction = parse_refinement_instruction("Make day two less crowded")
    assert instruction.action == RefinementAction.REDUCE_LOAD
    assert instruction.day_number == 2

    plan = {
        "day_plans": [
            {
                "day_number": 1,
                "notes": "Keep this exactly",
                "activities": [{"name": "Museum", "estimated_cost": 100}],
                "backup_activities": [],
            },
            {
                "day_number": 2,
                "notes": "Busy day",
                "activities": [
                    {"name": "Fort", "estimated_cost": 100},
                    {"name": "Market", "estimated_cost": 500},
                ],
                "backup_activities": [],
            },
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


def test_engine_reports_warning_for_unavoidable_outdoor_weather():
    intent = _intent()
    weather = [
        {"date": intent.start_date.isoformat(), "severity": "indoor"},
        {"date": (intent.start_date + timedelta(days=1)).isoformat(), "severity": "indoor"},
    ]
    plan = ConstraintEngine().optimize(
        intent,
        [_poi("Open Air Viewpoint", "viewpoint", 26.9)],
        weather=weather,
    )

    assert any(
        issue.code == "weather_unsuitable" and issue.severity == ConstraintSeverity.WARNING
        for issue in plan.issues
    )
