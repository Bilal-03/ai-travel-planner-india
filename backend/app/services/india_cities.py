"""Curated Indian city and destination search index.

This local index handles the places travellers search for most often without
calling a public geocoder on every keystroke. Nominatim remains the fallback
for locations not represented here.
"""

from __future__ import annotations

from typing import TypedDict


class IndiaCity(TypedDict):
    name: str
    state: str
    lat: float
    lng: float


# Tourist destinations plus major hubs. Keep this deliberately data-only so it
# can be expanded from a GeoNames import without changing the search logic.
INDIA_CITIES: list[IndiaCity] = [
    {"name": "Agra", "state": "Uttar Pradesh", "lat": 27.1767, "lng": 78.0081},
    {"name": "Ahmedabad", "state": "Gujarat", "lat": 23.0225, "lng": 72.5714},
    {"name": "Ajmer", "state": "Rajasthan", "lat": 26.4499, "lng": 74.6399},
    {"name": "Alappuzha", "state": "Kerala", "lat": 9.4981, "lng": 76.3388},
    {"name": "Amritsar", "state": "Punjab", "lat": 31.6340, "lng": 74.8723},
    {"name": "Auli", "state": "Uttarakhand", "lat": 30.5281, "lng": 79.5669},
    {"name": "Aurangabad", "state": "Maharashtra", "lat": 19.8762, "lng": 75.3433},
    {"name": "Ayodhya", "state": "Uttar Pradesh", "lat": 26.7990, "lng": 82.2042},
    {"name": "Bengaluru", "state": "Karnataka", "lat": 12.9716, "lng": 77.5946},
    {"name": "Bhopal", "state": "Madhya Pradesh", "lat": 23.2599, "lng": 77.4126},
    {"name": "Bhubaneswar", "state": "Odisha", "lat": 20.2961, "lng": 85.8245},
    {"name": "Bikaner", "state": "Rajasthan", "lat": 28.0229, "lng": 73.3119},
    {"name": "Bodh Gaya", "state": "Bihar", "lat": 24.6961, "lng": 84.9911},
    {"name": "Chandigarh", "state": "Chandigarh", "lat": 30.7333, "lng": 76.7794},
    {"name": "Chennai", "state": "Tamil Nadu", "lat": 13.0827, "lng": 80.2707},
    {"name": "Chikmagalur", "state": "Karnataka", "lat": 13.3153, "lng": 75.7754},
    {"name": "Coimbatore", "state": "Tamil Nadu", "lat": 11.0168, "lng": 76.9558},
    {"name": "Dalhousie", "state": "Himachal Pradesh", "lat": 32.5387, "lng": 75.9703},
    {"name": "Darjeeling", "state": "West Bengal", "lat": 27.0410, "lng": 88.2663},
    {"name": "Dehradun", "state": "Uttarakhand", "lat": 30.3165, "lng": 78.0322},
    {"name": "Delhi", "state": "Delhi", "lat": 28.6139, "lng": 77.2090},
    {"name": "Dharamshala", "state": "Himachal Pradesh", "lat": 32.2190, "lng": 76.3234},
    {"name": "Gangtok", "state": "Sikkim", "lat": 27.3389, "lng": 88.6065},
    {"name": "Goa", "state": "Goa", "lat": 15.2993, "lng": 74.1240},
    {"name": "Gokarna", "state": "Karnataka", "lat": 14.5479, "lng": 74.3188},
    {"name": "Gulmarg", "state": "Jammu and Kashmir", "lat": 34.0484, "lng": 74.3805},
    {"name": "Guwahati", "state": "Assam", "lat": 26.1445, "lng": 91.7362},
    {"name": "Hampi", "state": "Karnataka", "lat": 15.3350, "lng": 76.4600},
    {"name": "Haridwar", "state": "Uttarakhand", "lat": 29.9457, "lng": 78.1642},
    {"name": "Hyderabad", "state": "Telangana", "lat": 17.3850, "lng": 78.4867},
    {"name": "Indore", "state": "Madhya Pradesh", "lat": 22.7196, "lng": 75.8577},
    {"name": "Jaipur", "state": "Rajasthan", "lat": 26.9124, "lng": 75.7873},
    {"name": "Jaisalmer", "state": "Rajasthan", "lat": 26.9157, "lng": 70.9083},
    {"name": "Jim Corbett", "state": "Uttarakhand", "lat": 29.5300, "lng": 78.7700},
    {"name": "Jodhpur", "state": "Rajasthan", "lat": 26.2389, "lng": 73.0243},
    {"name": "Kanyakumari", "state": "Tamil Nadu", "lat": 8.0883, "lng": 77.5385},
    {"name": "Kasauli", "state": "Himachal Pradesh", "lat": 30.8989, "lng": 76.9655},
    {"name": "Kaziranga", "state": "Assam", "lat": 26.5775, "lng": 93.1711},
    {"name": "Kochi", "state": "Kerala", "lat": 9.9312, "lng": 76.2673},
    {"name": "Kodaikanal", "state": "Tamil Nadu", "lat": 10.2381, "lng": 77.4892},
    {"name": "Kolkata", "state": "West Bengal", "lat": 22.5726, "lng": 88.3639},
    {"name": "Kumarakom", "state": "Kerala", "lat": 9.6175, "lng": 76.4300},
    {"name": "Kutch", "state": "Gujarat", "lat": 23.7337, "lng": 69.8597},
    {"name": "Leh", "state": "Ladakh", "lat": 34.1526, "lng": 77.5771},
    {"name": "Lucknow", "state": "Uttar Pradesh", "lat": 26.8467, "lng": 80.9462},
    {"name": "Madurai", "state": "Tamil Nadu", "lat": 9.9252, "lng": 78.1198},
    {"name": "Manali", "state": "Himachal Pradesh", "lat": 32.2432, "lng": 77.1892},
    {"name": "Mangalore", "state": "Karnataka", "lat": 12.9141, "lng": 74.8560},
    {"name": "McLeod Ganj", "state": "Himachal Pradesh", "lat": 32.2426, "lng": 76.3213},
    {"name": "Mumbai", "state": "Maharashtra", "lat": 19.0760, "lng": 72.8777},
    {"name": "Munnar", "state": "Kerala", "lat": 10.0889, "lng": 77.0595},
    {"name": "Mysuru", "state": "Karnataka", "lat": 12.2958, "lng": 76.6394},
    {"name": "Nainital", "state": "Uttarakhand", "lat": 29.3803, "lng": 79.4636},
    {"name": "Nashik", "state": "Maharashtra", "lat": 19.9975, "lng": 73.7898},
    {"name": "Ooty", "state": "Tamil Nadu", "lat": 11.4102, "lng": 76.6950},
    {"name": "Pondicherry", "state": "Puducherry", "lat": 11.9416, "lng": 79.8083},
    {"name": "Port Blair", "state": "Andaman and Nicobar Islands", "lat": 11.6234, "lng": 92.7265},
    {"name": "Pushkar", "state": "Rajasthan", "lat": 26.4898, "lng": 74.5511},
    {"name": "Pune", "state": "Maharashtra", "lat": 18.5204, "lng": 73.8567},
    {"name": "Puri", "state": "Odisha", "lat": 19.8135, "lng": 85.8312},
    {"name": "Rameswaram", "state": "Tamil Nadu", "lat": 9.2876, "lng": 79.3129},
    {"name": "Ranthambore", "state": "Rajasthan", "lat": 26.0173, "lng": 76.5026},
    {"name": "Rishikesh", "state": "Uttarakhand", "lat": 30.0869, "lng": 78.2676},
    {"name": "Shillong", "state": "Meghalaya", "lat": 25.5788, "lng": 91.8933},
    {"name": "Shimla", "state": "Himachal Pradesh", "lat": 31.1048, "lng": 77.1734},
    {"name": "Srinagar", "state": "Jammu and Kashmir", "lat": 34.0837, "lng": 74.7973},
    {"name": "Tawang", "state": "Arunachal Pradesh", "lat": 27.5861, "lng": 91.8650},
    {"name": "Thiruvananthapuram", "state": "Kerala", "lat": 8.5241, "lng": 76.9366},
    {"name": "Tirupati", "state": "Andhra Pradesh", "lat": 13.6288, "lng": 79.4192},
    {"name": "Udaipur", "state": "Rajasthan", "lat": 24.5854, "lng": 73.7125},
    {"name": "Varanasi", "state": "Uttar Pradesh", "lat": 25.3176, "lng": 82.9739},
    {"name": "Varkala", "state": "Kerala", "lat": 8.7379, "lng": 76.7163},
    {"name": "Vijayawada", "state": "Andhra Pradesh", "lat": 16.5062, "lng": 80.6480},
    {"name": "Visakhapatnam", "state": "Andhra Pradesh", "lat": 17.6868, "lng": 83.2185},
    {"name": "Wayanad", "state": "Kerala", "lat": 11.6854, "lng": 76.1320},
]


def search_local_cities(query: str, limit: int = 8) -> list[dict]:
    """Return prefix-first, case-insensitive matches from the bundled index."""
    normalized = " ".join(query.casefold().split())
    if len(normalized) < 2:
        return []

    def rank(city: IndiaCity) -> tuple[int, str]:
        haystack = f"{city['name']} {city['state']}".casefold()
        name = city["name"].casefold()
        if name.startswith(normalized):
            return (0, name)
        if any(part.startswith(normalized) for part in name.split()):
            return (1, name)
        return (2, name)

    matches = [
        city for city in INDIA_CITIES
        if normalized in city["name"].casefold() or normalized in city["state"].casefold()
    ]
    return [
        {
            "name": city["name"],
            "state": city["state"],
            "display_name": f"{city['name']}, {city['state']}",
            "coordinates": {"lat": city["lat"], "lng": city["lng"]},
        }
        for city in sorted(matches, key=rank)[:limit]
    ]
