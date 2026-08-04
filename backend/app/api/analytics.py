"""Privacy-safe product analytics ingestion."""

from __future__ import annotations

import hashlib

from fastapi import APIRouter, HTTPException, Request

from app.cache.redis_cache import get_cache
from app.config import settings
from app.models.collaboration import AnalyticsEventRequest
from app.services.collaboration_service import record_analytics

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


async def _limit_ingestion(request: Request) -> None:
    client = request.client.host if request.client else "unknown"
    digest = hashlib.sha256(client.encode()).hexdigest()[:20]
    try:
        count = get_cache().increment(
            f"travel:analytics-rate:{digest}",
            ttl_seconds=60,
            require_distributed=settings.require_redis,
        )
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail="The distributed rate limiter is temporarily unavailable.") from error
    if count > 120:
        raise HTTPException(status_code=429, detail="Analytics rate limit exceeded")


@router.post("/events", status_code=202)
async def ingest_event(event: AnalyticsEventRequest, request: Request):
    await _limit_ingestion(request)
    try:
        await record_analytics(event, client_id=request.client.host if request.client else None)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"accepted": True}
