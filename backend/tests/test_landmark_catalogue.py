"""Regression checks for the reviewed high-demand landmark rollout."""

from datetime import date

from app.data.landmark_catalogue import LANDMARK_CATALOGUE
from app.models.trip import CityInfo, GeoPoint, TripRequest, TravelVibe
from app.services.gemini_planner import _build_planning_prompt
from app.services.poi_discovery import _priority_landmarks


EXPANDED_DESTINATIONS = (
    "goa",
    "bengaluru",
    "chennai",
    "kolkata",
    "hyderabad",
    "varanasi",
    "udaipur",
    "rishikesh",
    "manali",
    "kochi",
    "srinagar",
    "mumbai",
    "delhi",
    "jaipur",
    "agra",
    "amritsar",
    "lucknow",
    "mysuru",
    "jodhpur",
    "shimla",
    "ooty",
    "munnar",
    "pondicherry",
    "madurai",
    "tirupati",
    "darjeeling",
    "ayodhya",
    "jaisalmer",
    "haridwar",
    "rameswaram",
    "kanyakumari",
    "pushkar",
    "nainital",
    "dharamshala",
    "khajuraho",
)


def test_expanded_destinations_have_twelve_reviewed_ranked_records():
    for destination in EXPANDED_DESTINATIONS:
        records = LANDMARK_CATALOGUE[destination]

        assert len(records) >= 12
        assert [record["priority_rank"] for record in records] == list(
            range(1, len(records) + 1)
        )
        assert all(record["source_url"].startswith("https://") for record in records)
        assert all(record["reviewed_at"] for record in records)
        assert all(record["review_due_at"] for record in records)


def test_city_aliases_return_the_same_reviewed_catalogue():
    assert _priority_landmarks("Bangalore") == _priority_landmarks("Bengaluru")
    assert _priority_landmarks("Cochin") == _priority_landmarks("Kochi")
    assert _priority_landmarks("Benaras") == _priority_landmarks("Varanasi")


def test_prompt_keeps_every_reviewed_landmark_in_context():
    destination = CityInfo(name="Kochi", coordinates=GeoPoint(lat=9.9312, lng=76.2673))
    local_options = [
        {
            "name": f"Kochi local option {index}",
            "category": "attraction",
            "coordinates": {"lat": 9.9, "lng": 76.2},
            "estimated_visit_minutes": 60,
            "estimated_cost": 0,
            "osm_tags": {"tourism": "attraction"},
        }
        for index in range(30)
    ]
    prompt = _build_planning_prompt(
        request=TripRequest(
            origin="Bengaluru",
            destination="Kochi",
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 5),
            budget=30_000,
            vibes=[TravelVibe.CULTURE],
        ),
        origin=CityInfo(name="Bengaluru", coordinates=GeoPoint(lat=12.9716, lng=77.5946)),
        destination=destination,
        pois=_priority_landmarks(destination.name) + local_options,
        transport_options=[],
        weather=[],
        distance_km=360,
        festivals=[],
    )

    for record in LANDMARK_CATALOGUE["kochi"]:
        assert record["name"] in prompt
    assert local_options[-1]["name"] in prompt
