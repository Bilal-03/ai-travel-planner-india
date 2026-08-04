"""Phase 2 job lifecycle, replay, idempotency, cancellation, and retry tests."""

from __future__ import annotations

import asyncio
from datetime import date, timedelta
from uuid import uuid4

from app.models.trip import (
    BudgetBreakdown,
    CityInfo,
    GeoPoint,
    Itinerary,
    TripRequest,
)
from app.services import trip_jobs


def _request(day_offset: int = 10) -> TripRequest:
    start = date.today() + timedelta(days=day_offset)
    return TripRequest(
        origin="Delhi",
        destination="Jaipur",
        start_date=start,
        end_date=start,
        budget=10_000,
        members=2,
        planning_notes="heritage places",
    )


def _itinerary(request: TripRequest) -> Itinerary:
    city = CityInfo(
        name="Delhi",
        state="Delhi",
        coordinates=GeoPoint(lat=28.6139, lng=77.2090),
    )
    destination = CityInfo(
        name="Jaipur",
        state="Rajasthan",
        coordinates=GeoPoint(lat=26.9124, lng=75.7873),
    )
    return Itinerary(
        origin=city,
        destination=destination,
        start_date=request.start_date,
        end_date=request.end_date,
        total_days=1,
        members=request.members,
        planning_notes=request.planning_notes,
        budget=BudgetBreakdown(total_estimated=1_000, remaining=9_000),
    )


def _create_job(monkeypatch, request: TripRequest):
    async def no_worker():
        return None

    monkeypatch.setattr(trip_jobs, "ensure_worker_started", no_worker)
    key = f"phase-2-{uuid4()}"
    return asyncio.run(trip_jobs.create_job(request, key))[0]


def test_idempotency_returns_the_same_job_and_events_replay(monkeypatch):
    request = _request(11)

    async def no_worker():
        return None

    monkeypatch.setattr(trip_jobs, "ensure_worker_started", no_worker)
    key = f"phase-2-idempotency-{uuid4()}"
    first, first_replayed = asyncio.run(trip_jobs.create_job(request, key))
    second, second_replayed = asyncio.run(trip_jobs.create_job(request, key))

    events = asyncio.run(trip_jobs.replay_events(first.id, "0"))
    assert not first_replayed
    assert second_replayed
    assert first.id == second.id
    assert events
    assert events[0].status == trip_jobs.TripJobState.ACCEPTED
    assert [event.id for event in events] == sorted(event.id for event in events)


def test_job_worker_retries_a_transient_failure_and_completes(monkeypatch):
    request = _request(12)
    job = _create_job(monkeypatch, request)
    calls = 0

    async def flaky_generate(_request, progress=None):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("temporary provider outage")
        return _itinerary(request)

    async def fake_save(_itinerary, _owner_hash):
        return f"trip-{job.id[:8]}"

    monkeypatch.setattr(trip_jobs, "generate_itinerary", flaky_generate)
    monkeypatch.setattr(trip_jobs, "save_trip", fake_save)

    asyncio.run(trip_jobs._execute_job(job.id))
    result = asyncio.run(trip_jobs.get_job(job.id))

    assert calls == 2
    assert result is not None
    assert result.status == trip_jobs.TripJobState.COMPLETED
    assert result.attempts == 2
    assert result.result_trip_id == f"trip-{job.id[:8]}"


def test_cancellation_is_persisted_and_stops_before_generation(monkeypatch):
    request = _request(13)
    job = _create_job(monkeypatch, request)
    called = False

    async def should_not_generate(_request, progress=None):
        nonlocal called
        called = True
        return _itinerary(request)

    monkeypatch.setattr(trip_jobs, "generate_itinerary", should_not_generate)
    cancelled = asyncio.run(trip_jobs.request_cancellation(job.id))
    asyncio.run(trip_jobs._execute_job(job.id))
    result = asyncio.run(trip_jobs.get_job(job.id))

    assert cancelled is not None and cancelled.cancel_requested
    assert result is not None
    assert result.status == trip_jobs.TripJobState.CANCELLED
    assert not called
    events = asyncio.run(trip_jobs.replay_events(job.id, "0"))
    assert events[-1].status == trip_jobs.TripJobState.CANCELLED


def test_edit_token_is_stable_for_a_job_without_exposing_secret():
    token = trip_jobs.edit_token_for_job("job-123")

    assert token == trip_jobs.edit_token_for_job("job-123")
    assert token.startswith("job-123.")
    assert "trip_job_secret" not in token
