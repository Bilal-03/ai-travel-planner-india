"""
POI discovery service — Overpass API (OpenStreetMap).
Finds points of interest around a destination, filtered by travel vibe.
Results cached for 7 days to respect fair-use policies.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from app.cache.redis_cache import cached
from app.data.landmark_catalogue import LANDMARK_CATALOGUE
from app.models.trip import DataProvenance, DataStatus, GeoPoint, POI, TravelVibe
from app.providers.contracts import PlaceSearchRequest
from app.providers.gateway import get_provider_gateway

logger = logging.getLogger(__name__)

OVERPASS_API = "https://overpass-api.de/api/interpreter"

# Editorially verified landmark records are kept separate from the live OSM
# discovery result. They ensure that a destination's defining sights are
# considered even when an OSM query is incomplete, rate-limited, or dominated
# by lower-value nearby venues. Coordinates should be reviewed when this list
# is expanded.
PRIORITY_CITY_LANDMARKS = LANDMARK_CATALOGUE
"""Compatibility alias for catalogue consumers during the rollout."""

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

# Always include a broad, map-sourced landmark baseline. Vibe filters enrich
# this list; they must not cause major heritage, arts, or public places to be
# excluded before the planner sees them.
LANDMARK_BASELINE_QUERIES = [
    'nwr["tourism"="attraction"](around:{radius},{lat},{lng});',
    'nwr["tourism"="museum"](around:{radius},{lat},{lng});',
    'nwr["historic"](around:{radius},{lat},{lng});',
    'nwr["amenity"="theatre"](around:{radius},{lat},{lng});',
    'nwr["amenity"="arts_centre"](around:{radius},{lat},{lng});',
    'nwr["leisure"="park"](around:{radius},{lat},{lng});',
    'nwr["natural"="beach"](around:{radius},{lat},{lng});',
    'nwr["shop"="mall"](around:{radius},{lat},{lng});',
]

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


def _priority_landmarks(city: Optional[str]) -> list[dict]:
    """Return a copy of the destination's reviewed landmark shortlist."""
    normalized_city = " ".join((city or "").casefold().split())
    city_aliases = {
        "bangalore": "bengaluru",
        "bombay": "mumbai",
        "cochin": "kochi",
        "benaras": "varanasi",
    }
    normalized_city = city_aliases.get(normalized_city, normalized_city)
    priority_pois = []
    for landmark in PRIORITY_CITY_LANDMARKS.get(normalized_city, []):
        reviewed_at = datetime.fromisoformat(landmark["reviewed_at"]).replace(tzinfo=timezone.utc)
        review_due_at = datetime.fromisoformat(landmark["review_due_at"]).replace(tzinfo=timezone.utc)
        provenance = DataProvenance(
            provider=landmark["source_publisher"],
            status=DataStatus.STATIC_REFERENCE,
            retrieved_at=reviewed_at,
            expires_at=review_due_at,
            confidence=0.9,
            source_reference=landmark["source_url"],
            disclaimer="Editorial landmark reference; verify current opening hours, access, ticket price, and closures before visiting.",
        )
        field_provenance = {
            "coordinates": provenance,
            "estimated_visit_minutes": DataProvenance(
                provider="YatraAI planning estimate",
                status=DataStatus.ESTIMATED,
                retrieved_at=reviewed_at,
                expires_at=review_due_at,
                confidence=0.65,
                source_reference="app://poi-estimates",
                disclaimer="Visit duration is a planning estimate and can vary with queues and personal pace.",
            ),
            "estimated_cost": DataProvenance(
                provider="YatraAI planning estimate",
                status=DataStatus.ESTIMATED,
                retrieved_at=reviewed_at,
                expires_at=review_due_at,
                confidence=0.55,
                source_reference="app://poi-estimates",
                disclaimer="Ticket cost is an estimate; verify current admission and special fees before visiting.",
            ),
            "opening_hours": DataProvenance(
                provider="not_provided",
                status=DataStatus.UNAVAILABLE,
                disclaimer="Opening hours were not provided; verify the venue directly before visiting.",
            ),
        }
        priority_pois.append({
            **landmark,
            "coordinates": dict(landmark["coordinates"]),
            "osm_tags": {"source": "editorial_landmark_shortlist"},
            "opening_hours": None,
            "provenance": provenance.model_dump(mode="json"),
            "field_provenance": {
                key: value.model_dump(mode="json")
                for key, value in field_provenance.items()
            },
        })
    return priority_pois


async def _discover_pois_legacy(
    lat: float,
    lng: float,
    vibes: list[str],
    radius: int = 10000,
    limit: int = 30,
    city: Optional[str] = None,
) -> list[dict]:
    """
    Discover POIs around a location based on travel vibes.
    Returns list of dicts for caching.
    """
    priority_pois = _priority_landmarks(city)

    # Start with major places, then enrich according to the user's intent.
    query_parts = [
        template.format(radius=radius, lat=lat, lng=lng)
        for template in LANDMARK_BASELINE_QUERIES
    ]
    for vibe_str in vibes:
        try:
            vibe = TravelVibe(vibe_str)
        except ValueError:
            continue
        for template in VIBE_QUERIES.get(vibe, []):
            query_parts.append(template.format(radius=radius, lat=lat, lng=lng))

    union_body = "\n".join(query_parts)
    overpass_query = f"""
    [out:json][timeout:10];
    (
      {union_body}
    );
    out center {limit * 3};
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
        raise

    pois = priority_pois
    seen_names = {poi["name"].casefold() for poi in priority_pois}
    retrieved_at = datetime.now(timezone.utc)

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

        opening_hours = tags.get("opening_hours")
        provenance = DataProvenance(
            provider="OpenStreetMap Overpass",
            status=DataStatus.RECENTLY_VERIFIED,
            retrieved_at=retrieved_at,
            expires_at=retrieved_at + timedelta(days=7),
            confidence=0.75,
            source_reference="https://www.openstreetmap.org/",
            disclaimer="Map data may be incomplete or stale; verify current opening hours, access, ticket price, and closures before visiting.",
        )
        field_provenance = {
            "coordinates": provenance,
            "estimated_visit_minutes": DataProvenance(
                provider="YatraAI planning estimate",
                status=DataStatus.ESTIMATED,
                retrieved_at=retrieved_at,
                expires_at=retrieved_at + timedelta(days=7),
                confidence=0.55,
                source_reference="app://poi-estimates",
                disclaimer="Visit duration is a planning estimate and can vary with queues and personal pace.",
            ),
            "estimated_cost": DataProvenance(
                provider="YatraAI planning estimate",
                status=DataStatus.ESTIMATED,
                retrieved_at=retrieved_at,
                expires_at=retrieved_at + timedelta(days=7),
                confidence=0.45,
                source_reference="app://poi-estimates",
                disclaimer="Ticket cost is a category estimate; verify current admission and special fees before visiting.",
            ),
            "opening_hours": DataProvenance(
                provider="OpenStreetMap Overpass" if opening_hours else "not_provided",
                status=DataStatus.RECENTLY_VERIFIED if opening_hours else DataStatus.UNAVAILABLE,
                retrieved_at=retrieved_at if opening_hours else None,
                expires_at=retrieved_at + timedelta(days=7) if opening_hours else None,
                confidence=0.65 if opening_hours else None,
                source_reference="https://www.openstreetmap.org/" if opening_hours else None,
                disclaimer="Map opening hours may be stale; verify directly before visiting." if opening_hours else "Opening hours were not provided; verify the venue directly before visiting.",
            ),
        }
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
            "opening_hours": opening_hours,
            "provenance": provenance.model_dump(mode="json"),
            "field_provenance": {
                key: value.model_dump(mode="json")
                for key, value in field_provenance.items()
            },
        })

    logger.info(f"Discovered {len(pois)} POIs for vibes={vibes} at ({lat}, {lng})")
    return pois


@cached("pois", ttl_seconds=86400 * 7)  # Cache for 7 days
async def discover_pois(
    lat: float,
    lng: float,
    vibes: list[str],
    radius: int = 10000,
    limit: int = 30,
    city: Optional[str] = None,
) -> list[dict]:
    """Discover places through the configured places provider or catalogue fallback."""

    request = PlaceSearchRequest(
        coordinates=GeoPoint(lat=lat, lng=lng),
        vibes=vibes,
        radius=radius,
        limit=limit,
        city=city,
    )

    async def legacy_search(provider_request: PlaceSearchRequest) -> list[dict]:
        return await _discover_pois_legacy(
            provider_request.coordinates.lat,
            provider_request.coordinates.lng,
            provider_request.vibes,
            provider_request.radius,
            provider_request.limit,
            provider_request.city,
        )

    try:
        provider = get_provider_gateway().places_provider(legacy_search)
        places = await provider.search(request)
        if places:
            return [place.model_dump(mode="json") for place in places]
    except Exception as e:  # noqa: BLE001 - POI failure must preserve reviewed landmarks
        logger.warning(f"Configured places provider unavailable; using catalogue: {e}")

    return _priority_landmarks(city)
