"""Phase 6 trip-level commitment persistence and budget contracts."""

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
    PlanOption,
    RouteSegment,
)
from app.services import gemini_planner
from app.services.stays import add_stay_to_itinerary, search_stays
from app.services.trip_commitments import sync_trip_commitment_budgets


def _activity(name: str, latitude: float, start_time: str) -> Activity:
    start_minutes = int(start_time[:2]) * 60 + int(start_time[3:])
    end_minutes = start_minutes + 60
    return Activity(
        poi=POI(
            name=name,
            category="attraction",
            coordinates=GeoPoint(lat=latitude, lng=75.8),
            estimated_visit_minutes=60,
            estimated_cost=100,
        ),
        start_time=start_time,
        end_time=f"{end_minutes // 60:02d}:{end_minutes % 60:02d}",
        estimated_cost=100,
    )


def _itinerary() -> Itinerary:
    start = date.today() + timedelta(days=40)
    origin = CityInfo(name="Delhi", state="Delhi", coordinates=GeoPoint(lat=28.6, lng=77.2))
    destination = CityInfo(name="Jaipur", state="Rajasthan", coordinates=GeoPoint(lat=26.9, lng=75.8))
    meals = [
        MealRecommendation(name="Suggested breakfast", meal_type="breakfast", estimated_cost=150),
        MealRecommendation(name="Suggested lunch", meal_type="lunch", estimated_cost=300),
    ]
    return Itinerary(
        id="phase6-trip",
        origin=origin,
        destination=destination,
        start_date=start,
        end_date=start + timedelta(days=1),
        total_days=2,
        members=2,
        day_plans=[
            DayPlan(
                day_number=1,
                date=start,
                activities=[_activity("City Museum", 26.90, "09:00")],
                meals=meals,
            ),
            DayPlan(
                day_number=2,
                date=start + timedelta(days=1),
                activities=[_activity("Amber Fort", 26.91, "09:00"), _activity("City Palace", 26.92, "11:00")],
                meals=meals,
            ),
        ],
        budget=BudgetBreakdown(total_estimated=8_000, remaining=22_000),
    )


def test_trip_commitment_budget_line_updates_active_and_alternative_plans():
    itinerary = _itinerary()
    itinerary.plan_options = [
        PlanOption(
            id="plan-1",
            title="Essential",
            description="Focused route",
            day_plans=itinerary.day_plans,
            budget=BudgetBreakdown(total_estimated=8_000, remaining=22_000),
        ),
        PlanOption(
            id="plan-2",
            title="Slow",
            description="Slower route",
            day_plans=itinerary.day_plans,
            budget=BudgetBreakdown(total_estimated=7_000, remaining=23_000),
        ),
    ]
    stay = search_stays(
        city="Jaipur",
        check_in=itinerary.start_date,
        check_out=itinerary.end_date,
        members=itinerary.members,
    )[0]
    itinerary, changed = add_stay_to_itinerary(itinerary, stay)

    assert changed is True
    assert itinerary.budget.stay == stay.total_price
    assert all(option.budget.stay == stay.total_price for option in itinerary.plan_options)
    assert all(option.budget.total_estimated >= stay.total_price for option in itinerary.plan_options)

    itinerary.plan_options[1].budget.stay = 0
    itinerary.plan_options[1].budget.total_estimated -= stay.total_price
    itinerary.plan_options[1].budget.remaining += stay.total_price
    sync_trip_commitment_budgets(itinerary)
    assert itinerary.plan_options[1].budget.stay == stay.total_price


def test_refinement_preserves_saved_stay_item_and_budget(monkeypatch):
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
    itinerary = _itinerary()
    stay = search_stays(
        city="Jaipur",
        check_in=itinerary.start_date,
        check_out=itinerary.end_date,
        members=itinerary.members,
    )[0]
    itinerary, _ = add_stay_to_itinerary(itinerary, stay)
    original_total = itinerary.budget.total_estimated

    refined = asyncio.run(gemini_planner.refine_itinerary(itinerary, "Make day two less crowded"))

    assert refined.items[0].metadata["stay_id"] == stay.id
    assert refined.budget.stay == stay.total_price
    assert refined.budget.total_estimated >= original_total
    assert refined.budget.remaining <= itinerary.budget.remaining
