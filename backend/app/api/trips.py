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
from asyncio import Lock
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from fastapi.responses import StreamingResponse

from app.cache.redis_cache import get_cache
from app.config import settings
from app.models.collaboration import AnalyticsEventRequest, TripKind
from app.models.trip import GenerationStatus, Itinerary, PackingItem, ResearchEvent, TripRequest, TransportMode
from app.services.gemini_planner import (
    generate_itinerary,
    generate_packing_list,
    refine_itinerary,
    select_plan_for_itinerary,
    select_transport_for_itinerary,
)
from app.services.collaboration_service import VersionConflictError, assert_version, record_analytics, resolve_share_token
from app.services.observability import capture_exception, monotonic_ms, safe_error_message
from app.services.research_events import append_unique_events, event_for_failure, event_for_progress, event_for_update
from app.services.trip_storage import get_trip, get_trip_owner_token_hash, save_trip, undo_trip, update_trip

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/trips", tags=["trips"])
_progress_queues: dict[str, asyncio.Queue[dict]] = {}
TRIP_CACHE_TTL_SECONDS = 60 * 60
EDIT_TOKEN_HEADER = "X-Trip-Edit-Token"
SHARE_TOKEN_HEADER = "X-Trip-Share-Token"
_rate_limit_windows: dict[tuple[str, str], deque[float]] = defaultdict(deque)
_rate_limit_lock = Lock()


class RefineTripRequest(BaseModel):
    instruction: str = Field(..., min_length=3, max_length=500)


class TransportSelectionRequest(BaseModel):
    mode: TransportMode
    provider: str = Field(..., min_length=1)
    code: str | None = None


class PlanSelectionRequest(BaseModel):
    plan_id: str = Field(..., min_length=1, max_length=40)


def _hash_edit_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def _rate_limit(request: Request, scope: str, limit: int, window_seconds: int) -> None:
    """Shared Redis-backed guard for expensive endpoints with local fallback."""
    client = request.client.host if request.client else "unknown"
    client_hash = hashlib.sha256(client.encode("utf-8")).hexdigest()[:16]
    now = time.monotonic()
    local_key = (scope, client)
    async with _rate_limit_lock:
        local_attempts = _rate_limit_windows[local_key]
        while local_attempts and local_attempts[0] <= now - window_seconds:
            local_attempts.popleft()
        if len(local_attempts) >= limit:
            retry_after = max(1, int(window_seconds - (now - local_attempts[0])))
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please wait before trying again.",
                headers={"Retry-After": str(retry_after)},
            )
        try:
            attempts = get_cache().increment(
                f"travel:rate-limit:{scope}:{client_hash}",
                ttl_seconds=window_seconds,
                require_distributed=settings.require_redis,
            )
        except RuntimeError as error:
            raise HTTPException(status_code=503, detail="The distributed rate limiter is temporarily unavailable.") from error
        if attempts > limit:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please wait before trying again.",
                headers={"Retry-After": str(window_seconds)},
            )
        local_attempts.append(now)


async def generation_rate_limit(request: Request) -> None:
    await _rate_limit(request, "generate", limit=5, window_seconds=10 * 60)


async def refinement_rate_limit(request: Request) -> None:
    await _rate_limit(request, "refine", limit=10, window_seconds=60 * 60)


async def packing_rate_limit(request: Request) -> None:
    await _rate_limit(request, "packing", limit=10, window_seconds=60 * 60)


async def require_trip_owner(
    trip_id: str,
    edit_token: str | None = Header(None, alias=EDIT_TOKEN_HEADER),
    share_token: str | None = Header(None, alias=SHARE_TOKEN_HEADER),
) -> None:
    expected_hash = await get_trip_owner_token_hash(trip_id)
    if expected_hash and edit_token and hmac.compare_digest(expected_hash, _hash_edit_token(edit_token)):
        return
    share_value = share_token if isinstance(share_token, str) else None
    role = await resolve_share_token(share_value or "", trip_id, TripKind.SINGLE)
    if role and role.value == "editor":
        return
    raise HTTPException(
        status_code=403,
        detail="This shared itinerary is read-only. Open it from the browser that created it to make changes.",
    )


async def _record_analytics(event: AnalyticsEventRequest) -> None:
    try:
        await record_analytics(event)
    except Exception:
        logger.debug("Product analytics was unavailable", exc_info=True)


async def _current_version(trip_id: str) -> int:
    from app.services.collaboration_service import current_version

    return await current_version(trip_id, TripKind.SINGLE)


def _request_cache_key(request: TripRequest) -> str:
    payload = request.model_dump_json(exclude_none=True, round_trip=True)
    return f"trip-generation:{hashlib.sha256(payload.encode()).hexdigest()}"


async def _publish_progress(
    token: str | None,
    step: str,
    message: str,
    progress: int,
    research_event: ResearchEvent | None = None,
) -> None:
    if not token:
        return
    queue = _progress_queues.setdefault(token, asyncio.Queue())
    await queue.put(GenerationStatus(
        step=step,
        message=message,
        progress=progress,
        research_event=research_event,
    ).model_dump())


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
    started = monotonic_ms()
    await _record_analytics(AnalyticsEventRequest(event="planner_started", kind=TripKind.SINGLE))
    await _record_analytics(AnalyticsEventRequest(event="generation_started", kind=TripKind.SINGLE))
    try:
        research_events: list[ResearchEvent] = []

        async def report(step: str, message: str, progress: int) -> None:
            research_event = event_for_progress(step, message)
            research_events.append(research_event)
            await _publish_progress(progress_token, step, message, progress, research_event)

        await report("starting", "Starting your planner request…", 5)
        cache_key = _request_cache_key(request)
        cached = get_cache().get(cache_key)
        if cached:
            itinerary = Itinerary.model_validate_json(cached)
            cached_event = event_for_progress("cached", "Using your matching recent itinerary.")
            completed_event = event_for_progress("complete", "Your itinerary is ready.")
            itinerary.research_events = append_unique_events(
                itinerary.research_events,
                [*research_events, cached_event, completed_event],
            )
            # A cache hit is a new planning session. Give it its own immutable
            # share record and private write capability instead of reusing an
            # unrelated traveller's saved link.
            edit_token = secrets.token_urlsafe(32)
            trip_id = await save_trip(itinerary, _hash_edit_token(edit_token))
            itinerary.id = trip_id
            response.headers[EDIT_TOKEN_HEADER] = edit_token
            await _publish_progress(progress_token, "cached", "Using your matching recent itinerary.", 100, completed_event)
            await _record_analytics(AnalyticsEventRequest(event="generation_completed", kind=TripKind.SINGLE, duration_ms=int(monotonic_ms() - started), metadata={"source": "cache"}))
            await _record_analytics(AnalyticsEventRequest(event="planner_completed", kind=TripKind.SINGLE, duration_ms=int(monotonic_ms() - started), metadata={"source": "cache"}))
            return itinerary
        logger.info(
            f"🚀 Generating trip: {request.origin} → {request.destination}, "
            f"₹{request.budget:,}, {request.start_date} to {request.end_date}"
        )
        itinerary = await generate_itinerary(
            request,
            progress=report,
        )

        completed_event = event_for_progress("complete", "Your itinerary is ready.")
        itinerary.research_events = append_unique_events(
            itinerary.research_events,
            [*research_events, completed_event],
        )
        # Auto-save for sharing
        edit_token = secrets.token_urlsafe(32)
        trip_id = await save_trip(itinerary, _hash_edit_token(edit_token))
        itinerary.id = trip_id
        get_cache().set(cache_key, itinerary.model_dump_json(), TRIP_CACHE_TTL_SECONDS)
        response.headers[EDIT_TOKEN_HEADER] = edit_token
        await _publish_progress(progress_token, "complete", "Your itinerary is ready.", 100, completed_event)
        await _record_analytics(AnalyticsEventRequest(event="generation_completed", kind=TripKind.SINGLE, trip_id=trip_id, duration_ms=int(monotonic_ms() - started), metadata={"estimated_data": any(option.is_fallback for option in itinerary.transport_options)}))
        await _record_analytics(AnalyticsEventRequest(event="planner_completed", kind=TripKind.SINGLE, trip_id=trip_id, duration_ms=int(monotonic_ms() - started)))

        return itinerary

    except ValueError as e:
        await _publish_progress(progress_token, "failed", str(e), 100, event_for_failure(str(e)))
        await _record_analytics(AnalyticsEventRequest(event="generation_failed", kind=TripKind.SINGLE, duration_ms=int(monotonic_ms() - started), metadata={"invalid_itinerary": True}))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Trip generation failed: {e}")
        capture_exception(e, context={"operation": "generate_trip"})
        await _publish_progress(
            progress_token,
            "failed",
            "The planner could not complete this request.",
            100,
            event_for_failure("The planner could not complete this request."),
        )
        await _record_analytics(AnalyticsEventRequest(event="generation_failed", kind=TripKind.SINGLE, duration_ms=int(monotonic_ms() - started)))
        raise HTTPException(
            status_code=500,
            detail=safe_error_message(e, "Failed to generate itinerary. Please try again."),
        )


@router.post("/{trip_id}/transport", response_model=Itinerary)
async def select_trip_transport(
    trip_id: str,
    request: TransportSelectionRequest,
    response: Response,
    if_match: str | None = Header(None, alias="If-Match"),
    _: None = Depends(require_trip_owner),
):
    """Select the option that is displayed as recommended and budgeted."""
    itinerary = await get_trip(trip_id)
    if not itinerary:
        raise HTTPException(status_code=404, detail="Trip not found")
    try:
        await assert_version(trip_id, TripKind.SINGLE, if_match)
        updated = select_transport_for_itinerary(
            itinerary, request.mode, request.provider, request.code
        )
        await update_trip(updated)
        await _record_analytics(AnalyticsEventRequest(event="transport_selected", kind=TripKind.SINGLE, trip_id=trip_id, metadata={"provider": request.provider}))
        response.headers["ETag"] = f'W/"{await _current_version(trip_id)}"'
        return updated
    except VersionConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc), headers={"ETag": f'W/"{exc.current}"'}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{trip_id}/plan", response_model=Itinerary)
async def select_trip_plan(
    trip_id: str,
    request: PlanSelectionRequest,
    response: Response,
    if_match: str | None = Header(None, alias="If-Match"),
    _: None = Depends(require_trip_owner),
):
    """Select one of the generated itinerary alternatives."""
    itinerary = await get_trip(trip_id)
    if not itinerary:
        raise HTTPException(status_code=404, detail="Trip not found")
    try:
        await assert_version(trip_id, TripKind.SINGLE, if_match)
        updated = select_plan_for_itinerary(itinerary, request.plan_id)
        await update_trip(updated)
        await _record_analytics(AnalyticsEventRequest(
            event="plan_selected",
            kind=TripKind.SINGLE,
            trip_id=trip_id,
            metadata={"plan_id": request.plan_id},
        ))
        response.headers["ETag"] = f'W/"{await _current_version(trip_id)}"'
        return updated
    except VersionConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc), headers={"ETag": f'W/"{exc.current}"'}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{trip_id}", response_model=Itinerary)
async def get_trip_by_id(trip_id: str, response: Response):
    """Retrieve a saved/shared trip by ID."""
    itinerary = await get_trip(trip_id)
    if not itinerary:
        raise HTTPException(status_code=404, detail="Trip not found")
    response.headers["ETag"] = f'W/"{await _current_version(trip_id)}"'
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
    response: Response,
    if_match: str | None = Header(None, alias="If-Match"),
    _: None = Depends(require_trip_owner),
    __: None = Depends(refinement_rate_limit),
):
    """Apply an AI follow-up instruction to a saved itinerary."""
    itinerary = await get_trip(trip_id)
    if not itinerary:
        raise HTTPException(status_code=404, detail="Trip not found")
    try:
        await assert_version(trip_id, TripKind.SINGLE, if_match)
    except VersionConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc), headers={"ETag": f'W/"{exc.current}"'}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    refined = await refine_itinerary(itinerary, request.instruction)
    refined.places = itinerary.places
    refined.items = itinerary.items
    refined.sources = itinerary.sources
    refined.research_events = append_unique_events(
        itinerary.research_events,
        [event_for_update(request.instruction)],
    )
    await update_trip(refined)
    lower_instruction = request.instruction.casefold()
    if "replace" in lower_instruction:
        await _record_analytics(AnalyticsEventRequest(event="activity_replaced", kind=TripKind.SINGLE, trip_id=trip_id, metadata={"accepted": True}))
    if "regenerate day" in lower_instruction:
        await _record_analytics(AnalyticsEventRequest(event="day_regenerated", kind=TripKind.SINGLE, trip_id=trip_id, metadata={"accepted": True}))
    response.headers["ETag"] = f'W/"{await _current_version(trip_id)}"'
    return refined


@router.post("/{trip_id}/undo", response_model=Itinerary)
async def undo_trip_change(
    trip_id: str,
    response: Response,
    if_match: str | None = Header(None, alias="If-Match"),
    _: None = Depends(require_trip_owner),
):
    """Restore the previous server-validated itinerary revision."""
    try:
        await assert_version(trip_id, TripKind.SINGLE, if_match)
    except VersionConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc), headers={"ETag": f'W/"{exc.current}"'}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    restored = await undo_trip(trip_id)
    if not restored:
        raise HTTPException(status_code=409, detail="There is no previous trip version to restore.")
    response.headers["ETag"] = f'W/"{await _current_version(trip_id)}"'
    return restored


@router.post("/{trip_id}/packing-list", response_model=list[PackingItem])
async def create_packing_list(
    trip_id: str,
    response: Response,
    if_match: str | None = Header(None, alias="If-Match"),
    _: None = Depends(require_trip_owner),
    __: None = Depends(packing_rate_limit),
):
    """Generate and persist a destination- and weather-aware packing list."""
    itinerary = await get_trip(trip_id)
    if not itinerary:
        raise HTTPException(status_code=404, detail="Trip not found")
    try:
        await assert_version(trip_id, TripKind.SINGLE, if_match)
    except VersionConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc), headers={"ETag": f'W/"{exc.current}"'}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    itinerary.packing_list = await generate_packing_list(itinerary)
    await update_trip(itinerary)
    response.headers["ETag"] = f'W/"{await _current_version(trip_id)}"'
    return itinerary.packing_list
