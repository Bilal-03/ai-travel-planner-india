"""HTTP-level coverage for the Phase 2 trip-job lifecycle."""

from __future__ import annotations

import time
from datetime import date, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import trip_jobs as trip_jobs_api
from app.models.trip import BudgetBreakdown, CityInfo, GeoPoint, Itinerary, TripRequest
from app.services import trip_jobs
from main import app


def _request() -> TripRequest:
    start = date.today() + timedelta(days=40)
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
    return Itinerary(
        origin=CityInfo(
            name="Delhi",
            state="Delhi",
            coordinates=GeoPoint(lat=28.6139, lng=77.2090),
        ),
        destination=CityInfo(
            name="Jaipur",
            state="Rajasthan",
            coordinates=GeoPoint(lat=26.9124, lng=75.7873),
        ),
        start_date=request.start_date,
        end_date=request.end_date,
        total_days=1,
        members=request.members,
        planning_notes=request.planning_notes,
        budget=BudgetBreakdown(total_estimated=1_000, remaining=9_000),
    )


def test_trip_job_http_lifecycle(monkeypatch):
    request = _request()
    itinerary = _itinerary(request)
    trip_id = "api-trip-1234"

    async def fake_generate(_request, progress=None):
        if progress:
            await progress("fetching_places", "Finding places…", 35)
            await progress("validating", "Checking your itinerary…", 90)
        return itinerary

    async def fake_save(_itinerary, _owner_hash):
        return trip_id

    async def fake_get_trip(requested_trip_id):
        return itinerary if requested_trip_id == trip_id else None

    monkeypatch.setattr(trip_jobs, "generate_itinerary", fake_generate)
    monkeypatch.setattr(trip_jobs, "save_trip", fake_save)
    monkeypatch.setattr(trip_jobs_api, "get_trip", fake_get_trip)

    idempotency_key = f"phase-2-api-{uuid4()}"
    with TestClient(app) as client:
        created = client.post(
            "/api/trip-jobs",
            json=request.model_dump(mode="json"),
            headers={"Idempotency-Key": idempotency_key},
        )
        assert created.status_code == 202
        job_id = created.json()["id"]

        terminal_status = None
        for _ in range(40):
            snapshot = client.get(f"/api/trip-jobs/{job_id}")
            assert snapshot.status_code == 200
            terminal_status = snapshot.json()["status"]
            if terminal_status in {"completed", "failed", "cancelled"}:
                break
            time.sleep(0.05)

        assert terminal_status == "completed"

        replay = client.get(f"/api/trip-jobs/{job_id}/events")
        assert replay.status_code == 200
        assert "event: progress" in replay.text
        assert "id: 1" in replay.text
        assert "Your itinerary is ready." in replay.text

        result = client.get(f"/api/trip-jobs/{job_id}/result")
        assert result.status_code == 200
        assert result.headers.get("X-Trip-Edit-Token", "").startswith(f"{job_id}.")
        assert result.json()["destination"]["name"] == "Jaipur"

        replayed_submission = client.post(
            "/api/trip-jobs",
            json=request.model_dump(mode="json"),
            headers={"Idempotency-Key": idempotency_key},
        )
        assert replayed_submission.status_code == 202
        assert replayed_submission.json()["id"] == job_id
