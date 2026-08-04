"""Asynchronous, replayable trip-generation job endpoints."""

import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from fastapi.responses import JSONResponse, StreamingResponse

from app.api.trips import generation_rate_limit
from app.models.trip import TripRequest
from app.services.account_service import get_account_for_token
from app.services.trip_jobs import (
    TERMINAL_STATES,
    TripJobState,
    TripJobResponse,
    create_job,
    edit_token_for_job,
    get_job,
    request_cancellation,
    stream_events,
    to_response,
)
from app.services.trip_storage import get_trip

router = APIRouter(prefix="/api/trip-jobs", tags=["trip-jobs"])
IDEMPOTENCY_HEADER = "Idempotency-Key"
EDIT_TOKEN_HEADER = "X-Trip-Edit-Token"
ACCOUNT_TOKEN_HEADER = "X-Yatra-Account-Token"


@router.post("", response_model=TripJobResponse, status_code=202)
async def submit_trip_job(
    request: TripRequest,
    idempotency_key: str | None = Header(None, alias=IDEMPOTENCY_HEADER),
    _: None = Depends(generation_rate_limit),
    account_token: str | None = Header(None, alias=ACCOUNT_TOKEN_HEADER),
):
    """Accept a generation request and return immediately with a job ID."""

    # The frontend always supplies a stable key before sending the request.
    # Generate one for older API clients so they remain compatible, while
    # clearly documenting that retries without a key are new submissions.
    key = (idempotency_key or str(uuid.uuid4())).strip()
    if not 8 <= len(key) <= 200:
        raise HTTPException(status_code=400, detail="Idempotency-Key must be between 8 and 200 characters")
    account = await get_account_for_token(account_token)
    job, _ = await create_job(request, key, account.id if account else None)
    return to_response(job)


@router.get("/{job_id}", response_model=TripJobResponse)
async def get_trip_job(job_id: str):
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Trip job not found")
    return to_response(job)


@router.get("/{job_id}/events")
async def stream_trip_job_events(
    job_id: str,
    last_event_id: str | None = Query(None, alias="last_event_id"),
    last_event_header: str | None = Header(None, alias="Last-Event-ID"),
):
    """Replay missed events, then keep the SSE connection live until terminal."""

    if not await get_job(job_id):
        raise HTTPException(status_code=404, detail="Trip job not found")
    cursor = last_event_header or last_event_id

    async def events() -> AsyncIterator[str]:
        async for event in stream_events(job_id, cursor):
            yield (
                f"id: {event.id}\n"
                "event: progress\n"
                f"data: {event.model_dump_json()}\n\n"
            )

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{job_id}/cancel", response_model=TripJobResponse, status_code=202)
async def cancel_trip_job(job_id: str):
    job = await request_cancellation(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Trip job not found")
    return to_response(job)


@router.get("/{job_id}/result")
async def get_trip_job_result(job_id: str, response: Response):
    """Return the saved itinerary once the job has completed."""

    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Trip job not found")
    if job.status != TripJobState.COMPLETED:
        if job.status in TERMINAL_STATES:
            raise HTTPException(status_code=409, detail=job.error or job.message)
        return JSONResponse(status_code=202, content=to_response(job).model_dump(mode="json"))
    if not job.result_trip_id:
        raise HTTPException(status_code=500, detail="Trip job completed without a saved result")

    itinerary = await get_trip(job.result_trip_id)
    if not itinerary:
        raise HTTPException(status_code=404, detail="Saved itinerary result not found")
    response.headers[EDIT_TOKEN_HEADER] = edit_token_for_job(job_id)
    return itinerary
