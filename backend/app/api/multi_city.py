"""Phase 6 multi-city generation and scoped workspace edit endpoints."""

from __future__ import annotations

import hashlib
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from pydantic import BaseModel, Field

from app.api.trips import generation_rate_limit
from app.models.collaboration import AnalyticsEventRequest, TripKind
from app.models.trip import MultiCityTripRequest, Trip
from app.services.account_service import get_account_for_token
from app.services.collaboration_service import VersionConflictError, assert_version, record_analytics, resolve_share_token
from app.services.observability import capture_exception, monotonic_ms, safe_error_message
from app.services.multi_city_planner import (
    generate_multi_city_trip,
    reorder_multi_city_trip,
    update_multi_city_stay,
)
from app.services.trip_storage import (
    get_multi_city_trip,
    get_multi_city_trip_owner_token_hash,
    save_multi_city_trip,
    update_multi_city_trip,
)

router = APIRouter(prefix="/api/multi-city", tags=["multi-city"])
EDIT_TOKEN_HEADER = "X-Trip-Edit-Token"
SHARE_TOKEN_HEADER = "X-Trip-Share-Token"
ACCOUNT_TOKEN_HEADER = "X-Yatra-Account-Token"


class ReorderDestinationRequest(BaseModel):
    destination_stay_ids: list[str] = Field(..., min_length=2, max_length=5)


class UpdateDestinationStayRequest(BaseModel):
    nights: int | None = Field(None, ge=1, le=14)
    notes: str | None = Field(None, max_length=500)


def _hash_edit_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def _require_multi_city_owner(trip_id: str, edit_token: str | None, share_token: str | None = None) -> None:
    expected_hash = await get_multi_city_trip_owner_token_hash(trip_id)
    if expected_hash and edit_token and expected_hash == _hash_edit_token(edit_token):
        return
    share_value = share_token if isinstance(share_token, str) else None
    role = await resolve_share_token(share_value or "", trip_id, TripKind.MULTI_CITY)
    if role and role.value == "editor":
        return
    raise HTTPException(
        status_code=403,
        detail="This multi-city itinerary is read-only. Open it from the browser that created it to make changes.",
    )


async def _record_analytics(event: AnalyticsEventRequest) -> None:
    try:
        await record_analytics(event)
    except Exception:
        return


async def _current_version(trip_id: str) -> int:
    from app.services.collaboration_service import current_version

    return await current_version(trip_id, TripKind.MULTI_CITY)


async def _optional_account_id(account_token: str | None) -> str | None:
    account = await get_account_for_token(account_token)
    return account.id if account else None


@router.post("/generate", response_model=Trip)
async def generate_multi_city(
    request: MultiCityTripRequest,
    response: Response,
    _: None = Depends(generation_rate_limit),
    account_token: str | None = Header(None, alias=ACCOUNT_TOKEN_HEADER),
):
    started = monotonic_ms()
    await _record_analytics(AnalyticsEventRequest(event="planner_started", kind=TripKind.MULTI_CITY))
    await _record_analytics(AnalyticsEventRequest(event="generation_started", kind=TripKind.MULTI_CITY))
    try:
        trip = await generate_multi_city_trip(request)
        edit_token = secrets.token_urlsafe(32)
        trip_id = await save_multi_city_trip(
            trip,
            _hash_edit_token(edit_token),
            await _optional_account_id(account_token),
        )
        trip.id = trip_id
        response.headers[EDIT_TOKEN_HEADER] = edit_token
        await _record_analytics(AnalyticsEventRequest(event="generation_completed", kind=TripKind.MULTI_CITY, trip_id=trip_id, duration_ms=int(monotonic_ms() - started)))
        await _record_analytics(AnalyticsEventRequest(event="planner_completed", kind=TripKind.MULTI_CITY, trip_id=trip_id, duration_ms=int(monotonic_ms() - started)))
        return trip
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        capture_exception(error, context={"operation": "generate_multi_city"})
        await _record_analytics(AnalyticsEventRequest(event="generation_failed", kind=TripKind.MULTI_CITY, duration_ms=int(monotonic_ms() - started)))
        raise HTTPException(status_code=500, detail=safe_error_message(error, "The multi-city planner could not complete this request.")) from error


@router.get("/{trip_id}", response_model=Trip)
async def get_multi_city(trip_id: str, response: Response):
    trip = await get_multi_city_trip(trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Multi-city trip not found")
    response.headers["ETag"] = f'W/"{await _current_version(trip_id)}"'
    return trip


@router.post("/{trip_id}/reorder", response_model=Trip)
async def reorder_multi_city(
    trip_id: str,
    request: ReorderDestinationRequest,
    response: Response,
    edit_token: str | None = Header(None, alias=EDIT_TOKEN_HEADER),
    share_token: str | None = Header(None, alias=SHARE_TOKEN_HEADER),
    if_match: str | None = Header(None, alias="If-Match"),
):
    await _require_multi_city_owner(trip_id, edit_token, share_token)
    trip = await get_multi_city_trip(trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Multi-city trip not found")
    try:
        await assert_version(trip_id, TripKind.MULTI_CITY, if_match)
        updated = await reorder_multi_city_trip(trip, request.destination_stay_ids)
        await update_multi_city_trip(updated)
        response.headers["ETag"] = f'W/"{await _current_version(trip_id)}"'
        return updated
    except VersionConflictError as error:
        raise HTTPException(status_code=409, detail=str(error), headers={"ETag": f'W/"{error.current}"'}) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.patch("/{trip_id}/stays/{stay_id}", response_model=Trip)
async def edit_multi_city_stay(
    trip_id: str,
    stay_id: str,
    request: UpdateDestinationStayRequest,
    response: Response,
    edit_token: str | None = Header(None, alias=EDIT_TOKEN_HEADER),
    share_token: str | None = Header(None, alias=SHARE_TOKEN_HEADER),
    if_match: str | None = Header(None, alias="If-Match"),
):
    await _require_multi_city_owner(trip_id, edit_token, share_token)
    trip = await get_multi_city_trip(trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Multi-city trip not found")
    try:
        await assert_version(trip_id, TripKind.MULTI_CITY, if_match)
        updated = update_multi_city_stay(trip, stay_id, nights=request.nights, notes=request.notes)
        await update_multi_city_trip(updated)
        response.headers["ETag"] = f'W/"{await _current_version(trip_id)}"'
        return updated
    except VersionConflictError as error:
        raise HTTPException(status_code=409, detail=str(error), headers={"ETag": f'W/"{error.current}"'}) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
