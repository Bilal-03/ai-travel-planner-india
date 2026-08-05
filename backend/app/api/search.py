"""
Search API routes — city autocomplete and POI search.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.models.trip import CitySearchResult, Place
from app.services.geocoding import search_cities
from app.services.poi_discovery import discover_pois
from app.services.workspace_places import normalise_pois_to_places

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("/cities", response_model=list[CitySearchResult])
async def search_cities_endpoint(
    q: str = Query(..., min_length=2, description="City search query"),
):
    """Search for Indian cities — used for autocomplete."""
    try:
        results = await search_cities(q)
        return [CitySearchResult(**r) for r in results]
    except Exception as e:
        logger.error(f"City search failed: {e}")
        raise HTTPException(status_code=500, detail="City search failed")


@router.get("/pois")
async def search_pois_endpoint(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    focus: Optional[str] = Query(None, description="Optional prompt focus"),
    radius: int = Query(10000, description="Search radius in meters"),
):
    """Search for points of interest around a location."""
    try:
        focus_terms = [term.strip() for term in (focus or "").split(",") if term.strip()]
        pois = await discover_pois(lat=lat, lng=lng, focus_terms=focus_terms, radius=radius)
        return pois
    except Exception as e:
        logger.error(f"POI search failed: {e}")
        raise HTTPException(status_code=500, detail="POI search failed")


@router.get("/places", response_model=list[Place])
async def search_places_endpoint(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    city: Optional[str] = Query(None, max_length=120, description="Destination city"),
    q: Optional[str] = Query(None, max_length=120, description="Place name or category search"),
    focus: Optional[str] = Query(None, max_length=240, description="Comma-separated trip interests"),
    radius: int = Query(15000, ge=500, le=50000, description="Search radius in meters"),
    limit: int = Query(24, ge=1, le=50, description="Maximum places to return"),
):
    """Return normalized, India-focused places for the trip workspace."""
    try:
        focus_terms = [term.strip() for term in (focus or "").split(",") if term.strip()]
        if q and q.strip():
            focus_terms.append(q.strip())
        pois = await discover_pois(
            lat=lat,
            lng=lng,
            focus_terms=focus_terms,
            radius=radius,
            limit=limit,
            city=city,
        )
        return normalise_pois_to_places(pois, city=city, query=q, limit=limit)
    except Exception as e:
        logger.error(f"Place search failed: {e}")
        raise HTTPException(status_code=500, detail="Place search failed")
