"""
Geocoding service — Nominatim (OpenStreetMap).
Converts city names to coordinates, validates India-only, calculates distances.
Rate-limited to 1 req/sec with descriptive User-Agent per Nominatim policy.
"""

import asyncio
import logging
import math
from typing import Optional

import httpx

from app.cache.redis_cache import cached
from app.models.trip import CityInfo, CitySearchResult, GeoPoint

logger = logging.getLogger(__name__)

NOMINATIM_BASE = "https://nominatim.openstreetmap.org"
USER_AGENT = "YatraAI-Planner/1.0 (bilal_yatraai@gmail.com)"

# India bounding box (approximate)
INDIA_BBOX = {
    "min_lat": 6.0,
    "max_lat": 37.0,
    "min_lng": 68.0,
    "max_lng": 97.5,
}

# Rate limiter — 1 req/sec for public Nominatim
_last_request_time = 0.0
_rate_lock = asyncio.Lock()


async def _rate_limit():
    """Ensure we respect Nominatim's 1 req/sec policy."""
    global _last_request_time
    async with _rate_lock:
        now = asyncio.get_event_loop().time()
        elapsed = now - _last_request_time
        if elapsed < 1.0:
            await asyncio.sleep(1.0 - elapsed)
        _last_request_time = asyncio.get_event_loop().time()


def _is_in_india(lat: float, lng: float) -> bool:
    """Check if coordinates fall within India's bounding box."""
    return (
        INDIA_BBOX["min_lat"] <= lat <= INDIA_BBOX["max_lat"]
        and INDIA_BBOX["min_lng"] <= lng <= INDIA_BBOX["max_lng"]
    )


def haversine_distance(p1: GeoPoint, p2: GeoPoint) -> float:
    """Calculate the great-circle distance between two points in km."""
    R = 6371  # Earth's radius in km
    lat1, lat2 = math.radians(p1.lat), math.radians(p2.lat)
    dlat = math.radians(p2.lat - p1.lat)
    dlng = math.radians(p2.lng - p1.lng)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


@cached("geocode", ttl_seconds=86400 * 30)  # Cache for 30 days — cities don't move
async def geocode_city(city_name: str) -> Optional[dict]:
    """
    Geocode a city name to coordinates using Nominatim.
    Returns dict (not CityInfo) for JSON-serializable caching.
    """
    await _rate_limit()

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{NOMINATIM_BASE}/search",
            params={
                "q": city_name,
                "format": "jsonv2",
                "addressdetails": 1,
                "limit": 1,
                "countrycodes": "in",  # India only
            },
            headers={"User-Agent": USER_AGENT},
        )
        resp.raise_for_status()
        results = resp.json()

    if not results:
        logger.warning(f"No geocoding results for: {city_name}")
        return None

    result = results[0]
    lat = float(result["lat"])
    lng = float(result["lon"])

    if not _is_in_india(lat, lng):
        logger.warning(f"Location outside India: {city_name} ({lat}, {lng})")
        return None

    address = result.get("address", {})
    state = address.get("state", address.get("state_district"))

    return {
        "name": city_name.title(),
        "state": state,
        "coordinates": {"lat": lat, "lng": lng},
    }


async def geocode_to_city_info(city_name: str) -> Optional[CityInfo]:
    """Geocode and return a CityInfo object."""
    data = await geocode_city(city_name)
    if not data:
        return None

    from app.services.transport import get_iata_code, get_station_code

    return CityInfo(
        name=data["name"],
        state=data.get("state"),
        coordinates=GeoPoint(**data["coordinates"]),
        iata_code=get_iata_code(data["name"]),
        station_code=get_station_code(data["name"]),
    )


@cached("city_search", ttl_seconds=86400 * 7)
async def search_cities(query: str) -> list[dict]:
    """
    Search for Indian cities matching a query string.
    Returns list of dicts for caching.
    """
    if len(query) < 2:
        return []

    await _rate_limit()

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{NOMINATIM_BASE}/search",
            params={
                "q": query,
                "format": "jsonv2",
                "addressdetails": 1,
                "limit": 8,
                "countrycodes": "in",
                "featuretype": "city",
            },
            headers={"User-Agent": USER_AGENT},
        )
        resp.raise_for_status()
        results = resp.json()

    cities = []
    seen = set()

    for r in results:
        lat = float(r["lat"])
        lng = float(r["lon"])

        if not _is_in_india(lat, lng):
            continue

        address = r.get("address", {})
        name = address.get("city", address.get("town", address.get("village", r.get("name", ""))))
        state = address.get("state", "")

        if not name:
            continue

        dedup_key = f"{name.lower()}_{state.lower()}"
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        display = f"{name}, {state}" if state else name

        cities.append({
            "name": name,
            "state": state,
            "display_name": display,
            "coordinates": {"lat": lat, "lng": lng},
        })

    return cities
