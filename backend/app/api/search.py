"""
Search API routes — city autocomplete and POI search.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.models.trip import CitySearchResult, GeoPoint
from app.services.geocoding import search_cities
from app.services.poi_discovery import discover_pois

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
