"""Result-page plan option selection stays server-authoritative."""

from datetime import date, timedelta

from app.models.trip import BudgetBreakdown, CityInfo, DayPlan, GeoPoint, Itinerary, PlanOption
from app.services.gemini_planner import select_plan_for_itinerary


def _itinerary() -> Itinerary:
    start = date.today() + timedelta(days=10)
    city = CityInfo(name="Delhi", coordinates=GeoPoint(lat=28.6, lng=77.2))
    destination = CityInfo(name="Jaipur", coordinates=GeoPoint(lat=26.9, lng=75.8))
    focused_day = DayPlan(day_number=1, date=start, notes="Focused")
    full_day = DayPlan(day_number=1, date=start, notes="Full")
    focused_budget = BudgetBreakdown(total_estimated=5_000, remaining=5_000)
    full_budget = BudgetBreakdown(total_estimated=8_000, remaining=2_000)
    return Itinerary(
        origin=city,
        destination=destination,
        start_date=start,
        end_date=start,
        total_days=1,
        members=2,
        day_plans=[focused_day],
        budget=focused_budget,
        plan_options=[
            PlanOption(id="plan-1", title="Essential highlights", description="Focused", day_plans=[focused_day], budget=focused_budget),
            PlanOption(id="plan-3", title="Full destination", description="Full", day_plans=[full_day], budget=full_budget),
        ],
    )


def test_select_plan_projects_the_selected_option():
    itinerary = _itinerary()
    updated = select_plan_for_itinerary(itinerary, "plan-3")

    assert updated.selected_plan_id == "plan-3"
    assert updated.day_plans[0].notes == "Full"
    assert updated.budget.total_estimated == 8_000
