"""Durable-ish trip-generation jobs backed by Redis with a local fallback.

The worker keeps the long-running planner out of the request/response cycle.
Redis stores job snapshots, replayable event history, the queue, idempotency
keys, and cancellation flags when configured. The process-local cache fallback
keeps development and tests functional without pretending to be multi-instance
durable.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import AsyncIterator, Optional

from pydantic import BaseModel, Field

from app.cache.redis_cache import get_cache
from app.config import settings
from app.models.trip import Itinerary, TripRequest
from app.services.gemini_planner import generate_itinerary
from app.services.observability import capture_exception, safe_error_message
from app.services.trip_storage import save_trip

logger = logging.getLogger(__name__)

JOB_TTL_SECONDS = 48 * 60 * 60
EVENT_TTL_SECONDS = JOB_TTL_SECONDS
INDEX_TTL_SECONDS = 7 * 24 * 60 * 60
CLAIM_TTL_SECONDS = 15 * 60
TRIP_CACHE_TTL_SECONDS = 60 * 60
MAX_JOB_ATTEMPTS = 2
CONTROLLED_FAILURE_MESSAGE = (
    "The planner could not complete this request after a controlled retry. "
    "Please retry; your completed form is still available."
)
QUEUE_KEY = "travel:trip-jobs:queue"
INDEX_KEY = "travel:trip-jobs:index"


class TripJobState(str, Enum):
    ACCEPTED = "accepted"
    RETRIEVING_DATA = "retrieving_data"
    RESOLVING_LOCATIONS = "resolving_locations"
    FETCHING_TRANSPORT = "fetching_transport"
    FETCHING_PLACES = "fetching_places"
    FETCHING_WEATHER = "fetching_weather"
    OPTIMISING = "optimising"
    GENERATING_NARRATIVE = "generating_narrative"
    VALIDATING = "validating"
    SAVING = "saving"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL_STATES = {
    TripJobState.COMPLETED,
    TripJobState.FAILED,
    TripJobState.CANCELLED,
}


class TripJobRecord(BaseModel):
    """Internal persisted job representation; raw idempotency is never stored."""

    id: str
    idempotency_key_hash: str
    request: TripRequest
    owner_user_id: Optional[str] = None
    status: TripJobState = TripJobState.ACCEPTED
    step: str = TripJobState.ACCEPTED.value
    message: str = "Your trip request was accepted."
    progress: int = Field(0, ge=0, le=100)
    result_trip_id: Optional[str] = None
    error: Optional[str] = None
    attempts: int = 0
    cancel_requested: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None


class TripJobResponse(BaseModel):
    """Public job snapshot returned by the job endpoints."""

    id: str
    status: TripJobState
    step: str
    message: str
    progress: int
    result_trip_id: Optional[str] = None
    error: Optional[str] = None
    attempts: int
    cancel_requested: bool
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


class TripJobEvent(BaseModel):
    """A replayable progress event with a per-job monotonic ID."""

    id: int
    job_id: str
    status: TripJobState
    step: str
    message: str
    progress: int
    timestamp: datetime
    error: Optional[str] = None


class JobCancelled(Exception):
    """Internal control flow used when a cancellation flag is observed."""


def _job_key(job_id: str) -> str:
    return f"travel:trip-job:{job_id}"


def _idempotency_key(key_hash: str) -> str:
    return f"travel:trip-job:idempotency:{key_hash}"


def _event_key(job_id: str) -> str:
    return f"travel:trip-job:{job_id}:events"


def _event_counter_key(job_id: str) -> str:
    return f"travel:trip-job:{job_id}:event-counter"


def _claim_key(job_id: str) -> str:
    return f"travel:trip-job:{job_id}:claim"


def _cancel_key(job_id: str) -> str:
    return f"travel:trip-job:{job_id}:cancel"


def request_cache_key(request: TripRequest) -> str:
    payload = request.model_dump_json(exclude_none=True, round_trip=True)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"trip-generation:{digest}"


def queue_depth() -> int:
    """Expose a bounded operational signal for the readiness/monitoring surface."""

    return len(get_cache().list_range(QUEUE_KEY, 0, -1))


def edit_token_for_job(job_id: str) -> str:
    """Derive a stable owner token without persisting plaintext credentials."""

    secret = settings.trip_job_secret or "yatraai-development-trip-job-secret"
    signature = hmac.new(
        secret.encode("utf-8"),
        job_id.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{job_id}.{signature}"


def hash_edit_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _load_job(job_id: str) -> Optional[TripJobRecord]:
    raw = get_cache().get(_job_key(job_id))
    if not raw:
        return None
    try:
        return TripJobRecord.model_validate_json(raw)
    except ValueError:
        logger.exception("Invalid trip job record in cache: %s", job_id)
        return None


def _save_job(job: TripJobRecord) -> None:
    job.updated_at = datetime.now(timezone.utc)
    get_cache().set(_job_key(job.id), job.model_dump_json(), JOB_TTL_SECONDS)


def to_response(job: TripJobRecord) -> TripJobResponse:
    return TripJobResponse(
        id=job.id,
        status=job.status,
        step=job.step,
        message=job.message,
        progress=job.progress,
        result_trip_id=job.result_trip_id,
        error=job.error,
        attempts=job.attempts,
        cancel_requested=job.cancel_requested,
        created_at=job.created_at,
        updated_at=job.updated_at,
        completed_at=job.completed_at,
    )


async def _publish_event(
    job: TripJobRecord,
    *,
    status: Optional[TripJobState] = None,
    message: Optional[str] = None,
    progress: Optional[int] = None,
    error: Optional[str] = None,
) -> TripJobEvent:
    if status is not None:
        job.status = status
        job.step = status.value
    if message is not None:
        job.message = message
    if progress is not None:
        job.progress = max(0, min(100, progress))
    if error is not None:
        job.error = error
    if job.status in TERMINAL_STATES:
        job.completed_at = datetime.now(timezone.utc)

    _save_job(job)
    cache = get_cache()
    event_id = cache.increment(_event_counter_key(job.id), EVENT_TTL_SECONDS)
    event = TripJobEvent(
        id=event_id,
        job_id=job.id,
        status=job.status,
        step=job.step,
        message=job.message,
        progress=job.progress,
        timestamp=datetime.now(timezone.utc),
        error=job.error,
    )
    cache.list_push(
        _event_key(job.id),
        event.model_dump_json(),
        EVENT_TTL_SECONDS,
    )
    return event


async def get_job(job_id: str) -> Optional[TripJobRecord]:
    return _load_job(job_id)


async def create_job(
    request: TripRequest,
    idempotency_key: str,
    owner_user_id: str | None = None,
) -> tuple[TripJobRecord, bool]:
    """Create one job or return the existing job for the same idempotency key."""

    key_hash = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
    cache = get_cache()
    idempotency_key_name = _idempotency_key(key_hash)
    existing_id = cache.get(idempotency_key_name)
    if existing_id:
        existing = _load_job(existing_id)
        if existing:
            if existing.status not in TERMINAL_STATES:
                await enqueue_job(existing.id)
            await ensure_worker_started()
            return existing, True
        cache.delete(idempotency_key_name)

    job = TripJobRecord(
        id=str(uuid.uuid4()),
        idempotency_key_hash=key_hash,
        request=request,
        owner_user_id=owner_user_id,
    )
    # Write the snapshot before reserving the key. A concurrent retry can
    # then always resolve the winning reservation to a complete job record.
    _save_job(job)
    reserved = cache.set_if_absent(idempotency_key_name, job.id, JOB_TTL_SECONDS)
    if not reserved:
        existing_id = cache.get(idempotency_key_name)
        existing = _load_job(existing_id) if existing_id else None
        if existing:
            if existing.status not in TERMINAL_STATES:
                await enqueue_job(existing.id)
            await ensure_worker_started()
            return existing, True
        # A cache entry can outlive its snapshot during an interrupted write.
        # Remove only that stale reservation, then make one fresh atomic claim.
        cache.delete(idempotency_key_name)
        if not cache.set_if_absent(idempotency_key_name, job.id, JOB_TTL_SECONDS):
            existing_id = cache.get(idempotency_key_name)
            existing = _load_job(existing_id) if existing_id else None
            if existing:
                if existing.status not in TERMINAL_STATES:
                    await enqueue_job(existing.id)
                await ensure_worker_started()
                return existing, True
            raise RuntimeError("Could not reserve the idempotency key")

    cache.list_push(INDEX_KEY, job.id, INDEX_TTL_SECONDS)
    await _publish_event(job)
    await enqueue_job(job.id)
    await ensure_worker_started()
    return job, False


async def enqueue_job(job_id: str) -> None:
    get_cache().list_push(QUEUE_KEY, job_id, JOB_TTL_SECONDS)


async def request_cancellation(job_id: str) -> Optional[TripJobRecord]:
    job = _load_job(job_id)
    if not job:
        return None
    if job.status in TERMINAL_STATES:
        return job

    get_cache().set(_cancel_key(job_id), "1", JOB_TTL_SECONDS)
    job.cancel_requested = True
    await _publish_event(
        job,
        message="Cancellation requested. Finishing the current safe checkpoint…",
    )
    return job


def _cancel_requested(job_id: str) -> bool:
    job = _load_job(job_id)
    return bool(job and job.cancel_requested) or bool(get_cache().get(_cancel_key(job_id)))


async def _raise_if_cancelled(job_id: str) -> None:
    if _cancel_requested(job_id):
        raise JobCancelled


def _mapped_state(step: str) -> TripJobState:
    return {
        "starting": TripJobState.ACCEPTED,
        "geocoding": TripJobState.RESOLVING_LOCATIONS,
        "trip_context": TripJobState.RETRIEVING_DATA,
        "fetching_transport": TripJobState.FETCHING_TRANSPORT,
        "fetching_places": TripJobState.FETCHING_PLACES,
        "fetching_weather": TripJobState.FETCHING_WEATHER,
        "planning": TripJobState.GENERATING_NARRATIVE,
        "validating": TripJobState.VALIDATING,
        "routing": TripJobState.OPTIMISING,
        "saving": TripJobState.SAVING,
        "ready": TripJobState.SAVING,
        "complete": TripJobState.COMPLETED,
        "cached": TripJobState.COMPLETED,
    }.get(step, TripJobState.RETRIEVING_DATA)


async def _generate_with_cancellation(
    job_id: str,
    request: TripRequest,
    progress_callback,
) -> Itinerary:
    task = asyncio.create_task(generate_itinerary(request, progress=progress_callback))
    try:
        while not task.done():
            await asyncio.wait({task}, timeout=0.5)
            if _cancel_requested(job_id):
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                raise JobCancelled
        return await task
    except asyncio.CancelledError:
        if not task.done():
            task.cancel()
        raise


async def _run_generation(job_id: str) -> None:
    job = _load_job(job_id)
    if not job:
        return
    await _raise_if_cancelled(job_id)

    async def progress_callback(step: str, message: str, progress: int) -> None:
        await _raise_if_cancelled(job_id)
        current = _load_job(job_id)
        if not current:
            raise JobCancelled
        await _publish_event(
            current,
            status=_mapped_state(step),
            message=message,
            progress=progress,
        )

    cache = get_cache()
    cached = cache.get(request_cache_key(job.request))
    if cached:
        await _publish_event(
            job,
            status=TripJobState.SAVING,
            message="Saving your matching recent itinerary…",
            progress=92,
        )
        itinerary = Itinerary.model_validate_json(cached)
    else:
        itinerary = await _generate_with_cancellation(
            job_id,
            job.request,
            progress_callback,
        )

    await _raise_if_cancelled(job_id)
    current = _load_job(job_id)
    if not current:
        raise JobCancelled
    await _publish_event(
        current,
        status=TripJobState.SAVING,
        message="Saving your itinerary so it survives refreshes…",
        progress=94,
    )

    edit_token = edit_token_for_job(job_id)
    if job.owner_user_id:
        trip_id = await save_trip(itinerary, hash_edit_token(edit_token), job.owner_user_id)
    else:
        trip_id = await save_trip(itinerary, hash_edit_token(edit_token))
    itinerary.id = trip_id
    if not cached:
        cache.set(
            request_cache_key(job.request),
            itinerary.model_dump_json(),
            TRIP_CACHE_TTL_SECONDS,
        )

    current = _load_job(job_id)
    if not current:
        raise JobCancelled
    current.result_trip_id = trip_id
    await _publish_event(
        current,
        status=TripJobState.COMPLETED,
        message="Your itinerary is ready.",
        progress=100,
    )


async def _execute_job(job_id: str) -> None:
    job = _load_job(job_id)
    if not job or job.status in TERMINAL_STATES:
        return
    if _cancel_requested(job_id):
        current = _load_job(job_id) or job
        await _publish_event(
            current,
            status=TripJobState.CANCELLED,
            message="Generation cancelled.",
            progress=current.progress,
        )
        return

    start_attempt = max(1, min(job.attempts + 1, MAX_JOB_ATTEMPTS))
    for attempt in range(start_attempt, MAX_JOB_ATTEMPTS + 1):
        current = _load_job(job_id)
        if not current:
            return
        current.attempts = attempt
        _save_job(current)
        try:
            await _run_generation(job_id)
            return
        except JobCancelled:
            current = _load_job(job_id) or current
            await _publish_event(
                current,
                status=TripJobState.CANCELLED,
                message="Generation cancelled.",
                progress=current.progress,
            )
            return
        except ValueError as error:
            current = _load_job(job_id) or current
            await _publish_event(
                current,
                status=TripJobState.FAILED,
                message="The trip request could not be completed.",
                progress=current.progress,
                error=safe_error_message(error, "The trip request could not be completed."),
            )
            return
        except Exception as error:
            logger.exception("Trip job %s failed on attempt %s", job_id, attempt)
            capture_exception(error, context={"operation": "trip_job", "job_id": job_id, "attempt": attempt})
            if attempt < MAX_JOB_ATTEMPTS and not _cancel_requested(job_id):
                current = _load_job(job_id) or current
                await _publish_event(
                    current,
                    status=TripJobState.RETRIEVING_DATA,
                    message="A provider interrupted the first attempt. Retrying safely…",
                    progress=max(5, current.progress),
                    error=None,
                )
                continue
            current = _load_job(job_id) or current
            await _publish_event(
                current,
                status=TripJobState.FAILED,
                message="The planner could not complete this request.",
                progress=current.progress,
                error=CONTROLLED_FAILURE_MESSAGE,
            )
            return


async def replay_events(job_id: str, last_event_id: str | None = None) -> list[TripJobEvent]:
    raw_events = get_cache().list_range(_event_key(job_id), 0, -1)
    try:
        last_id = int(last_event_id or 0)
    except ValueError:
        last_id = 0
    events: list[TripJobEvent] = []
    for raw in raw_events:
        try:
            event = TripJobEvent.model_validate_json(raw)
        except ValueError:
            continue
        if event.id > last_id:
            events.append(event)
    return events


async def stream_events(job_id: str, last_event_id: str | None = None) -> AsyncIterator[TripJobEvent]:
    next_event_id = last_event_id
    while True:
        events = await replay_events(job_id, next_event_id)
        for event in events:
            next_event_id = str(event.id)
            yield event
            if event.status in TERMINAL_STATES:
                return

        job = _load_job(job_id)
        if not job:
            return
        if job.status in TERMINAL_STATES:
            return
        await asyncio.sleep(0.5)


async def wait_for_job(job_id: str, timeout_seconds: float = 120.0) -> TripJobRecord:
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    while asyncio.get_running_loop().time() < deadline:
        job = _load_job(job_id)
        if job and job.status in TERMINAL_STATES:
            return job
        await asyncio.sleep(0.25)
    raise TimeoutError(f"Trip job {job_id} did not finish within {timeout_seconds:.0f} seconds")


class TripJobWorker:
    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()
        self._worker_id = str(uuid.uuid4())

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop = asyncio.Event()
        await self._recover_active_jobs()
        self._task = asyncio.create_task(self._run(), name="yatraai-trip-job-worker")

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _recover_active_jobs(self) -> None:
        for job_id in get_cache().list_range(INDEX_KEY, 0, -1):
            job = _load_job(job_id)
            if job and job.status not in TERMINAL_STATES:
                await enqueue_job(job_id)

    async def _run(self) -> None:
        while not self._stop.is_set():
            job_id = get_cache().list_pop_left(QUEUE_KEY)
            if not job_id:
                await asyncio.sleep(0.25)
                continue
            claimed = get_cache().set_if_absent(
                _claim_key(job_id),
                self._worker_id,
                CLAIM_TTL_SECONDS,
            )
            if not claimed:
                continue
            try:
                await _execute_job(job_id)
            finally:
                get_cache().delete(_claim_key(job_id))


_worker = TripJobWorker()


async def ensure_worker_started() -> None:
    await _worker.start()


async def stop_worker() -> None:
    await _worker.stop()


async def recover_jobs() -> None:
    await _worker._recover_active_jobs()
