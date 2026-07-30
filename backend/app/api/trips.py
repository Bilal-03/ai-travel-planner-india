"""
Trip API routes — main endpoints for generating and sharing itineraries.
"""

import logging
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException

from app.models.trip import Itinerary, PackingItem, TripRequest
from app.services.gemini_planner import generate_itinerary, generate_packing_list, refine_itinerary
from app.services.trip_storage import get_trip, save_trip, update_trip

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/trips", tags=["trips"])


class RefineTripRequest(BaseModel):
    instruction: str = Field(..., min_length=3, max_length=500)


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


@router.post("/{trip_id}/refine", response_model=Itinerary)
async def refine_trip(trip_id: str, request: RefineTripRequest):
    """Apply an AI follow-up instruction to a saved itinerary."""
    itinerary = await get_trip(trip_id)
    if not itinerary:
        raise HTTPException(status_code=404, detail="Trip not found")
    refined = await refine_itinerary(itinerary, request.instruction)
    await update_trip(refined)
    return refined


@router.post("/{trip_id}/packing-list", response_model=list[PackingItem])
async def create_packing_list(trip_id: str):
    """Generate and persist a destination- and weather-aware packing list."""
    itinerary = await get_trip(trip_id)
    if not itinerary:
        raise HTTPException(status_code=404, detail="Trip not found")
    itinerary.packing_list = await generate_packing_list(itinerary)
    await update_trip(itinerary)
    return itinerary.packing_list
