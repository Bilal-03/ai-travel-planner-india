"""
Transport API routes — flights and trains search.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.services.transport import search_flights, search_trains

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/transport", tags=["transport"])


@router.get("/flights")
async def search_flights_endpoint(
    origin: str = Query(..., alias="from", description="Origin city"),
    destination: str = Query(..., alias="to", description="Destination city"),
    date: str = Query(..., description="Departure date (YYYY-MM-DD)"),
    max_price: Optional[int] = Query(None, description="Max price in INR"),
):
    """Search for domestic flights."""
    try:
        flights = await search_flights(origin, destination, date, max_price)
        return flights
    except Exception as e:
        logger.error(f"Flight search failed: {e}")
        raise HTTPException(status_code=500, detail="Flight search failed")


@router.get("/trains")
async def search_trains_endpoint(
    origin: str = Query(..., alias="from", description="Origin city"),
    destination: str = Query(..., alias="to", description="Destination city"),
    date: Optional[str] = Query(None, description="Travel date (YYYY-MM-DD)"),
):
    """Search for trains between cities."""
    try:
        trains = await search_trains(origin, destination, date)
        return trains
    except Exception as e:
        logger.error(f"Train search failed: {e}")
        raise HTTPException(status_code=500, detail="Train search failed")
