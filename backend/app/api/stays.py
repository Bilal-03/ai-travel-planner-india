"""Stay discovery routes for the trip workspace."""

from datetime import date
import logging

from fastapi import APIRouter, HTTPException, Query

from app.models.trip import StayOption
from app.services.stays import search_stays

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stays", tags=["stays"])


@router.get("", response_model=list[StayOption])
async def search_stays_endpoint(
    city: str = Query(..., min_length=2, max_length=120),
    check_in: date = Query(..., description="Check-in date (YYYY-MM-DD)"),
    check_out: date = Query(..., description="Check-out date (YYYY-MM-DD)"),
    members: int = Query(2, ge=1, le=40),
    hotel_style: str | None = Query(None, max_length=80),
):
    """Return area-level estimates until live property inventory is configured."""

    try:
        return search_stays(
            city=city,
            check_in=check_in,
            check_out=check_out,
            members=members,
            hotel_style=hotel_style,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        logger.exception("Stay search failed")
        raise HTTPException(status_code=500, detail="Stay search failed") from error
