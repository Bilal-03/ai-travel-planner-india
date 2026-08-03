"""Versioned, source-reviewed destination landmark catalogue."""

from typing import TypedDict


CATALOGUE_VERSION = "2026-08-03"


class LandmarkRecord(TypedDict):
    name: str
    category: str
    intents: list[str]
    coordinates: dict[str, float]
    estimated_visit_minutes: int
    estimated_cost: int
    priority_rank: int
    source_publisher: str
    source_url: str
    reviewed_at: str
    review_due_at: str


MUMBAI_SOURCE = {
    "source_publisher": "Department of Tourism Maharashtra",
    "source_url": "https://maharashtratourism.gov.in/districts/mumbai-city/",
    "reviewed_at": "2026-08-03",
    "review_due_at": "2027-02-03",
}


LANDMARK_CATALOGUE: dict[str, list[LandmarkRecord]] = {
    "mumbai": [
        {"name": "Gateway of India", "category": "historic", "intents": ["culture"], "coordinates": {"lat": 18.9220, "lng": 72.8347}, "estimated_visit_minutes": 60, "estimated_cost": 0, "priority_rank": 1, **MUMBAI_SOURCE},
        {"name": "Chhatrapati Shivaji Maharaj Terminus", "category": "historic", "intents": ["culture"], "coordinates": {"lat": 18.9401, "lng": 72.8356}, "estimated_visit_minutes": 60, "estimated_cost": 0, "priority_rank": 2, **MUMBAI_SOURCE},
        {"name": "Marine Drive", "category": "viewpoint", "intents": ["culture", "relaxation"], "coordinates": {"lat": 18.9430, "lng": 72.8236}, "estimated_visit_minutes": 75, "estimated_cost": 0, "priority_rank": 3, **MUMBAI_SOURCE},
        {"name": "Elephanta Caves", "category": "attraction", "intents": ["culture", "spiritual"], "coordinates": {"lat": 18.9633, "lng": 72.9315}, "estimated_visit_minutes": 300, "estimated_cost": 400, "priority_rank": 4, **MUMBAI_SOURCE},
        {"name": "Haji Ali Dargah", "category": "place_of_worship", "intents": ["culture", "spiritual"], "coordinates": {"lat": 18.9827, "lng": 72.8102}, "estimated_visit_minutes": 60, "estimated_cost": 0, "priority_rank": 5, **MUMBAI_SOURCE},
        {"name": "Juhu Beach", "category": "beach", "intents": ["relaxation", "food"], "coordinates": {"lat": 19.0883, "lng": 72.8264}, "estimated_visit_minutes": 120, "estimated_cost": 0, "priority_rank": 6, **MUMBAI_SOURCE},
        {"name": "Siddhivinayak Temple", "category": "place_of_worship", "intents": ["spiritual", "culture"], "coordinates": {"lat": 19.0169, "lng": 72.8305}, "estimated_visit_minutes": 60, "estimated_cost": 0, "priority_rank": 7, **MUMBAI_SOURCE},
    ],
    "delhi": [
        {"name": "India Gate", "category": "historic", "intents": ["culture"], "coordinates": {"lat": 28.6129, "lng": 77.2295}, "estimated_visit_minutes": 45, "estimated_cost": 0, "priority_rank": 1, "source_publisher": "Ministry of Tourism, Government of India", "source_url": "https://www.incredibleindia.gov.in/en/delhi", "reviewed_at": "2026-08-03", "review_due_at": "2027-02-03"},
        {"name": "Red Fort", "category": "historic", "intents": ["culture"], "coordinates": {"lat": 28.6562, "lng": 77.2410}, "estimated_visit_minutes": 120, "estimated_cost": 300, "priority_rank": 2, "source_publisher": "Ministry of Tourism, Government of India", "source_url": "https://www.incredibleindia.gov.in/en/delhi", "reviewed_at": "2026-08-03", "review_due_at": "2027-02-03"},
        {"name": "Qutub Minar", "category": "historic", "intents": ["culture"], "coordinates": {"lat": 28.5245, "lng": 77.1855}, "estimated_visit_minutes": 120, "estimated_cost": 300, "priority_rank": 3, "source_publisher": "Ministry of Tourism, Government of India", "source_url": "https://www.incredibleindia.gov.in/en/delhi", "reviewed_at": "2026-08-03", "review_due_at": "2027-02-03"},
    ],
    "jaipur": [
        {"name": "Amber Fort", "category": "fort", "intents": ["culture"], "coordinates": {"lat": 26.9855, "lng": 75.8513}, "estimated_visit_minutes": 180, "estimated_cost": 600, "priority_rank": 1, "source_publisher": "Ministry of Tourism, Government of India", "source_url": "https://www.incredibleindia.gov.in/en/rajasthan/jaipur", "reviewed_at": "2026-08-03", "review_due_at": "2027-02-03"},
        {"name": "Hawa Mahal", "category": "historic", "intents": ["culture"], "coordinates": {"lat": 26.9239, "lng": 75.8267}, "estimated_visit_minutes": 60, "estimated_cost": 200, "priority_rank": 2, "source_publisher": "Ministry of Tourism, Government of India", "source_url": "https://www.incredibleindia.gov.in/en/rajasthan/jaipur", "reviewed_at": "2026-08-03", "review_due_at": "2027-02-03"},
        {"name": "City Palace", "category": "palace", "intents": ["culture"], "coordinates": {"lat": 26.9258, "lng": 75.8237}, "estimated_visit_minutes": 120, "estimated_cost": 400, "priority_rank": 3, "source_publisher": "Ministry of Tourism, Government of India", "source_url": "https://www.incredibleindia.gov.in/en/rajasthan/jaipur", "reviewed_at": "2026-08-03", "review_due_at": "2027-02-03"},
    ],
    "agra": [
        {"name": "Taj Mahal", "category": "historic", "intents": ["culture"], "coordinates": {"lat": 27.1751, "lng": 78.0421}, "estimated_visit_minutes": 180, "estimated_cost": 300, "priority_rank": 1, "source_publisher": "Ministry of Tourism, Government of India", "source_url": "https://www.incredibleindia.gov.in/en/uttar-pradesh/agra", "reviewed_at": "2026-08-03", "review_due_at": "2027-02-03"},
        {"name": "Agra Fort", "category": "fort", "intents": ["culture"], "coordinates": {"lat": 27.1795, "lng": 78.0211}, "estimated_visit_minutes": 150, "estimated_cost": 300, "priority_rank": 2, "source_publisher": "Ministry of Tourism, Government of India", "source_url": "https://www.incredibleindia.gov.in/en/uttar-pradesh/agra/agra-fort", "reviewed_at": "2026-08-03", "review_due_at": "2027-02-03"},
        {"name": "Itmad-ud-Daulah's Tomb", "category": "historic", "intents": ["culture"], "coordinates": {"lat": 27.1927, "lng": 78.0302}, "estimated_visit_minutes": 90, "estimated_cost": 200, "priority_rank": 3, "source_publisher": "Ministry of Tourism, Government of India", "source_url": "https://www.incredibleindia.gov.in/en/uttar-pradesh/agra", "reviewed_at": "2026-08-03", "review_due_at": "2027-02-03"},
    ],
}
