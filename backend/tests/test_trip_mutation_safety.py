"""Write capabilities and expensive endpoint limits protect shared itineraries."""

import asyncio
import hashlib

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api import trips


def _request(ip: str = "203.0.113.7") -> Request:
    return Request({"type": "http", "method": "POST", "path": "/", "headers": [], "client": (ip, 1234)})


def test_shared_trip_write_requires_creator_edit_capability(monkeypatch):
    token = "creator-only-token"

    async def owner_hash(_trip_id: str):
        return hashlib.sha256(token.encode()).hexdigest()

    monkeypatch.setattr(trips, "get_trip_owner_token_hash", owner_hash)

    asyncio.run(trips.require_trip_owner("shared-trip", edit_token=token))
    with pytest.raises(HTTPException) as denied:
        asyncio.run(trips.require_trip_owner("shared-trip", edit_token="from-a-link"))

    assert denied.value.status_code == 403


def test_generation_rate_limit_returns_retry_after():
    trips._rate_limit_windows.clear()
    request = _request()

    async def exercise_limit():
        for _ in range(5):
            await trips.generation_rate_limit(request)
        with pytest.raises(HTTPException) as limited:
            await trips.generation_rate_limit(request)
        return limited.value

    error = asyncio.run(exercise_limit())
    assert error.status_code == 429
    assert error.headers["Retry-After"]
