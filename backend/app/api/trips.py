"""
Trip API routes — main endpoints for generating and sharing itineraries.
"""

import asyncio
import hashlib
import hmac
import json
import logging
import secrets
import time
from collections import defaultdict, deque
from collections.abc import AsyncIterator
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from fastapi.responses import StreamingResponse

from app.cache.redis_cache import get_cache
from app.models.trip import GenerationStatus, Itinerary, PackingItem, TripRequest, TransportMode
from app.services.gemini_planner import (
    generate_itinerary,
    generate_packing_list,
    refine_itinerary,
    select_transport_for_itinerary,
)
from app.services.trip_storage import get_trip, get_trip_owner_token_hash, save_trip, update_trip

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/trips", tags=["trips"])
_progress_queues: dict[str, asyncio.Queue[dict]] = {}
TRIP_CACHE_TTL_SECONDS = 60 * 60
EDIT_TOKEN_HEADER = "X-Trip-Edit-Token"
_rate_limit_windows: dict[tuple[str, str], deque[float]] = defaultdict(deque)
_rate_limit_lock = asyncio.Lock()


class RefineTripRequest(BaseModel):
    instruction: str = Field(..., min_length=3, max_length=500)


class TransportSelectionRequest(BaseModel):
    mode: TransportMode
    provider: str = Field(..., min_length=1)
    code: str | None = None


def _hash_edit_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def _rate_limit(request: Request, scope: str, limit: int, window_seconds: int) -> None:
    """Small in-process guard for expensive AI endpoints.

    Deployments with multiple instances should put this counter in Redis, but a
    local guard still protects each worker and keeps development deterministic.
    """
    client = request.client.host if request.client else "unknown"
    now = time.monotonic()
    key = (scope, client)
    async with _rate_limit_lock:
        attempts = _rate_limit_windows[key]
        while attempts and attempts[0] <= now - window_seconds:
            attempts.popleft()
        if len(attempts) >= limit:
            retry_after = max(1, int(window_seconds - (now - attempts[0])))
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please wait before trying again.",
                headers={"Retry-After": str(retry_after)},
            )
        attempts.append(now)


async def generation_rate_limit(request: Request) -> None:
    await _rate_limit(request, "generate", limit=5, window_seconds=10 * 60)


async def refinement_rate_limit(request: Request) -> None:
    await _rate_limit(request, "refine", limit=10, window_seconds=60 * 60)


async def packing_rate_limit(request: Request) -> None:
    await _rate_limit(request, "packing", limit=10, window_seconds=60 * 60)


async def require_trip_owner(
    trip_id: str,
    edit_token: str | None = Header(None, alias=EDIT_TOKEN_HEADER),
) -> None:
    expected_hash = await get_trip_owner_token_hash(trip_id)
    if not expected_hash or not edit_token or not hmac.compare_digest(expected_hash, _hash_edit_token(edit_token)):
        raise HTTPException(
            status_code=403,
            detail="This shared itinerary is read-only. Open it from the browser that created it to make changes.",
        )


def _request_cache_key(request: TripRequest) -> str:
    payload = request.model_dump_json(exclude_none=True, round_trip=True)
    return f"trip-generation:{hashlib.sha256(payload.encode()).hexdigest()}"


async def _publish_progress(token: str | None, step: str, message: str, progress: int) -> None:
    if not token:
        return
    queue = _progress_queues.setdefault(token, asyncio.Queue())
    await queue.put(GenerationStatus(step=step, message=message, progress=progress).model_dump())


async def _progress_events(token: str) -> AsyncIterator[str]:
    queue = _progress_queues.setdefault(token, asyncio.Queue())
    try:
        while True:
            try:
                update = await asyncio.wait_for(queue.get(), timeout=15)
            except TimeoutError:
                yield ": keep-alive\n\n"
                continue
            yield f"event: progress\ndata: {json.dumps(update, default=str)}\n\n"
            if update["progress"] >= 100 or update["step"] == "failed":
                return
    finally:
        _progress_queues.pop(token, None)


@router.get("/progress/{token}")
async def stream_generation_progress(token: str):
    """Stream real generation milestones for the browser loading UI."""
    return StreamingResponse(
        _progress_events(token),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/generate", response_model=Itinerary)
async def generate_trip(
    request: TripRequest,
    response: Response,
    _: None = Depends(generation_rate_limit),
    progress_token: str | None = Header(None, alias="X-Progress-Token"),
):
    """
    Generate a complete AI-powered itinerary.
    This is the main endpoint — orchestrates all services.
    """
    try:
        await _publish_progress(progress_token, "starting", "Starting your planner request…", 5)
        cache_key = _request_cache_key(request)
        cached = get_cache().get(cache_key)
        if cached:
            itinerary = Itinerary.model_validate_json(cached)
            # A cache hit is a new planning session. Give it its own immutable
            # share record and private write capability instead of reusing an
            # unrelated traveller's saved link.
            edit_token = secrets.token_urlsafe(32)
            trip_id = await save_trip(itinerary, _hash_edit_token(edit_token))
            itinerary.id = trip_id
            response.headers[EDIT_TOKEN_HEADER] = edit_token
            await _publish_progress(progress_token, "cached", "Using your matching recent itinerary.", 100)
            return itinerary
        logger.info(
            f"🚀 Generating trip: {request.origin} → {request.destination}, "
            f"₹{request.budget:,}, {request.start_date} to {request.end_date}"
        )
        itinerary = await generate_itinerary(
            request,
            progress=lambda step, message, progress: _publish_progress(
                progress_token, step, message, progress
            ),
        )

        # Auto-save for sharing
        edit_token = secrets.token_urlsafe(32)
        trip_id = await save_trip(itinerary, _hash_edit_token(edit_token))
        itinerary.id = trip_id
        get_cache().set(cache_key, itinerary.model_dump_json(), TRIP_CACHE_TTL_SECONDS)
        response.headers[EDIT_TOKEN_HEADER] = edit_token
        await _publish_progress(progress_token, "complete", "Your itinerary is ready.", 100)

        return itinerary

    except ValueError as e:
        await _publish_progress(progress_token, "failed", str(e), 100)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Trip generation failed: {e}")
        await _publish_progress(progress_token, "failed", "The planner could not complete this request.", 100)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate itinerary: {str(e)}",
        )


@router.post("/{trip_id}/transport", response_model=Itinerary)
async def select_trip_transport(
    trip_id: str,
    request: TransportSelectionRequest,
    _: None = Depends(require_trip_owner),
):
    """Select the option that is displayed as recommended and budgeted."""
    itinerary = await get_trip(trip_id)
    if not itinerary:
        raise HTTPException(status_code=404, detail="Trip not found")
    try:
        updated = select_transport_for_itinerary(
            itinerary, request.mode, request.provider, request.code
        )
        await update_trip(updated)
        return updated
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


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
async def refine_trip(
    trip_id: str,
    request: RefineTripRequest,
    _: None = Depends(require_trip_owner),
    __: None = Depends(refinement_rate_limit),
):
    """Apply an AI follow-up instruction to a saved itinerary."""
    itinerary = await get_trip(trip_id)
    if not itinerary:
        raise HTTPException(status_code=404, detail="Trip not found")
    refined = await refine_itinerary(itinerary, request.instruction)
    await update_trip(refined)
    return refined


@router.post("/{trip_id}/packing-list", response_model=list[PackingItem])
async def create_packing_list(
    trip_id: str,
    _: None = Depends(require_trip_owner),
    __: None = Depends(packing_rate_limit),
):
    """Generate and persist a destination- and weather-aware packing list."""
    itinerary = await get_trip(trip_id)
    if not itinerary:
        raise HTTPException(status_code=404, detail="Trip not found")
    itinerary.packing_list = await generate_packing_list(itinerary)
    await update_trip(itinerary)
    return itinerary.packing_list
