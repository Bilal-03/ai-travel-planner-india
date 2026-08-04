"""
Routing service — OSRM (Open Source Routing Machine).
Calculates travel times and routes between POIs for feasibility validation.
"""

import asyncio
import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from app.cache.redis_cache import cached
from app.models.trip import DataProvenance, DataStatus, GeoPoint, RouteSegment

logger = logging.getLogger(__name__)

OSRM_BASE = "https://router.project-osrm.org"

# Rate limiter
_last_request_time = 0.0
_rate_lock = asyncio.Lock()


async def _rate_limit():
    global _last_request_time
    async with _rate_lock:
        now = asyncio.get_event_loop().time()
        elapsed = now - _last_request_time
        if elapsed < 0.2:
            await asyncio.sleep(0.2 - elapsed)
        _last_request_time = asyncio.get_event_loop().time()


@cached("route", ttl_seconds=86400 * 7)  # Cache for 7 days
async def get_route(
    from_lat: float,
    from_lng: float,
    to_lat: float,
    to_lng: float,
) -> Optional[dict]:
    """
    Get driving route between two points via OSRM.
    Returns dict with distance, duration, and geometry.
    """
    await _rate_limit()

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{OSRM_BASE}/route/v1/driving/{from_lng},{from_lat};{to_lng},{to_lat}",
                params={
                    "overview": "full",
                    "geometries": "geojson",
                    "steps": "false",
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.error(f"OSRM route request failed: {e}")
        return None

    if data.get("code") != "Ok" or not data.get("routes"):
        return None

    route = data["routes"][0]
    geometry = route.get("geometry", {}).get("coordinates", [])
    retrieved_at = datetime.now(timezone.utc)

    return {
        "from_point": {"lat": from_lat, "lng": from_lng},
        "to_point": {"lat": to_lat, "lng": to_lng},
        "geometry": geometry,  # [[lng, lat], ...]
        "distance_km": round(route["distance"] / 1000, 1),
        "duration_minutes": round(route["duration"] / 60, 1),
        "provenance": DataProvenance(
            provider="OSRM",
            status=DataStatus.RECENTLY_VERIFIED,
            retrieved_at=retrieved_at,
            expires_at=retrieved_at + timedelta(days=7),
            confidence=0.8,
            source_reference=OSRM_BASE,
            disclaimer="Route distance and duration are traffic-independent planning values; regenerate after reordering stops and recheck travel time on the day.",
        ).model_dump(mode="json"),
    }


async def get_route_segment(from_point: GeoPoint, to_point: GeoPoint) -> Optional[RouteSegment]:
    """Get a route segment between two GeoPoints."""
    data = await get_route(from_point.lat, from_point.lng, to_point.lat, to_point.lng)
    if not data:
        return None
    return RouteSegment(**data)


async def validate_day_feasibility(
    stops: list[GeoPoint],
    visit_durations: list[int],
    max_day_hours: float = 12.0,
) -> tuple[bool, float, list[RouteSegment]]:
    """
    Validate that a day's itinerary is feasible by checking total travel + visit time.

    Returns:
        (is_feasible, total_hours, route_segments)
    """
    if len(stops) < 2:
        total_visit = sum(visit_durations) / 60
        return total_visit <= max_day_hours, total_visit, []

    total_travel_minutes = 0
    segments: list[RouteSegment] = []

    for i in range(len(stops) - 1):
        segment = await get_route_segment(stops[i], stops[i + 1])
        if segment:
            total_travel_minutes += segment.duration_minutes
            segments.append(segment)
        else:
            # Keep the estimate as a segment too, so the local-transport budget
            # and the feasibility result use identical data even when routing is down.
            lat_delta = (stops[i + 1].lat - stops[i].lat) * 111
            lng_delta = (stops[i + 1].lng - stops[i].lng) * 111 * math.cos(math.radians(stops[i].lat))
            estimated_distance = round(math.hypot(lat_delta, lng_delta), 1)
            total_travel_minutes += 30
            segments.append(RouteSegment(
                from_point=stops[i],
                to_point=stops[i + 1],
                distance_km=estimated_distance,
                duration_minutes=30,
                provenance=DataProvenance(
                    provider="YatraAI route estimator",
                    status=DataStatus.ESTIMATED,
                    retrieved_at=datetime.now(timezone.utc),
                    confidence=0.35,
                    source_reference="app://routing/estimate",
                    disclaimer="Route duration is a fallback estimate because the routing provider was unavailable; regenerate after reordering stops and recheck travel time.",
                ),
            ))

    total_visit_minutes = sum(visit_durations)
    total_hours = (total_travel_minutes + total_visit_minutes) / 60

    return total_hours <= max_day_hours, round(total_hours, 1), segments
