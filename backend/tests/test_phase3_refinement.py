"""Server-side itinerary refinement stays local and revalidates the result."""

from __future__ import annotations

import asyncio
from datetime import date, timedelta

from app.models.trip import (
    Activity,
    BudgetBreakdown,
    CityInfo,
    DayPlan,
    GeoPoint,
    Itinerary,
    MealRecommendation,
    POI,
    RouteSegment,
    TravelVibe,
)
from app.services import gemini_planner


def _itinerary() -> Itinerary:
    start = date.today() + timedelta(days=30)
    origin = CityInfo(name="Delhi", state="Delhi", coordinates=GeoPoint(lat=28.6, lng=77.2))
    destination = CityInfo(name="Jaipur", state="Rajasthan", coordinates=GeoPoint(lat=26.9, lng=75.8))

    def activity(name: str, lat: float, start_time: str) -> Activity:
        poi = POI(
            name=name,
            category="attraction",
            coordinates=GeoPoint(lat=lat, lng=75.8),
            estimated_visit_minutes=60,
            estimated_cost=100,
        )
        start_minutes = int(start_time[:2]) * 60 + int(start_time[3:])
        end_time = f"{(start_minutes + 60) // 60:02d}:{(start_minutes + 60) % 60:02d}"
        return Activity(
            poi=poi,
            start_time=start_time,
            end_time=end_time,
            estimated_cost=100,
        )

    meals = [
        MealRecommendation(name="Suggested meal type: breakfast", meal_type="breakfast", estimated_cost=150),
        MealRecommendation(name="Suggested meal type: lunch", meal_type="lunch", estimated_cost=300),
    ]
    return Itinerary(
        id="refine-trip",
        origin=origin,
        destination=destination,
        start_date=start,
        end_date=start + timedelta(days=1),
        total_days=2,
        vibes=[TravelVibe.CULTURE],
        day_plans=[
            DayPlan(day_number=1, date=start, activities=[activity("City Museum", 26.90, "09:00")], meals=meals),
            DayPlan(
                day_number=2,
                date=start + timedelta(days=1),
                activities=[activity("Amber Fort", 26.91, "09:00"), activity("City Palace", 26.92, "11:00")],
                meals=meals,
            ),
        ],
        budget=BudgetBreakdown(total_estimated=10_000, remaining=20_000),
    )


def test_less_crowded_refinement_preserves_unrelated_days(monkeypatch):
    async def routes(stops, durations, max_day_hours=12.0):
        segments = [
            RouteSegment(
                from_point=stops[index],
                to_point=stops[index + 1],
                distance_km=2,
                duration_minutes=20,
            )
            for index in range(len(stops) - 1)
        ]
        total_hours = (sum(durations) + sum(segment.duration_minutes for segment in segments)) / 60
        return total_hours <= max_day_hours, total_hours, segments

    monkeypatch.setattr(gemini_planner, "validate_day_feasibility", routes)
    original = _itinerary()
    original_day_one = {
        "activities": [
            (activity.poi.name, activity.start_time, activity.end_time, activity.estimated_cost)
            for activity in original.day_plans[0].activities
        ],
        "meals": [
            (meal.name, meal.meal_type, meal.estimated_cost)
            for meal in original.day_plans[0].meals
        ],
        "notes": original.day_plans[0].notes,
    }

    refined = asyncio.run(gemini_planner.refine_itinerary(original, "Make day two less crowded"))

    assert refined.id == original.id
    assert [
        (activity.poi.name, activity.start_time, activity.end_time, activity.estimated_cost)
        for activity in refined.day_plans[0].activities
    ] == original_day_one["activities"]
    assert [
        (meal.name, meal.meal_type, meal.estimated_cost)
        for meal in refined.day_plans[0].meals
    ] == original_day_one["meals"]
    assert refined.day_plans[0].notes == original_day_one["notes"]
    assert [activity.poi.name for activity in refined.day_plans[1].activities] == ["Amber Fort"]
    assert refined.day_plans[1].backup_activities[0].poi.name == "City Palace"
    assert any("Deterministic refinement applied" in note for note in refined.generation_notes)
