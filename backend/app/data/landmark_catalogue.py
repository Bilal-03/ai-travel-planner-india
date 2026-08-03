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


def _official_landmark(
    name: str,
    category: str,
    intents: list[str],
    lat: float,
    lng: float,
    minutes: int,
    cost: int,
    rank: int,
    source_url: str,
) -> LandmarkRecord:
    return {
        "name": name,
        "category": category,
        "intents": intents,
        "coordinates": {"lat": lat, "lng": lng},
        "estimated_visit_minutes": minutes,
        "estimated_cost": cost,
        "priority_rank": rank,
        "source_publisher": "Ministry of Tourism, Government of India",
        "source_url": source_url,
        "reviewed_at": "2026-08-03",
        "review_due_at": "2027-02-03",
    }


def _add_destination_catalogue(
    city: str,
    source_url: str,
    entries: list[tuple[str, str, list[str], float, float]],
) -> None:
    """Add reviewed landmark records with conservative planning estimates."""
    visit_minutes = {
        "fort": 150, "museum": 120, "palace": 120, "nature": 180,
        "zoo": 180, "garden": 75, "lake": 75, "beach": 120,
        "place_of_worship": 60, "historic": 90, "market": 90,
    }
    estimated_cost = {
        "fort": 200, "museum": 200, "palace": 250, "nature": 150,
        "zoo": 200, "garden": 50,
    }
    LANDMARK_CATALOGUE[city] = [
        _official_landmark(
            name, category, intents, lat, lng,
            visit_minutes.get(category, 75), estimated_cost.get(category, 0), rank,
            source_url,
        )
        for rank, (name, category, intents, lat, lng) in enumerate(entries, start=1)
    ]


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
    "goa": [_official_landmark("Basilica of Bom Jesus", "historic", ["culture", "spiritual"], 15.5009, 73.9116, 90, 0, 1, "https://www.incredibleindia.gov.in/en/goa"), _official_landmark("Fort Aguada", "fort", ["culture"], 15.4922, 73.7737, 90, 0, 2, "https://www.incredibleindia.gov.in/en/goa"), _official_landmark("Anjuna Beach", "beach", ["relaxation", "food"], 15.5730, 73.7397, 120, 0, 3, "https://www.incredibleindia.gov.in/en/goa")],
    "bengaluru": [_official_landmark("Lalbagh Botanical Garden", "garden", ["relaxation", "culture"], 12.9507, 77.5848, 120, 0, 1, "https://www.incredibleindia.gov.in/en/karnataka/bengaluru"), _official_landmark("Bangalore Palace", "palace", ["culture"], 12.9987, 77.5920, 90, 300, 2, "https://www.incredibleindia.gov.in/en/karnataka/bengaluru"), _official_landmark("Tipu Sultan's Summer Palace", "palace", ["culture"], 12.9593, 77.5739, 75, 200, 3, "https://www.incredibleindia.gov.in/en/karnataka/bengaluru")],
    "chennai": [_official_landmark("Marina Beach", "beach", ["relaxation", "food"], 13.0500, 80.2824, 120, 0, 1, "https://www.incredibleindia.gov.in/en/tamil-nadu/chennai"), _official_landmark("Kapaleeshwarar Temple", "place_of_worship", ["spiritual", "culture"], 13.0339, 80.2697, 75, 0, 2, "https://www.incredibleindia.gov.in/en/tamil-nadu/chennai"), _official_landmark("Fort St. George", "fort", ["culture"], 13.0807, 80.2870, 90, 100, 3, "https://www.incredibleindia.gov.in/en/tamil-nadu/chennai")],
    "kolkata": [_official_landmark("Victoria Memorial", "museum", ["culture"], 22.5448, 88.3426, 120, 200, 1, "https://www.incredibleindia.gov.in/en/west-bengal/kolkata"), _official_landmark("Indian Museum", "museum", ["culture"], 22.5580, 88.3508, 120, 100, 2, "https://www.incredibleindia.gov.in/en/west-bengal/kolkata"), _official_landmark("Howrah Bridge", "historic", ["culture"], 22.5851, 88.3468, 45, 0, 3, "https://www.incredibleindia.gov.in/en/west-bengal/kolkata")],
    "hyderabad": [_official_landmark("Charminar", "historic", ["culture"], 17.3616, 78.4747, 75, 100, 1, "https://www.incredibleindia.gov.in/en/telangana/hyderabad"), _official_landmark("Golconda Fort", "fort", ["culture"], 17.3833, 78.4011, 180, 300, 2, "https://www.incredibleindia.gov.in/en/telangana/hyderabad"), _official_landmark("Salar Jung Museum", "museum", ["culture"], 17.3713, 78.4804, 120, 200, 3, "https://www.incredibleindia.gov.in/en/telangana/hyderabad")],
    "varanasi": [_official_landmark("Dashashwamedh Ghat", "ghat", ["spiritual", "culture"], 25.3064, 83.0100, 90, 0, 1, "https://www.incredibleindia.gov.in/en/uttar-pradesh/varanasi"), _official_landmark("Kashi Vishwanath Temple", "place_of_worship", ["spiritual"], 25.3109, 83.0107, 90, 0, 2, "https://www.incredibleindia.gov.in/en/uttar-pradesh/varanasi"), _official_landmark("Sarnath", "historic", ["culture", "spiritual"], 25.3755, 83.0217, 180, 0, 3, "https://www.incredibleindia.gov.in/en/uttar-pradesh/varanasi")],
    "udaipur": [_official_landmark("City Palace", "palace", ["culture"], 24.5764, 73.6835, 150, 400, 1, "https://www.incredibleindia.gov.in/en/rajasthan/udaipur"), _official_landmark("Lake Pichola", "lake", ["relaxation", "culture"], 24.5752, 73.6793, 90, 400, 2, "https://www.incredibleindia.gov.in/en/rajasthan/udaipur"), _official_landmark("Jagdish Temple", "place_of_worship", ["spiritual", "culture"], 24.5786, 73.6837, 60, 0, 3, "https://www.incredibleindia.gov.in/en/rajasthan/udaipur")],
    "rishikesh": [_official_landmark("Ram Jhula", "historic", ["spiritual", "culture"], 30.1203, 78.3217, 45, 0, 1, "https://www.incredibleindia.gov.in/en/uttarakhand/rishikesh"), _official_landmark("Triveni Ghat", "ghat", ["spiritual", "culture"], 30.1087, 78.2913, 75, 0, 2, "https://www.incredibleindia.gov.in/en/uttarakhand/rishikesh"), _official_landmark("Beatles Ashram", "historic", ["culture", "relaxation"], 30.1367, 78.3173, 120, 200, 3, "https://www.incredibleindia.gov.in/en/uttarakhand/rishikesh")],
    "manali": [_official_landmark("Hadimba Devi Temple", "place_of_worship", ["spiritual", "culture"], 32.2432, 77.1810, 75, 0, 1, "https://www.incredibleindia.gov.in/en/himachal-pradesh/manali"), _official_landmark("Solang Valley", "viewpoint", ["adventure", "relaxation"], 32.3164, 77.1586, 180, 500, 2, "https://www.incredibleindia.gov.in/en/himachal-pradesh/manali"), _official_landmark("Mall Road", "market", ["food", "culture"], 32.2432, 77.1892, 90, 0, 3, "https://www.incredibleindia.gov.in/en/himachal-pradesh/manali")],
    "kochi": [_official_landmark("Fort Kochi Beach", "beach", ["relaxation", "culture"], 9.9658, 76.2429, 90, 0, 1, "https://www.incredibleindia.gov.in/en/kerala/kochi"), _official_landmark("Mattancherry Palace", "museum", ["culture"], 9.9587, 76.2599, 90, 10, 2, "https://www.incredibleindia.gov.in/en/kerala/kochi"), _official_landmark("Paradesi Synagogue", "place_of_worship", ["culture"], 9.9575, 76.2599, 60, 10, 3, "https://www.incredibleindia.gov.in/en/kerala/kochi")],
    "srinagar": [_official_landmark("Dal Lake", "lake", ["relaxation", "culture"], 34.1175, 74.8669, 120, 500, 1, "https://www.incredibleindia.gov.in/en/jammu-and-kashmir/srinagar"), _official_landmark("Shalimar Bagh", "garden", ["relaxation", "culture"], 34.1494, 74.8720, 90, 50, 2, "https://www.incredibleindia.gov.in/en/jammu-and-kashmir/srinagar"), _official_landmark("Shankaracharya Temple", "place_of_worship", ["spiritual", "culture"], 34.0837, 74.8667, 120, 0, 3, "https://www.incredibleindia.gov.in/en/jammu-and-kashmir/srinagar")],
}

# The first three records in each of these destinations establish the primary
# anchors. These additional records deliberately make a multi-day
# catalogue available to the deterministic planner. All costs and visit times
# are planning estimates, not claims of current entry pricing or opening hours.
LANDMARK_CATALOGUE["goa"].extend([
    _official_landmark("Chapora Fort", "fort", ["culture", "relaxation"], 15.6042, 73.7448, 90, 0, 4, "https://www.incredibleindia.gov.in/en/goa"),
    _official_landmark("Se Cathedral", "historic", ["culture", "spiritual"], 15.5033, 73.9118, 60, 0, 5, "https://www.incredibleindia.gov.in/en/goa"),
    _official_landmark("Calangute Beach", "beach", ["relaxation", "food"], 15.5439, 73.7553, 150, 0, 6, "https://www.incredibleindia.gov.in/en/goa"),
    _official_landmark("Dona Paula View Point", "viewpoint", ["relaxation", "culture"], 15.4657, 73.8050, 60, 0, 7, "https://www.incredibleindia.gov.in/en/goa"),
    _official_landmark("Salim Ali Bird Sanctuary", "nature", ["adventure", "relaxation"], 15.5138, 73.8789, 120, 100, 8, "https://www.incredibleindia.gov.in/en/goa"),
])

LANDMARK_CATALOGUE["bengaluru"].extend([
    _official_landmark("Cubbon Park", "park", ["relaxation", "culture"], 12.9763, 77.5929, 90, 0, 4, "https://www.incredibleindia.gov.in/en/karnataka/bengaluru"),
    _official_landmark("Vidhana Soudha", "historic", ["culture"], 12.9795, 77.5907, 45, 0, 5, "https://www.incredibleindia.gov.in/en/karnataka/bengaluru"),
    _official_landmark("ISKCON Temple Bengaluru", "place_of_worship", ["spiritual", "culture"], 13.0109, 77.5511, 75, 0, 6, "https://www.incredibleindia.gov.in/en/karnataka/bengaluru"),
    _official_landmark("National Gallery of Modern Art", "museum", ["culture"], 12.9894, 77.5894, 90, 200, 7, "https://www.incredibleindia.gov.in/en/karnataka/bengaluru"),
    _official_landmark("Bull Temple", "place_of_worship", ["spiritual", "culture"], 12.9429, 77.5671, 45, 0, 8, "https://www.incredibleindia.gov.in/en/karnataka/bengaluru"),
])

LANDMARK_CATALOGUE["chennai"].extend([
    _official_landmark("Government Museum Chennai", "museum", ["culture"], 13.0718, 80.2608, 120, 250, 4, "https://www.incredibleindia.gov.in/en/tamil-nadu/chennai"),
    _official_landmark("San Thome Basilica", "historic", ["culture", "spiritual"], 13.0330, 80.2776, 60, 0, 5, "https://www.incredibleindia.gov.in/en/tamil-nadu/chennai"),
    _official_landmark("Parthasarathy Temple", "place_of_worship", ["spiritual", "culture"], 13.0549, 80.2792, 60, 0, 6, "https://www.incredibleindia.gov.in/en/tamil-nadu/chennai"),
    _official_landmark("Valluvar Kottam", "historic", ["culture"], 13.0581, 80.2411, 60, 0, 7, "https://www.incredibleindia.gov.in/en/tamil-nadu/chennai"),
    _official_landmark("Elliot's Beach", "beach", ["relaxation", "food"], 13.0000, 80.2707, 120, 0, 8, "https://www.incredibleindia.gov.in/en/tamil-nadu/chennai"),
])

LANDMARK_CATALOGUE["kolkata"].extend([
    _official_landmark("St. Paul's Cathedral", "historic", ["culture", "spiritual"], 22.5446, 88.3473, 60, 0, 4, "https://www.incredibleindia.gov.in/en/west-bengal/kolkata"),
    _official_landmark("Prinsep Ghat", "historic", ["relaxation", "culture"], 22.5444, 88.3327, 60, 0, 5, "https://www.incredibleindia.gov.in/en/west-bengal/kolkata"),
    _official_landmark("Jorasanko Thakur Bari", "museum", ["culture"], 22.5842, 88.3620, 90, 100, 6, "https://www.incredibleindia.gov.in/en/west-bengal/kolkata"),
    _official_landmark("Mother House", "historic", ["culture", "spiritual"], 22.5529, 88.3593, 60, 0, 7, "https://www.incredibleindia.gov.in/en/west-bengal/kolkata"),
    _official_landmark("Kumartuli", "neighbourhood", ["culture"], 22.6030, 88.3636, 90, 0, 8, "https://www.incredibleindia.gov.in/en/west-bengal/kolkata"),
])

LANDMARK_CATALOGUE["hyderabad"].extend([
    _official_landmark("Chowmahalla Palace", "palace", ["culture"], 17.3578, 78.4717, 120, 250, 4, "https://www.incredibleindia.gov.in/en/telangana/hyderabad"),
    _official_landmark("Mecca Masjid", "place_of_worship", ["spiritual", "culture"], 17.3604, 78.4735, 60, 0, 5, "https://www.incredibleindia.gov.in/en/telangana/hyderabad"),
    _official_landmark("Hussain Sagar", "lake", ["relaxation", "culture"], 17.4239, 78.4738, 90, 0, 6, "https://www.incredibleindia.gov.in/en/telangana/hyderabad"),
    _official_landmark("Birla Mandir", "place_of_worship", ["spiritual", "culture"], 17.4062, 78.4691, 60, 0, 7, "https://www.incredibleindia.gov.in/en/telangana/hyderabad"),
    _official_landmark("Qutb Shahi Tombs", "historic", ["culture"], 17.3947, 78.3947, 90, 100, 8, "https://www.incredibleindia.gov.in/en/telangana/hyderabad"),
])

LANDMARK_CATALOGUE["varanasi"].extend([
    _official_landmark("Assi Ghat", "ghat", ["spiritual", "culture"], 25.2872, 83.0054, 75, 0, 4, "https://www.incredibleindia.gov.in/en/uttar-pradesh/varanasi"),
    _official_landmark("Manikarnika Ghat", "ghat", ["spiritual", "culture"], 25.3120, 83.0105, 45, 0, 5, "https://www.incredibleindia.gov.in/en/uttar-pradesh/varanasi"),
    _official_landmark("Bharat Mata Mandir", "place_of_worship", ["spiritual", "culture"], 25.3234, 82.9891, 60, 0, 6, "https://www.incredibleindia.gov.in/en/uttar-pradesh/varanasi"),
    _official_landmark("Banaras Hindu University", "historic", ["culture"], 25.2677, 82.9913, 90, 0, 7, "https://www.incredibleindia.gov.in/en/uttar-pradesh/varanasi"),
    _official_landmark("Ramnagar Fort", "fort", ["culture"], 25.2712, 83.0292, 120, 100, 8, "https://www.incredibleindia.gov.in/en/uttar-pradesh/varanasi"),
])

LANDMARK_CATALOGUE["udaipur"].extend([
    _official_landmark("Jagmandir Island Palace", "palace", ["culture", "relaxation"], 24.5688, 73.6784, 120, 500, 4, "https://www.incredibleindia.gov.in/en/rajasthan/udaipur"),
    _official_landmark("Fateh Sagar Lake", "lake", ["relaxation", "culture"], 24.6009, 73.6753, 90, 0, 5, "https://www.incredibleindia.gov.in/en/rajasthan/udaipur"),
    _official_landmark("Saheliyon-ki-Bari", "garden", ["relaxation", "culture"], 24.6051, 73.6848, 75, 50, 6, "https://www.incredibleindia.gov.in/en/rajasthan/udaipur"),
    _official_landmark("Sajjangarh Palace", "palace", ["culture", "relaxation"], 24.6003, 73.6664, 120, 150, 7, "https://www.incredibleindia.gov.in/en/rajasthan/udaipur"),
    _official_landmark("Bagore Ki Haveli", "museum", ["culture"], 24.5788, 73.6827, 90, 150, 8, "https://www.incredibleindia.gov.in/en/rajasthan/udaipur"),
])

LANDMARK_CATALOGUE["rishikesh"].extend([
    _official_landmark("Parmarth Niketan", "place_of_worship", ["spiritual", "culture"], 30.1269, 78.3260, 75, 0, 4, "https://www.incredibleindia.gov.in/en/uttarakhand/rishikesh"),
    _official_landmark("Gita Bhawan", "place_of_worship", ["spiritual", "culture"], 30.1234, 78.3229, 60, 0, 5, "https://www.incredibleindia.gov.in/en/uttarakhand/rishikesh"),
    _official_landmark("Bharat Mandir", "place_of_worship", ["spiritual", "culture"], 30.1077, 78.2943, 60, 0, 6, "https://www.incredibleindia.gov.in/en/uttarakhand/rishikesh"),
    _official_landmark("Trayambakeshwar Temple", "place_of_worship", ["spiritual", "culture"], 30.1217, 78.3229, 60, 0, 7, "https://www.incredibleindia.gov.in/en/uttarakhand/rishikesh"),
    _official_landmark("Neelkanth Mahadev Temple", "place_of_worship", ["spiritual", "adventure"], 30.0965, 78.3490, 180, 0, 8, "https://www.incredibleindia.gov.in/en/uttarakhand/rishikesh"),
])

LANDMARK_CATALOGUE["manali"].extend([
    _official_landmark("Manu Temple", "place_of_worship", ["spiritual", "culture"], 32.2507, 77.1906, 60, 0, 4, "https://www.incredibleindia.gov.in/en/himachal-pradesh/manali"),
    _official_landmark("Vashisht Temple", "place_of_worship", ["spiritual", "culture"], 32.2592, 77.1883, 75, 0, 5, "https://www.incredibleindia.gov.in/en/himachal-pradesh/manali"),
    _official_landmark("Himalayan Nyingmapa Gompa", "place_of_worship", ["spiritual", "culture"], 32.2422, 77.1875, 60, 0, 6, "https://www.incredibleindia.gov.in/en/himachal-pradesh/manali"),
    _official_landmark("Jogini Falls", "waterfall", ["adventure", "relaxation"], 32.2700, 77.1850, 180, 0, 7, "https://www.incredibleindia.gov.in/en/himachal-pradesh/manali"),
    _official_landmark("Nehru Kund", "nature", ["relaxation", "adventure"], 32.2796, 77.1784, 45, 0, 8, "https://www.incredibleindia.gov.in/en/himachal-pradesh/manali"),
])

LANDMARK_CATALOGUE["kochi"].extend([
    _official_landmark("Chinese Fishing Nets", "historic", ["culture"], 9.9685, 76.2410, 45, 0, 4, "https://www.incredibleindia.gov.in/en/kerala/kochi"),
    _official_landmark("St. Francis Church", "historic", ["culture", "spiritual"], 9.9658, 76.2424, 60, 0, 5, "https://www.incredibleindia.gov.in/en/kerala/kochi"),
    _official_landmark("Santa Cruz Basilica", "historic", ["culture", "spiritual"], 9.9637, 76.2423, 60, 0, 6, "https://www.incredibleindia.gov.in/en/kerala/kochi"),
    _official_landmark("Jew Town", "neighbourhood", ["culture", "food"], 9.9584, 76.2592, 90, 0, 7, "https://www.incredibleindia.gov.in/en/kerala/kochi"),
    _official_landmark("Hill Palace Museum", "museum", ["culture"], 9.9515, 76.3621, 120, 100, 8, "https://www.incredibleindia.gov.in/en/kerala/kochi"),
])

LANDMARK_CATALOGUE["srinagar"].extend([
    _official_landmark("Nishat Bagh", "garden", ["relaxation", "culture"], 34.1341, 74.8848, 90, 50, 4, "https://www.incredibleindia.gov.in/en/jammu-and-kashmir/srinagar"),
    _official_landmark("Hazratbal Shrine", "place_of_worship", ["spiritual", "culture"], 34.1226, 74.8373, 75, 0, 5, "https://www.incredibleindia.gov.in/en/jammu-and-kashmir/srinagar"),
    _official_landmark("Jamia Masjid Srinagar", "place_of_worship", ["spiritual", "culture"], 34.0922, 74.8099, 60, 0, 6, "https://www.incredibleindia.gov.in/en/jammu-and-kashmir/srinagar"),
    _official_landmark("Pari Mahal", "historic", ["culture", "relaxation"], 34.0687, 74.8767, 90, 50, 7, "https://www.incredibleindia.gov.in/en/jammu-and-kashmir/srinagar"),
    _official_landmark("Nigeen Lake", "lake", ["relaxation", "culture"], 34.1269, 74.8523, 90, 500, 8, "https://www.incredibleindia.gov.in/en/jammu-and-kashmir/srinagar"),
])

# A twelve-place catalogue gives four-or-more-day trips enough major sights to
# choose from without treating every map POI as an attraction. These are still
# editorial recommendations, not a claim that a venue is currently open.
LANDMARK_CATALOGUE["goa"].extend([
    _official_landmark("Shri Manguesh Temple", "place_of_worship", ["spiritual", "culture"], 15.4415, 73.9845, 60, 0, 9, "https://www.incredibleindia.gov.in/en/goa/goa"),
    _official_landmark("Palolem Beach", "beach", ["relaxation", "food"], 15.0099, 74.0232, 150, 0, 10, "https://www.incredibleindia.gov.in/en/goa/goa/palolem-beach"),
    _official_landmark("Reis Magos Fort", "fort", ["culture"], 15.4993, 73.8072, 90, 100, 11, "https://www.incredibleindia.gov.in/en/goa/goa/reis-magos-fort"),
    _official_landmark("Goa State Museum", "museum", ["culture"], 15.4989, 73.8289, 90, 50, 12, "https://www.incredibleindia.gov.in/en/goa/goa"),
])

LANDMARK_CATALOGUE["bengaluru"].extend([
    _official_landmark("Visvesvaraya Industrial and Technological Museum", "museum", ["culture"], 12.9758, 77.5964, 120, 100, 9, "https://www.incredibleindia.gov.in/en/karnataka/bengaluru"),
    _official_landmark("Bangalore Fort", "fort", ["culture"], 12.9626, 77.5750, 60, 0, 10, "https://www.incredibleindia.gov.in/en/karnataka/bengaluru"),
    _official_landmark("Bannerghatta National Park", "nature", ["adventure", "relaxation"], 12.8007, 77.5770, 240, 500, 11, "https://www.incredibleindia.gov.in/en/karnataka/bengaluru"),
    _official_landmark("Ulsoor Lake", "lake", ["relaxation", "culture"], 12.9825, 77.6191, 60, 0, 12, "https://www.incredibleindia.gov.in/en/karnataka/bengaluru"),
])

LANDMARK_CATALOGUE["chennai"].extend([
    _official_landmark("Guindy National Park", "nature", ["adventure", "relaxation"], 13.0069, 80.2208, 150, 250, 9, "https://www.incredibleindia.gov.in/en/tamil-nadu/chennai/guindy-national-park"),
    _official_landmark("Dakshinachitra Museum", "museum", ["culture"], 12.8238, 80.2433, 150, 250, 10, "https://www.incredibleindia.gov.in/en/tamil-nadu/chennai/guindy-national-park"),
    _official_landmark("Arignar Anna Zoological Park", "zoo", ["adventure", "relaxation"], 12.8799, 79.9971, 240, 300, 11, "https://www.incredibleindia.gov.in/en/tamil-nadu/chennai/a-gateway-to-unforgettable-experiences"),
    _official_landmark("Birla Planetarium Chennai", "museum", ["culture"], 13.0124, 80.2420, 90, 200, 12, "https://www.incredibleindia.gov.in/en/tamil-nadu/chennai/a-gateway-to-unforgettable-experiences"),
])

LANDMARK_CATALOGUE["kolkata"].extend([
    _official_landmark("Science City Kolkata", "museum", ["culture", "adventure"], 22.5416, 88.3969, 180, 300, 9, "https://www.incredibleindia.gov.in/en/west-bengal/kolkata/science-city"),
    _official_landmark("Belur Math", "place_of_worship", ["spiritual", "culture"], 22.6325, 88.3557, 120, 0, 10, "https://www.incredibleindia.gov.in/en/west-bengal/kolkata/belur-math"),
    _official_landmark("Kalighat Kali Temple", "place_of_worship", ["spiritual", "culture"], 22.5201, 88.3428, 75, 0, 11, "https://www.incredibleindia.gov.in/en/west-bengal/kolkata"),
    _official_landmark("Netaji Bhawan", "museum", ["culture"], 22.5347, 88.3473, 90, 100, 12, "https://www.incredibleindia.gov.in/en/west-bengal/kolkata"),
])

LANDMARK_CATALOGUE["hyderabad"].extend([
    _official_landmark("Nehru Zoological Park", "zoo", ["adventure", "relaxation"], 17.3508, 78.4518, 240, 300, 9, "https://www.incredibleindia.gov.in/en/telangana/hyderabad"),
    _official_landmark("NTR Gardens", "park", ["relaxation", "culture"], 17.4145, 78.4735, 75, 50, 10, "https://www.incredibleindia.gov.in/en/telangana/hyderabad"),
    _official_landmark("Birla Science Museum", "museum", ["culture"], 17.4040, 78.4696, 120, 200, 11, "https://www.incredibleindia.gov.in/en/telangana/hyderabad"),
    _official_landmark("Lumbini Park", "park", ["relaxation", "culture"], 17.4149, 78.4742, 75, 50, 12, "https://www.incredibleindia.gov.in/en/telangana/hyderabad"),
])

LANDMARK_CATALOGUE["varanasi"].extend([
    _official_landmark("Tulsi Manas Temple", "place_of_worship", ["spiritual", "culture"], 25.2955, 83.0034, 60, 0, 9, "https://www.incredibleindia.gov.in/en/uttar-pradesh/varanasi"),
    _official_landmark("Sankat Mochan Hanuman Temple", "place_of_worship", ["spiritual", "culture"], 25.2827, 83.0013, 60, 0, 10, "https://www.incredibleindia.gov.in/en/uttar-pradesh/varanasi"),
    _official_landmark("Durga Mandir", "place_of_worship", ["spiritual", "culture"], 25.2945, 83.0018, 60, 0, 11, "https://www.incredibleindia.gov.in/en/uttar-pradesh/varanasi"),
    _official_landmark("Dhamek Stupa", "historic", ["culture", "spiritual"], 25.3811, 83.0230, 75, 0, 12, "https://www.incredibleindia.gov.in/en/uttar-pradesh/varanasi"),
])

LANDMARK_CATALOGUE["udaipur"].extend([
    _official_landmark("Mansapurna Karni Mata Temple", "place_of_worship", ["spiritual", "culture"], 24.5726, 73.6855, 75, 0, 9, "https://www.incredibleindia.gov.in/en/rajasthan/udaipur"),
    _official_landmark("Ambrai Ghat", "ghat", ["relaxation", "culture"], 24.5767, 73.6796, 60, 0, 10, "https://www.incredibleindia.gov.in/en/rajasthan/udaipur"),
    _official_landmark("Doodh Talai", "lake", ["relaxation", "culture"], 24.5681, 73.6893, 60, 0, 11, "https://www.incredibleindia.gov.in/en/rajasthan/udaipur"),
    _official_landmark("Ahar Cenotaphs", "historic", ["culture"], 24.5794, 73.7189, 90, 50, 12, "https://www.incredibleindia.gov.in/en/rajasthan/udaipur"),
])

LANDMARK_CATALOGUE["rishikesh"].extend([
    _official_landmark("Lakshman Jhula", "historic", ["spiritual", "culture"], 30.1253, 78.3262, 45, 0, 9, "https://www.incredibleindia.gov.in/en/uttarakhand/rishikesh"),
    _official_landmark("Raghunath Temple", "place_of_worship", ["spiritual", "culture"], 30.1104, 78.2952, 45, 0, 10, "https://www.incredibleindia.gov.in/en/uttarakhand/rishikesh"),
    _official_landmark("Kunjapuri Devi Temple", "place_of_worship", ["spiritual", "adventure"], 30.2755, 78.2337, 180, 0, 11, "https://www.incredibleindia.gov.in/en/uttarakhand/rishikesh"),
    _official_landmark("Vashishta Gufa", "historic", ["spiritual", "adventure"], 30.2028, 78.3628, 150, 0, 12, "https://www.incredibleindia.gov.in/en/uttarakhand/rishikesh"),
])

LANDMARK_CATALOGUE["manali"].extend([
    _official_landmark("Naggar Castle", "historic", ["culture"], 32.1107, 77.1661, 120, 100, 9, "https://www.incredibleindia.gov.in/en/himachal-pradesh/manali"),
    _official_landmark("Manali Nature Park", "park", ["relaxation", "adventure"], 32.2427, 77.1858, 90, 0, 10, "https://www.incredibleindia.gov.in/en/himachal-pradesh/manali"),
    _official_landmark("Old Manali", "neighbourhood", ["culture", "food"], 32.2534, 77.1886, 120, 0, 11, "https://www.incredibleindia.gov.in/en/himachal-pradesh/manali"),
    _official_landmark("Rohtang Pass", "viewpoint", ["adventure", "relaxation"], 32.3722, 77.2476, 300, 500, 12, "https://www.incredibleindia.gov.in/en/himachal-pradesh/manali"),
])

LANDMARK_CATALOGUE["kochi"].extend([
    _official_landmark("Marine Drive Kochi", "waterfront", ["relaxation", "culture"], 9.9817, 76.2765, 75, 0, 9, "https://www.incredibleindia.gov.in/en/kerala/kochi"),
    _official_landmark("Kerala Folklore Museum", "museum", ["culture"], 9.9264, 76.3171, 120, 200, 10, "https://www.incredibleindia.gov.in/en/kerala/kochi"),
    _official_landmark("Bolgatty Palace", "palace", ["culture", "relaxation"], 9.9976, 76.2783, 90, 100, 11, "https://www.incredibleindia.gov.in/en/kerala/kochi"),
    _official_landmark("Willingdon Island", "waterfront", ["relaxation", "culture"], 9.9538, 76.2721, 75, 0, 12, "https://www.incredibleindia.gov.in/en/kerala/kochi"),
])

LANDMARK_CATALOGUE["srinagar"].extend([
    _official_landmark("Chashme Shahi", "garden", ["relaxation", "culture"], 34.0779, 74.8784, 75, 50, 9, "https://www.incredibleindia.gov.in/en/jammu-and-kashmir/srinagar"),
    _official_landmark("Hari Parbat Fort", "fort", ["culture"], 34.1112, 74.8115, 120, 0, 10, "https://www.incredibleindia.gov.in/en/jammu-and-kashmir/srinagar"),
    _official_landmark("Badamwari Garden", "garden", ["relaxation", "culture"], 34.1032, 74.8393, 75, 0, 11, "https://www.incredibleindia.gov.in/en/jammu-and-kashmir/srinagar"),
    _official_landmark("Khanqah Shah-i-Hamadan", "place_of_worship", ["spiritual", "culture"], 34.0896, 74.8083, 60, 0, 12, "https://www.incredibleindia.gov.in/en/jammu-and-kashmir/srinagar"),
])

# Bring the originally seeded destinations up to the same twelve-attraction
# standard. The rank expresses editorial prominence, not a mandatory visit
# order, and longer excursions remain subject to daily feasibility checks.
LANDMARK_CATALOGUE["mumbai"].extend([
    _official_landmark("Bandra Fort", "fort", ["culture", "relaxation"], 19.0421, 72.8196, 75, 0, 8, "https://www.incredibleindia.gov.in/en/maharashtra/mumbai/elephanta-caves"),
    _official_landmark("National Museum of Indian Cinema", "museum", ["culture"], 18.9346, 72.8268, 120, 100, 9, "https://www.incredibleindia.gov.in/en/maharashtra/mumbai/elephanta-caves"),
    _official_landmark("Dr. Bhau Daji Lad Museum", "museum", ["culture"], 18.9788, 72.8334, 120, 100, 10, "https://www.incredibleindia.gov.in/en/maharashtra/mumbai/elephanta-caves"),
    _official_landmark("Kanheri Caves", "historic", ["culture", "spiritual", "adventure"], 19.2088, 72.9069, 180, 100, 11, "https://www.incredibleindia.gov.in/en/maharashtra/mumbai/elephanta-caves"),
    _official_landmark("Hanging Gardens", "garden", ["relaxation", "culture"], 18.9562, 72.8044, 60, 0, 12, "https://www.incredibleindia.gov.in/en/maharashtra/mumbai/elephanta-caves"),
])

LANDMARK_CATALOGUE["delhi"].extend([
    _official_landmark("Humayun's Tomb", "historic", ["culture"], 28.5933, 77.2507, 120, 300, 4, "https://www.incredibleindia.gov.in/en/delhi/delhi/akshardham-temple"),
    _official_landmark("Lotus Temple", "place_of_worship", ["spiritual", "culture"], 28.5535, 77.2588, 75, 0, 5, "https://www.incredibleindia.gov.in/en/delhi/delhi/lotus-temple"),
    _official_landmark("Akshardham Temple", "place_of_worship", ["spiritual", "culture"], 28.6127, 77.2773, 180, 0, 6, "https://www.incredibleindia.gov.in/en/delhi/delhi/akshardham-temple"),
    _official_landmark("Jama Masjid", "place_of_worship", ["spiritual", "culture"], 28.6507, 77.2334, 75, 0, 7, "https://www.incredibleindia.gov.in/en/delhi/delhi/akshardham-temple"),
    _official_landmark("Lodhi Garden", "garden", ["relaxation", "culture"], 28.5931, 77.2197, 75, 0, 8, "https://www.incredibleindia.gov.in/en/delhi/delhi/lotus-temple"),
    _official_landmark("Raj Ghat", "historic", ["culture"], 28.6406, 77.2495, 60, 0, 9, "https://www.incredibleindia.gov.in/en/delhi/delhi/akshardham-temple"),
    _official_landmark("Purana Qila", "fort", ["culture"], 28.6096, 77.2433, 120, 100, 10, "https://www.incredibleindia.gov.in/en/delhi/delhi/akshardham-temple"),
    _official_landmark("National Museum", "museum", ["culture"], 28.6118, 77.2197, 150, 250, 11, "https://www.incredibleindia.gov.in/en/delhi/delhi/akshardham-temple"),
    _official_landmark("Gurudwara Bangla Sahib", "place_of_worship", ["spiritual", "culture"], 28.6264, 77.2091, 60, 0, 12, "https://www.incredibleindia.gov.in/en/delhi/delhi/akshardham-temple"),
])

LANDMARK_CATALOGUE["jaipur"].extend([
    _official_landmark("Jantar Mantar", "historic", ["culture"], 26.9248, 75.8246, 90, 200, 4, "https://www.incredibleindia.gov.in/en/rajasthan/jaipur"),
    _official_landmark("Nahargarh Fort", "fort", ["culture", "relaxation"], 26.9373, 75.8158, 150, 200, 5, "https://www.incredibleindia.gov.in/en/rajasthan/jaipur"),
    _official_landmark("Jaigarh Fort", "fort", ["culture"], 26.9850, 75.8454, 150, 200, 6, "https://www.incredibleindia.gov.in/en/rajasthan/jaipur"),
    _official_landmark("Albert Hall Museum", "museum", ["culture"], 26.9117, 75.8197, 120, 200, 7, "https://www.incredibleindia.gov.in/en/rajasthan/jaipur"),
    _official_landmark("Jal Mahal", "palace", ["culture", "relaxation"], 26.9530, 75.8468, 45, 0, 8, "https://www.incredibleindia.gov.in/en/rajasthan/jaipur"),
    _official_landmark("Birla Mandir Jaipur", "place_of_worship", ["spiritual", "culture"], 26.8928, 75.8154, 60, 0, 9, "https://www.incredibleindia.gov.in/en/rajasthan/jaipur"),
    _official_landmark("Galtaji Temple", "place_of_worship", ["spiritual", "culture"], 26.9157, 75.8606, 120, 0, 10, "https://www.incredibleindia.gov.in/en/rajasthan/jaipur"),
    _official_landmark("Sisodia Rani Garden", "garden", ["relaxation", "culture"], 26.9028, 75.8439, 75, 100, 11, "https://www.incredibleindia.gov.in/en/rajasthan/jaipur"),
    _official_landmark("Patrika Gate", "historic", ["culture"], 26.8415, 75.7927, 45, 0, 12, "https://www.incredibleindia.gov.in/en/rajasthan/jaipur"),
])

LANDMARK_CATALOGUE["agra"].extend([
    _official_landmark("Mehtab Bagh", "garden", ["relaxation", "culture"], 27.1811, 78.0431, 75, 50, 4, "https://www.incredibleindia.gov.in/en/uttar-pradesh/agra/mehtab-bagh"),
    _official_landmark("Fatehpur Sikri", "historic", ["culture"], 27.0945, 77.6680, 240, 300, 5, "https://www.incredibleindia.gov.in/en/uttar-pradesh/agra/fatehpur-sikri"),
    _official_landmark("Akbar's Tomb", "historic", ["culture"], 27.2217, 77.9508, 120, 200, 6, "https://www.incredibleindia.gov.in/en/uttar-pradesh/agra"),
    _official_landmark("Chini Ka Rauza", "historic", ["culture"], 27.1944, 78.0410, 60, 50, 7, "https://www.incredibleindia.gov.in/en/uttar-pradesh/agra/mehtab-bagh"),
    _official_landmark("Ram Bagh", "garden", ["relaxation", "culture"], 27.2058, 78.0250, 75, 50, 8, "https://www.incredibleindia.gov.in/en/uttar-pradesh/agra/ram-bagh"),
    _official_landmark("Mankameshwar Temple", "place_of_worship", ["spiritual", "culture"], 27.1804, 78.0174, 60, 0, 9, "https://www.incredibleindia.gov.in/en/uttar-pradesh/agra"),
    _official_landmark("Radhasoami Samadhi", "place_of_worship", ["spiritual", "culture"], 27.2451, 78.0068, 75, 0, 10, "https://www.incredibleindia.gov.in/en/uttar-pradesh/agra"),
    _official_landmark("Mariam's Tomb", "historic", ["culture"], 27.2021, 77.9512, 60, 50, 11, "https://www.incredibleindia.gov.in/en/uttar-pradesh/agra/mehtab-bagh"),
    _official_landmark("Soor Sarovar Bird Sanctuary", "nature", ["adventure", "relaxation"], 27.2376, 77.8203, 180, 100, 12, "https://www.incredibleindia.gov.in/en/uttar-pradesh/agra"),
])

_add_destination_catalogue("amritsar", "https://www.incredibleindia.gov.in/en/punjab/amritsar", [
    ("Golden Temple", "place_of_worship", ["spiritual", "culture"], 31.6200, 74.8765),
    ("Jallianwala Bagh", "historic", ["culture"], 31.6207, 74.8800),
    ("Attari-Wagah Border", "historic", ["culture"], 31.6040, 74.5742),
    ("Durgiana Temple", "place_of_worship", ["spiritual", "culture"], 31.6310, 74.8727),
    ("Gobindgarh Fort", "fort", ["culture"], 31.6335, 74.8969),
    ("Partition Museum", "museum", ["culture"], 31.6247, 74.8769),
    ("Ram Tirath Temple", "place_of_worship", ["spiritual", "culture"], 31.6990, 74.9660),
    ("Maharaja Ranjit Singh Museum", "museum", ["culture"], 31.6380, 74.8610),
    ("Pul Kanjari", "historic", ["culture"], 31.6018, 74.5044),
    ("Khalsa College", "historic", ["culture"], 31.6471, 74.8725),
    ("Sadda Pind", "museum", ["culture", "food"], 31.6770, 74.9770),
    ("Ram Bagh Garden", "garden", ["relaxation", "culture"], 31.6376, 74.8619),
])

_add_destination_catalogue("lucknow", "https://www.incredibleindia.gov.in/en/uttar-pradesh/lucknow", [
    ("Bara Imambara", "historic", ["culture"], 26.8693, 80.9129),
    ("Chota Imambara", "historic", ["culture"], 26.8745, 80.9118),
    ("Rumi Darwaza", "historic", ["culture"], 26.8717, 80.9120),
    ("The Residency", "historic", ["culture"], 26.8686, 80.9367),
    ("Hazratganj Market", "market", ["culture", "food"], 26.8499, 80.9472),
    ("Ambedkar Memorial Park", "park", ["culture", "relaxation"], 26.8580, 81.0087),
    ("Janeshwar Mishra Park", "park", ["relaxation"], 26.8722, 81.0291),
    ("Husainabad Clock Tower", "historic", ["culture"], 26.8737, 80.9131),
    ("State Museum Lucknow", "museum", ["culture"], 26.8607, 80.9334),
    ("Dilkusha Kothi", "historic", ["culture"], 26.8387, 80.9732),
    ("La Martiniere College", "historic", ["culture"], 26.8493, 80.9752),
    ("Nawab Wajid Ali Shah Zoological Garden", "zoo", ["adventure", "relaxation"], 26.8475, 80.9398),
])

_add_destination_catalogue("mysuru", "https://www.incredibleindia.gov.in/en/karnataka/mysuru", [
    ("Mysore Palace", "palace", ["culture"], 12.3052, 76.6552),
    ("Chamundeshwari Temple", "place_of_worship", ["spiritual", "culture"], 12.2729, 76.6708),
    ("St. Philomena's Cathedral", "historic", ["culture", "spiritual"], 12.3220, 76.6627),
    ("Brindavan Gardens", "garden", ["relaxation", "culture"], 12.4213, 76.5728),
    ("Mysore Zoo", "zoo", ["adventure", "relaxation"], 12.3021, 76.6646),
    ("Jaganmohan Palace", "museum", ["culture"], 12.3075, 76.6509),
    ("Karanji Lake", "lake", ["relaxation", "adventure"], 12.2976, 76.6691),
    ("Lalitha Mahal Palace", "palace", ["culture"], 12.2838, 76.6806),
    ("Mysore Railway Museum", "museum", ["culture"], 12.3148, 76.6450),
    ("Devaraja Market", "market", ["culture", "food"], 12.3081, 76.6511),
    ("Ranganathittu Bird Sanctuary", "nature", ["adventure", "relaxation"], 12.4229, 76.6554),
    ("Srirangapatna", "historic", ["culture"], 12.4220, 76.6840),
])

_add_destination_catalogue("jodhpur", "https://www.incredibleindia.gov.in/en/rajasthan/jodhpur", [
    ("Mehrangarh Fort", "fort", ["culture"], 26.2980, 73.0186),
    ("Jaswant Thada", "historic", ["culture"], 26.3032, 73.0237),
    ("Umaid Bhawan Palace", "palace", ["culture"], 26.2815, 73.0479),
    ("Ghanta Ghar", "historic", ["culture"], 26.2941, 73.0245),
    ("Mandore Gardens", "garden", ["relaxation", "culture"], 26.3517, 73.0379),
    ("Toorji Ka Jhalra", "historic", ["culture"], 26.2969, 73.0231),
    ("Rao Jodha Desert Rock Park", "nature", ["adventure", "culture"], 26.3010, 73.0161),
    ("Kaylana Lake", "lake", ["relaxation"], 26.2733, 72.9855),
    ("Machiya Safari Park", "zoo", ["adventure", "relaxation"], 26.2690, 72.9790),
    ("Sardar Government Museum", "museum", ["culture"], 26.2864, 73.0317),
    ("Mahamandir Temple", "place_of_worship", ["spiritual", "culture"], 26.3130, 73.0346),
    ("Chokelao Bagh", "garden", ["relaxation", "culture"], 26.2985, 73.0200),
])

_add_destination_catalogue("shimla", "https://www.incredibleindia.gov.in/en/himachal-pradesh/shimla", [
    ("The Ridge", "historic", ["culture", "relaxation"], 31.1048, 77.1734), ("Mall Road", "market", ["culture", "food"], 31.1041, 77.1730),
    ("Jakhoo Temple", "place_of_worship", ["spiritual", "culture"], 31.1100, 77.1713), ("Christ Church", "historic", ["culture", "spiritual"], 31.1047, 77.1741),
    ("Viceregal Lodge", "historic", ["culture"], 31.1035, 77.1600), ("Kalka-Shimla Railway", "historic", ["culture"], 31.1049, 77.1640),
    ("Kufri", "nature", ["adventure", "relaxation"], 31.0977, 77.2671), ("Annandale", "park", ["relaxation"], 31.0962, 77.1506),
    ("Tara Devi Temple", "place_of_worship", ["spiritual", "culture"], 31.0320, 77.1321), ("Chadwick Falls", "nature", ["adventure", "relaxation"], 31.1048, 77.1282),
    ("Himachal State Museum", "museum", ["culture"], 31.1014, 77.1657), ("Gaiety Heritage Cultural Complex", "historic", ["culture"], 31.1045, 77.1732),
])

_add_destination_catalogue("ooty", "https://www.incredibleindia.gov.in/en/tamil-nadu/ooty", [
    ("Government Botanical Garden", "garden", ["relaxation", "culture"], 11.4119, 76.7022), ("Ooty Lake", "lake", ["relaxation"], 11.4055, 76.6950),
    ("Doddabetta Peak", "nature", ["adventure", "relaxation"], 11.4064, 76.7354), ("Government Rose Garden", "garden", ["relaxation"], 11.4134, 76.7072),
    ("Nilgiri Mountain Railway", "historic", ["culture"], 11.4100, 76.7080), ("Pykara Lake", "lake", ["relaxation", "adventure"], 11.4560, 76.5350),
    ("Pykara Falls", "nature", ["adventure", "relaxation"], 11.4743, 76.5431), ("Avalanche Lake", "lake", ["relaxation", "adventure"], 11.2648, 76.5855),
    ("Emerald Lake", "lake", ["relaxation"], 11.3520, 76.5880), ("Tea Factory and Museum", "museum", ["culture"], 11.3864, 76.7238),
    ("St. Stephen's Church", "historic", ["culture", "spiritual"], 11.4122, 76.7031), ("Ooty Government Museum", "museum", ["culture"], 11.4163, 76.7080),
])

_add_destination_catalogue("munnar", "https://www.incredibleindia.gov.in/en/kerala/munnar", [
    ("Tea Museum", "museum", ["culture"], 10.0940, 77.0597), ("Eravikulam National Park", "nature", ["adventure", "relaxation"], 10.2182, 77.0883),
    ("Mattupetty Dam", "lake", ["relaxation", "adventure"], 10.1032, 77.1239), ("Echo Point", "nature", ["adventure", "relaxation"], 10.1205, 77.1391),
    ("Kundala Lake", "lake", ["relaxation"], 10.1517, 77.1967), ("Top Station", "nature", ["adventure", "relaxation"], 10.1700, 77.2428),
    ("Attukad Waterfalls", "nature", ["adventure", "relaxation"], 10.0227, 77.0477), ("Pothamedu View Point", "nature", ["relaxation"], 10.0375, 77.0633),
    ("Blossom Hydel Park", "park", ["relaxation"], 10.0693, 77.0536), ("Chinnar Wildlife Sanctuary", "nature", ["adventure"], 10.3567, 77.2038),
    ("Anamudi Peak", "nature", ["adventure"], 10.1708, 77.0614), ("Munnar Tea Gardens", "nature", ["relaxation", "culture"], 10.0889, 77.0595),
])

_add_destination_catalogue("pondicherry", "https://www.incredibleindia.gov.in/en/puducherry", [
    ("Promenade Beach", "beach", ["relaxation", "culture"], 11.9305, 79.8352), ("White Town", "historic", ["culture", "food"], 11.9308, 79.8317),
    ("Sri Aurobindo Ashram", "place_of_worship", ["spiritual", "culture"], 11.9312, 79.8327), ("Auroville", "historic", ["culture", "relaxation"], 12.0069, 79.8100),
    ("Matrimandir", "place_of_worship", ["spiritual", "culture"], 12.0065, 79.8095), ("Paradise Beach", "beach", ["relaxation"], 11.8838, 79.8288),
    ("Botanical Garden", "garden", ["relaxation"], 11.9270, 79.8260), ("Basilica of the Sacred Heart of Jesus", "historic", ["culture", "spiritual"], 11.9263, 79.8277),
    ("Immaculate Conception Cathedral", "historic", ["culture", "spiritual"], 11.9324, 79.8309), ("Manakula Vinayagar Temple", "place_of_worship", ["spiritual", "culture"], 11.9329, 79.8341),
    ("Bharati Park", "park", ["relaxation"], 11.9304, 79.8335), ("Puducherry Museum", "museum", ["culture"], 11.9292, 79.8352),
])

_add_destination_catalogue("madurai", "https://www.incredibleindia.gov.in/en/tamil-nadu/madurai", [
    ("Meenakshi Amman Temple", "place_of_worship", ["spiritual", "culture"], 9.9195, 78.1193), ("Thirumalai Nayakkar Mahal", "palace", ["culture"], 9.9159, 78.1247),
    ("Gandhi Memorial Museum", "museum", ["culture"], 9.9400, 78.1460), ("Koodal Azhagar Temple", "place_of_worship", ["spiritual", "culture"], 9.9209, 78.1167),
    ("St. Mary's Cathedral", "historic", ["culture", "spiritual"], 9.9209, 78.1204), ("Alagar Kovil", "place_of_worship", ["spiritual", "culture"], 10.0634, 78.2120),
    ("Pazhamudircholai", "place_of_worship", ["spiritual", "culture"], 10.0807, 78.2154), ("Vandiyur Mariamman Teppakulam", "historic", ["culture", "relaxation"], 9.9054, 78.1411),
    ("Samanar Hills", "historic", ["adventure", "culture"], 9.8574, 78.0620), ("Thiruparankundram Murugan Temple", "place_of_worship", ["spiritual", "culture"], 9.8828, 78.0723),
    ("Keeladi Museum", "museum", ["culture"], 9.8608, 78.1790), ("Aayiram Kaal Mandapam", "historic", ["culture"], 9.9193, 78.1190),
])

_add_destination_catalogue("tirupati", "https://www.incredibleindia.gov.in/en/andhra-pradesh/tirupati", [
    ("Sri Venkateswara Temple", "place_of_worship", ["spiritual", "culture"], 13.6833, 79.3470), ("Sri Padmavathi Ammavari Temple", "place_of_worship", ["spiritual", "culture"], 13.6300, 79.4110),
    ("Govindaraja Temple", "place_of_worship", ["spiritual", "culture"], 13.6280, 79.4172), ("Kapila Theertham", "place_of_worship", ["spiritual", "culture"], 13.6565, 79.4185),
    ("Chandragiri Fort", "fort", ["culture"], 13.5890, 79.3184), ("Sri Venkateswara Zoological Park", "zoo", ["adventure", "relaxation"], 13.6580, 79.3677),
    ("Sila Thoranam", "nature", ["adventure", "culture"], 13.6886, 79.3621), ("Srivari Padalu", "place_of_worship", ["spiritual", "adventure"], 13.6827, 79.3457),
    ("Akasa Ganga", "nature", ["adventure", "spiritual"], 13.6751, 79.3637), ("Papavinasam Theertham", "nature", ["adventure", "spiritual"], 13.6632, 79.3477),
    ("ISKCON Tirupati", "place_of_worship", ["spiritual", "culture"], 13.6330, 79.4101), ("Talakona Waterfall", "nature", ["adventure", "relaxation"], 13.8192, 79.2134),
])

_add_destination_catalogue("darjeeling", "https://www.incredibleindia.gov.in/en/west-bengal/darjeeling", [
    ("Tiger Hill", "nature", ["adventure", "relaxation"], 27.0354, 88.2637), ("Batasia Loop", "historic", ["culture", "relaxation"], 27.0096, 88.2550),
    ("Darjeeling Himalayan Railway", "historic", ["culture"], 27.0410, 88.2663), ("Ghoom Monastery", "place_of_worship", ["spiritual", "culture"], 27.0065, 88.2600),
    ("Japanese Peace Pagoda", "place_of_worship", ["spiritual", "culture"], 27.0330, 88.2590), ("Himalayan Mountaineering Institute", "museum", ["culture", "adventure"], 27.0558, 88.2664),
    ("Padmaja Naidu Himalayan Zoological Park", "zoo", ["adventure", "relaxation"], 27.0551, 88.2664), ("Rock Garden", "garden", ["relaxation"], 27.0286, 88.2200),
    ("Happy Valley Tea Estate", "nature", ["culture", "relaxation"], 27.0371, 88.2555), ("Observatory Hill", "historic", ["spiritual", "culture"], 27.0432, 88.2644),
    ("Mahakal Temple", "place_of_worship", ["spiritual", "culture"], 27.0431, 88.2641), ("Tibetan Refugee Self Help Centre", "museum", ["culture"], 27.0206, 88.2568),
])

_add_destination_catalogue("ayodhya", "https://www.incredibleindia.gov.in/en/uttar-pradesh/ayodhya", [
    ("Shri Ram Janmabhoomi Mandir", "place_of_worship", ["spiritual", "culture"], 26.7956, 82.1943), ("Hanuman Garhi", "place_of_worship", ["spiritual", "culture"], 26.7973, 82.1997),
    ("Kanak Bhawan", "place_of_worship", ["spiritual", "culture"], 26.7994, 82.1992), ("Ram Ki Paidi", "ghat", ["spiritual", "culture"], 26.8090, 82.2042),
    ("Saryu Ghat", "ghat", ["spiritual", "relaxation"], 26.8111, 82.2016), ("Nageshwarnath Temple", "place_of_worship", ["spiritual", "culture"], 26.8107, 82.2031),
    ("Treta Ke Thakur", "place_of_worship", ["spiritual", "culture"], 26.8036, 82.2005), ("Dashrath Mahal", "historic", ["culture", "spiritual"], 26.7997, 82.1990),
    ("Mani Parvat", "historic", ["culture", "spiritual"], 26.8097, 82.1896), ("Guptar Ghat", "ghat", ["spiritual", "relaxation"], 26.7622, 82.1433),
    ("Tulsi Smarak Bhawan", "museum", ["culture"], 26.8039, 82.2024), ("Bharat Kund", "place_of_worship", ["spiritual", "culture"], 26.6808, 82.2161),
])

_add_destination_catalogue("jaisalmer", "https://www.incredibleindia.gov.in/en/rajasthan/jaisalmer", [
    ("Jaisalmer Fort", "fort", ["culture"], 26.9124, 70.9120), ("Patwon Ki Haveli", "historic", ["culture"], 26.9163, 70.9082),
    ("Gadisar Lake", "lake", ["relaxation", "culture"], 26.9065, 70.9158), ("Salim Singh Ki Haveli", "historic", ["culture"], 26.9155, 70.9101),
    ("Nathmal Ki Haveli", "historic", ["culture"], 26.9144, 70.9091), ("Bada Bagh", "historic", ["culture"], 26.9590, 70.8970),
    ("Kuldhara", "historic", ["culture", "adventure"], 26.9600, 70.7530), ("Sam Sand Dunes", "nature", ["adventure", "relaxation"], 26.8143, 70.5146),
    ("Desert National Park", "nature", ["adventure"], 26.9063, 70.9811), ("Jain Temples", "place_of_worship", ["spiritual", "culture"], 26.9137, 70.9120),
    ("Tanot Mata Temple", "place_of_worship", ["spiritual", "culture"], 27.7835, 70.3711), ("Vyas Chhatri", "historic", ["culture"], 26.9195, 70.9183),
])

_add_destination_catalogue("haridwar", "https://www.incredibleindia.gov.in/en/uttarakhand/haridwar", [
    ("Har Ki Pauri", "ghat", ["spiritual", "culture"], 29.9591, 78.1607), ("Mansa Devi Temple", "place_of_worship", ["spiritual", "culture"], 29.9675, 78.1630),
    ("Chandi Devi Temple", "place_of_worship", ["spiritual", "culture"], 29.9256, 78.1624), ("Maya Devi Temple", "place_of_worship", ["spiritual", "culture"], 29.9555, 78.1583),
    ("Daksha Mahadev Temple", "place_of_worship", ["spiritual", "culture"], 29.9362, 78.1456), ("Bharat Mata Mandir", "place_of_worship", ["spiritual", "culture"], 29.9694, 78.1708),
    ("Pawan Dham", "place_of_worship", ["spiritual", "culture"], 29.9680, 78.1690), ("Shantikunj", "place_of_worship", ["spiritual", "culture"], 29.9774, 78.1712),
    ("Sapt Rishi Ashram", "place_of_worship", ["spiritual", "culture"], 29.9788, 78.1718), ("Rajaji National Park", "nature", ["adventure", "relaxation"], 29.9580, 78.0920),
    ("Kankhal", "historic", ["spiritual", "culture"], 29.9306, 78.1483), ("Chandi Ghat", "ghat", ["spiritual", "relaxation"], 29.9410, 78.1580),
])

_add_destination_catalogue("rameswaram", "https://www.incredibleindia.gov.in/en/tamil-nadu/rameswaram", [
    ("Ramanathaswamy Temple", "place_of_worship", ["spiritual", "culture"], 9.2881, 79.3129), ("Dhanushkodi", "historic", ["culture", "adventure"], 9.1765, 79.4180),
    ("Pamban Bridge", "historic", ["culture"], 9.2783, 79.2727), ("Agnitheertham", "ghat", ["spiritual", "culture"], 9.2877, 79.3144),
    ("Gandhamadhana Parvatham", "place_of_worship", ["spiritual", "culture"], 9.2996, 79.3143), ("Kothandaramaswamy Temple", "place_of_worship", ["spiritual", "culture"], 9.2134, 79.4192),
    ("Dr. A.P.J. Abdul Kalam Memorial", "museum", ["culture"], 9.2877, 79.3035), ("Kalam House", "museum", ["culture"], 9.2885, 79.3030),
    ("Villoondi Theertham", "place_of_worship", ["spiritual", "culture"], 9.3007, 79.2924), ("Five-Faced Hanuman Temple", "place_of_worship", ["spiritual", "culture"], 9.2874, 79.3093),
    ("Ariyaman Beach", "beach", ["relaxation"], 9.8516, 78.9654), ("Water Bird Sanctuary", "nature", ["adventure", "relaxation"], 9.2798, 79.2879),
])

_add_destination_catalogue("kanyakumari", "https://www.incredibleindia.gov.in/en/tamil-nadu/kanyakumari", [
    ("Kanyakumari Beach", "beach", ["relaxation", "culture"], 8.0883, 77.5385), ("Vivekananda Rock Memorial", "historic", ["culture", "spiritual"], 8.0780, 77.5550),
    ("Thiruvalluvar Statue", "historic", ["culture"], 8.0779, 77.5546), ("Kumari Amman Temple", "place_of_worship", ["spiritual", "culture"], 8.0885, 77.5382),
    ("Sunset Point", "nature", ["relaxation"], 8.0879, 77.5400), ("Our Lady of Ransom Church", "historic", ["culture", "spiritual"], 8.0898, 77.5394),
    ("Gandhi Memorial", "historic", ["culture"], 8.0873, 77.5413), ("Padmanabhapuram Palace", "palace", ["culture"], 8.2442, 77.3267),
    ("Suchindram Temple", "place_of_worship", ["spiritual", "culture"], 8.1545, 77.4672), ("Vattakottai Fort", "fort", ["culture", "relaxation"], 8.1277, 77.5648),
    ("Thirparappu Falls", "nature", ["adventure", "relaxation"], 8.3956, 77.2608), ("Baywatch Amusement Park", "park", ["adventure"], 8.0974, 77.5532),
])

_add_destination_catalogue("pushkar", "https://www.incredibleindia.gov.in/en/rajasthan/pushkar", [
    ("Pushkar Lake", "lake", ["spiritual", "culture"], 26.4898, 74.5521), ("Brahma Temple", "place_of_worship", ["spiritual", "culture"], 26.4893, 74.5511),
    ("Savitri Temple", "place_of_worship", ["spiritual", "adventure"], 26.4828, 74.5464), ("Varaha Temple", "place_of_worship", ["spiritual", "culture"], 26.4893, 74.5518),
    ("Rangji Temple", "place_of_worship", ["spiritual", "culture"], 26.4871, 74.5535), ("Pushkar Bazaar", "market", ["culture", "food"], 26.4899, 74.5512),
    ("Man Mahal", "palace", ["culture"], 26.4904, 74.5520), ("Atmeshwar Temple", "place_of_worship", ["spiritual", "culture"], 26.4896, 74.5530),
    ("Gau Ghat", "ghat", ["spiritual", "culture"], 26.4903, 74.5524), ("Merta Road", "historic", ["culture"], 26.4910, 74.5528),
    ("Pap Mochani Temple", "place_of_worship", ["spiritual", "adventure"], 26.4949, 74.5424), ("Rose Garden", "garden", ["relaxation", "culture"], 26.4840, 74.5630),
])

_add_destination_catalogue("nainital", "https://www.incredibleindia.gov.in/en/uttarakhand/nainital", [
    ("Naini Lake", "lake", ["relaxation", "culture"], 29.3803, 79.4636), ("Naina Devi Temple", "place_of_worship", ["spiritual", "culture"], 29.3818, 79.4618),
    ("Snow View Point", "nature", ["relaxation", "adventure"], 29.3924, 79.4663), ("Tiffin Top", "nature", ["adventure", "relaxation"], 29.3873, 79.4514),
    ("Nainital Zoo", "zoo", ["adventure", "relaxation"], 29.3871, 79.4545), ("Governor's House", "historic", ["culture"], 29.3913, 79.4528),
    ("Eco Cave Gardens", "nature", ["adventure"], 29.4025, 79.4538), ("The Mall Road", "market", ["culture", "food"], 29.3809, 79.4621),
    ("G.B. Pant High Altitude Zoo", "zoo", ["adventure", "relaxation"], 29.3868, 79.4547), ("Hanuman Garhi", "place_of_worship", ["spiritual", "culture"], 29.3628, 79.4465),
    ("Bhimtal Lake", "lake", ["relaxation", "adventure"], 29.3469, 79.5614), ("Sattal", "lake", ["relaxation", "adventure"], 29.3840, 79.5320),
])

_add_destination_catalogue("dharamshala", "https://www.incredibleindia.gov.in/en/himachal-pradesh/dharamshala", [
    ("McLeod Ganj", "neighbourhood", ["culture", "food"], 32.2420, 76.3200), ("Tsuglagkhang Complex", "place_of_worship", ["spiritual", "culture"], 32.2426, 76.3219),
    ("Namgyal Monastery", "place_of_worship", ["spiritual", "culture"], 32.2427, 76.3222), ("Bhagsunag Waterfall", "nature", ["adventure", "relaxation"], 32.2474, 76.3352),
    ("Bhagsunag Temple", "place_of_worship", ["spiritual", "culture"], 32.2466, 76.3341), ("Dal Lake Dharamshala", "lake", ["relaxation", "culture"], 32.2652, 76.3271),
    ("St. John in the Wilderness", "historic", ["culture", "spiritual"], 32.2466, 76.3234), ("Kangra Art Museum", "museum", ["culture"], 32.2191, 76.3230),
    ("Dharamshala Cricket Stadium", "historic", ["culture"], 32.1973, 76.3223), ("Norbulingka Institute", "museum", ["culture"], 32.1854, 76.3504),
    ("Triund", "nature", ["adventure"], 32.2695, 76.3565), ("War Memorial Dharamshala", "historic", ["culture"], 32.2196, 76.3345),
])

_add_destination_catalogue("khajuraho", "https://www.incredibleindia.gov.in/en/madhya-pradesh/khajuraho", [
    ("Western Group of Temples", "historic", ["culture", "spiritual"], 24.8511, 79.9199), ("Kandariya Mahadev Temple", "place_of_worship", ["spiritual", "culture"], 24.8515, 79.9191),
    ("Lakshmana Temple", "place_of_worship", ["spiritual", "culture"], 24.8521, 79.9204), ("Devi Jagadambi Temple", "place_of_worship", ["spiritual", "culture"], 24.8510, 79.9195),
    ("Eastern Group of Temples", "historic", ["culture", "spiritual"], 24.8594, 79.9221), ("Jain Group of Temples", "place_of_worship", ["spiritual", "culture"], 24.8613, 79.9209),
    ("Duladeo Temple", "place_of_worship", ["spiritual", "culture"], 24.8409, 79.9175), ("Chaturbhuj Temple", "place_of_worship", ["spiritual", "culture"], 24.8331, 79.9220),
    ("Archaeological Museum Khajuraho", "museum", ["culture"], 24.8524, 79.9208), ("Adivart Tribal and Folk Art Museum", "museum", ["culture"], 24.8472, 79.9312),
    ("Raneh Falls", "nature", ["adventure", "relaxation"], 24.9550, 79.8760), ("Panna National Park", "nature", ["adventure"], 24.7070, 80.1880),
])
