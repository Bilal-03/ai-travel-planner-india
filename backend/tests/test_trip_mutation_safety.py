"""Write capabilities and expensive endpoint limits protect shared itineraries."""

import asyncio
import hashlib

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api import trips


def _request(ip: str = "203.0.113.7", client_id: str | None = None) -> Request:
    headers = [(b"x-yatraai-client-id", client_id.encode())] if client_id else []
    return Request({"type": "http", "method": "POST", "path": "/", "headers": headers, "client": (ip, 1234)})


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


def test_generation_rate_limit_separates_browser_identity_behind_shared_proxy():
    trips._rate_limit_windows.clear()
    browser_a = _request(client_id="test-browser-a-0001")
    browser_b = _request(client_id="test-browser-b-0001")

    async def exercise_limit():
        for _ in range(5):
            await trips.generation_rate_limit(browser_a)
        await trips.generation_rate_limit(browser_b)

    asyncio.run(exercise_limit())


def test_clarification_rate_limit_does_not_consume_generation_quota():
    trips._rate_limit_windows.clear()
    request = _request(client_id="test-clarify-client-01")

    async def exercise_limits():
        for _ in range(5):
            await trips.generation_rate_limit(request)
        for _ in range(6):
            await trips.clarification_rate_limit(request)

    asyncio.run(exercise_limits())
