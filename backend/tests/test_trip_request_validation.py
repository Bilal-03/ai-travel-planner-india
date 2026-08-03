"""Input validation for trip requests must be enforced independently of the UI."""

from datetime import date, timedelta

import pytest

from app.models.trip import TripRequest, TravelVibe


def _payload(**overrides):
    start = date.today() + timedelta(days=1)
    payload = {
        "origin": "Delhi",
        "destination": "Jaipur",
        "start_date": start,
        "end_date": start + timedelta(days=2),
        "budget": 10_000,
        "vibes": [TravelVibe.CULTURE],
        "adults": 2,
        "children": 0,
    }
    payload.update(overrides)
    return payload


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"destination": " delhi "}, "Origin and destination"),
        ({"start_date": date.today() - timedelta(days=1)}, "past"),
        ({"end_date": date.today()}, "before departure"),
        ({"end_date": date.today() + timedelta(days=15)}, "14 days"),
        ({"budget": 2_999}, "too low"),
        ({"senior_citizens": 3}, "cannot exceed"),
    ],
)
def test_invalid_trip_constraints_are_rejected(overrides, message):
    with pytest.raises(ValueError, match=message):
        TripRequest(**_payload(**overrides))


def test_day_trip_and_group_budget_at_the_threshold_are_valid():
    start = date.today() + timedelta(days=1)
    request = TripRequest(**_payload(end_date=start, budget=3_000))

    assert request.end_date == request.start_date
