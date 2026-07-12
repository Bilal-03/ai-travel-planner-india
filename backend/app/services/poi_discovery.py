"""
POI discovery service — Overpass API (OpenStreetMap).
Finds points of interest around a destination, filtered by travel vibe.
Results cached for 7 days to respect fair-use policies.
"""

import asyncio
import logging
from typing import Optional

import httpx

from app.cache.redis_cache import cached
from app.models.trip import GeoPoint, POI, TravelVibe

logger = logging.getLogger(__name__)

OVERPASS_API = "https://overpass-api.de/api/interpreter"

# Rate limiter
_last_request_time = 0.0
_rate_lock = asyncio.Lock()


async def _rate_limit():
    global _last_request_time
    async with _rate_lock:
        now = asyncio.get_event_loop().time()
        elapsed = now - _last_request_time
        if elapsed < 1.5:
            await asyncio.sleep(1.5 - elapsed)
        _last_request_time = asyncio.get_event_loop().time()


# ── Vibe-to-OSM tag mapping ──────────────────────────────────────────

VIBE_QUERIES: dict[TravelVibe, list[str]] = {
    TravelVibe.ADVENTURE: [
        'node["sport"](around:{radius},{lat},{lng});',
        'node["leisure"="park"](around:{radius},{lat},{lng});',
        'node["natural"](around:{radius},{lat},{lng});',
        'way["leisure"="park"](around:{radius},{lat},{lng});',
        'node["tourism"="viewpoint"](around:{radius},{lat},{lng});',
    ],
    TravelVibe.CULTURE: [
        'node["tourism"="museum"](around:{radius},{lat},{lng});',
        'node["historic"](around:{radius},{lat},{lng});',
        'node["tourism"="attraction"](around:{radius},{lat},{lng});',
        'way["tourism"="attraction"](around:{radius},{lat},{lng});',
        'node["amenity"="theatre"](around:{radius},{lat},{lng});',
    ],
    TravelVibe.FOOD: [
        'node["amenity"="restaurant"](around:{radius},{lat},{lng});',
        'node["amenity"="cafe"](around:{radius},{lat},{lng});',
        'node["amenity"="fast_food"](around:{radius},{lat},{lng});',
        'node["shop"="bakery"](around:{radius},{lat},{lng});',
    ],
    TravelVibe.RELAXATION: [
        'node["leisure"="spa"](around:{radius},{lat},{lng});',
        'node["leisure"="garden"](around:{radius},{lat},{lng});',
        'way["leisure"="garden"](around:{radius},{lat},{lng});',
        'node["natural"="beach"](around:{radius},{lat},{lng});',
        'way["natural"="beach"](around:{radius},{lat},{lng});',
    ],
    TravelVibe.SPIRITUAL: [
        'node["amenity"="place_of_worship"](around:{radius},{lat},{lng});',
        'way["amenity"="place_of_worship"](around:{radius},{lat},{lng});',
        'node["historic"="temple"](around:{radius},{lat},{lng});',
        'node["building"="temple"](around:{radius},{lat},{lng});',
    ],
    TravelVibe.NIGHTLIFE: [
        'node["amenity"="bar"](around:{radius},{lat},{lng});',
        'node["amenity"="nightclub"](around:{radius},{lat},{lng});',
        'node["amenity"="pub"](around:{radius},{lat},{lng});',
        'node["leisure"="bowling_alley"](around:{radius},{lat},{lng});',
    ],
}

# Time estimates by category (minutes)
VISIT_TIME_ESTIMATES = {
    "museum": 90,
    "temple": 60,
    "place_of_worship": 45,
    "park": 60,
    "garden": 45,
    "restaurant": 60,
    "cafe": 30,
    "bar": 60,
    "nightclub": 120,
    "beach": 120,
    "viewpoint": 30,
    "attraction": 60,
    "theatre": 120,
    "spa": 90,
    "default": 60,
}

# Cost estimates by category (INR)
COST_ESTIMATES = {
    "museum": 200,
    "temple": 0,
    "place_of_worship": 0,
    "park": 50,
    "restaurant": 500,
    "cafe": 200,
    "bar": 800,
    "nightclub": 1500,
    "beach": 0,
    "spa": 2000,
    "theatre": 500,
    "attraction": 300,
    "default": 100,
}


def _estimate_visit_time(tags: dict) -> int:
    for key in ["tourism", "amenity", "leisure", "historic", "natural"]:
        val = tags.get(key, "")
        if val in VISIT_TIME_ESTIMATES:
            return VISIT_TIME_ESTIMATES[val]
    return VISIT_TIME_ESTIMATES["default"]


def _estimate_cost(tags: dict) -> int:
    for key in ["tourism", "amenity", "leisure", "historic", "natural"]:
        val = tags.get(key, "")
        if val in COST_ESTIMATES:
            return COST_ESTIMATES[val]
    return COST_ESTIMATES["default"]


def _extract_name(element: dict) -> Optional[str]:
    tags = element.get("tags", {})
    return tags.get("name", tags.get("name:en"))


@cached("pois", ttl_seconds=86400 * 7)  # Cache for 7 days
async def discover_pois(
    lat: float,
    lng: float,
    vibes: list[str],
    radius: int = 10000,
    limit: int = 30,
) -> list[dict]:
    """
    Discover POIs around a location based on travel vibes.
    Returns list of dicts for caching.
    """
    # Build Overpass query combining all vibe categories
    query_parts = []
    for vibe_str in vibes:
        try:
            vibe = TravelVibe(vibe_str)
        except ValueError:
            continue
        for template in VIBE_QUERIES.get(vibe, []):
            query_parts.append(template.format(radius=radius, lat=lat, lng=lng))

    if not query_parts:
        # Fallback: general tourist attractions
        query_parts = [
            f'node["tourism"="attraction"](around:{radius},{lat},{lng});',
            f'node["tourism"="museum"](around:{radius},{lat},{lng});',
            f'node["amenity"="restaurant"](around:{radius},{lat},{lng});',
        ]

    union_body = "\n".join(query_parts)
    overpass_query = f"""
    [out:json][timeout:10];
    (
      {union_body}
    );
    out body {limit};
    """

    await _rate_limit()

    try:
        async with httpx.AsyncClient(timeout=12) as client:
            resp = await client.post(
                OVERPASS_API,
                data={"data": overpass_query},
                headers={"User-Agent": "YatraAI-Planner/1.0 (bilal_yatraai@gmail.com)"},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.error(f"Overpass API error: {e}")
        return []

    pois = []
    seen_names = set()

    for element in data.get("elements", []):
        name = _extract_name(element)
        if not name or name.lower() in seen_names:
            continue
        seen_names.add(name.lower())

        tags = element.get("tags", {})
        poi_lat = element.get("lat")
        poi_lng = element.get("lon")

        if poi_lat is None or poi_lng is None:
            # For ways, try to get center
            center = element.get("center", {})
            poi_lat = center.get("lat")
            poi_lng = center.get("lon")

        if poi_lat is None or poi_lng is None:
            continue

        # Determine category
        category = "attraction"
        for key in ["tourism", "amenity", "leisure", "historic", "natural"]:
            if key in tags:
                category = tags[key]
                break

        pois.append({
            "name": name,
            "category": category,
            "coordinates": {"lat": poi_lat, "lng": poi_lng},
            "osm_tags": {k: v for k, v in tags.items() if k in [
                "tourism", "amenity", "leisure", "historic", "natural",
                "cuisine", "opening_hours", "phone", "website",
            ]},
            "estimated_visit_minutes": _estimate_visit_time(tags),
            "estimated_cost": _estimate_cost(tags),
            "opening_hours": tags.get("opening_hours"),
        })

    logger.info(f"Discovered {len(pois)} POIs for vibes={vibes} at ({lat}, {lng})")
    return pois
