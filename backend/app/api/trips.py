"""
Trip API routes — main endpoints for generating and sharing itineraries.
"""

import logging
from fastapi import APIRouter, HTTPException

from app.models.trip import Itinerary, TripRequest
from app.services.gemini_planner import generate_itinerary
from app.services.trip_storage import get_trip, save_trip

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/trips", tags=["trips"])


@router.post("/generate", response_model=Itinerary)
async def generate_trip(request: TripRequest):
    """
    Generate a complete AI-powered itinerary.
    This is the main endpoint — orchestrates all services.
    """
    try:
        logger.info(
            f"🚀 Generating trip: {request.origin} → {request.destination}, "
            f"₹{request.budget:,}, {request.start_date} to {request.end_date}"
        )
        itinerary = await generate_itinerary(request)

        # Auto-save for sharing
        trip_id = await save_trip(itinerary)
        itinerary.id = trip_id

        return itinerary

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Trip generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate itinerary: {str(e)}",
        )


@router.get("/{trip_id}", response_model=Itinerary)
async def get_trip_by_id(trip_id: str):
    """Retrieve a saved/shared trip by ID."""
    itinerary = await get_trip(trip_id)
    if not itinerary:
        raise HTTPException(status_code=404, detail="Trip not found")
    return itinerary


@router.post("/{trip_id}/share")
async def share_trip(trip_id: str):
    """Get shareable link for a trip."""
    itinerary = await get_trip(trip_id)
    if not itinerary:
        raise HTTPException(status_code=404, detail="Trip not found")

    from app.config import settings
    share_url = f"{settings.frontend_url}/trip/{trip_id}"

    return {"share_url": share_url, "trip_id": trip_id}
