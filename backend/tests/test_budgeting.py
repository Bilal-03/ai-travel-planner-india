"""Regression coverage for deterministic trip costing and transport selection."""

from datetime import date, timedelta

from app.models.trip import (
    Activity,
    DayPlan,
    GeoPoint,
    MealRecommendation,
    POI,
    TransportMode,
    TransportOption,
    TravelVibe,
    TripRequest,
)
from app.services.gemini_planner import _calculate_budget, _select_transport


def _request() -> TripRequest:
    start = date.today() + timedelta(days=7)
    return TripRequest(
        origin="Delhi",
        destination="Jaipur",
        start_date=start,
        end_date=start + timedelta(days=2),
        budget=20_000,
        vibes=[TravelVibe.CULTURE],
        transport_mode=TransportMode.TRAIN,
    )


def test_budget_is_derived_from_items_and_selected_round_trip_not_llm_categories():
    request = _request()
    day = DayPlan(
        day_number=1,
        date=request.start_date,
        activities=[
            Activity(
                poi=POI(name="Amber Fort", category="fort", coordinates=GeoPoint(lat=1, lng=1)),
                estimated_cost=700,
            )
        ],
        meals=[MealRecommendation(name="Suggested meal type: thali", meal_type="lunch", estimated_cost=325)],
        local_transport_cost=175,
    )
    train = TransportOption(
        mode=TransportMode.TRAIN,
        provider="Test Train",
        price=900,
        duration_minutes=120,
        departure_city="Delhi",
        arrival_city="Jaipur",
    )

    budget = _calculate_budget([day], train, request)

    assert budget.outbound_transport == 1_800
    assert budget.return_transport == 1_800
    assert budget.food == 650
    assert budget.activities == 1_400
    assert budget.local_transport == 675  # includes ₹500 return station transfers
    assert budget.taxes_buffer == 317
    assert budget.total_estimated == 6_642


def test_requested_transport_mode_is_also_the_recommended_option():
    train = TransportOption(mode=TransportMode.TRAIN, provider="Train", price=900, duration_minutes=120, departure_city="A", arrival_city="B")
    flight = TransportOption(mode=TransportMode.FLIGHT, provider="Flight", price=2_797, duration_minutes=70, departure_city="A", arrival_city="B")

    selected = _select_transport([train, flight], TransportMode.FLIGHT, distance_km=250)

    assert selected is flight
    assert flight.is_recommended
    assert not train.is_recommended
