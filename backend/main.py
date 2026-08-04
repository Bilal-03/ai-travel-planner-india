"""
AI Travel Itinerary Planner — FastAPI Backend
Domestic India travel planning powered by Gemini AI, OSM, and free-tier APIs.
"""

import hmac
import logging
import re
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.cache.redis_cache import get_cache
from app.providers.gateway import get_provider_gateway
from app.services.collaboration_service import ensure_collaboration_storage_ready
from app.services.observability import (
    configure_observability,
    request_span,
    reset_request_context,
    set_request_context,
)
from app.services.trip_jobs import ensure_worker_started, queue_depth, stop_worker
from app.services.trip_storage import ensure_durable_storage_ready

configure_observability()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("🚀 AI Travel Planner backend starting...")
    await ensure_durable_storage_ready()
    await ensure_collaboration_storage_ready()
    if settings.require_redis and not get_cache().is_distributed:
        raise RuntimeError("REQUIRE_REDIS is enabled but Redis is unavailable")
    logger.info(f"   Gemini API: {'✅ configured' if settings.gemini_api_key else '❌ not set'}")
    logger.info(f"   Skyscanner API: {'✅ configured' if settings.skyscanner_rapidapi_key else '❌ not set'}")
    logger.info(f"   OpenWeatherMap: {'✅ configured' if settings.openweathermap_api_key else '❌ not set'}")
    logger.info(f"   RailRadar API: {'✅ configured' if settings.railradar_api_key else '❌ not set'}")
    logger.info(f"   Provider gateway: {get_provider_gateway().selected_providers()}")
    logger.info(f"   Neon PostgreSQL: {'✅ configured' if settings.database_url else '❌ not set (using in-memory)'}")
    logger.info(f"   Redis: {'✅ configured' if settings.upstash_redis_url else '❌ not set (using in-memory)'}")
    await ensure_worker_started()
    yield
    await stop_worker()
    logger.info("👋 AI Travel Planner shutting down")


app = FastAPI(
    title="AI Travel Itinerary Planner — India",
    description="Generate AI-powered domestic travel itineraries across India",
    version="1.0.0",
    lifespan=lifespan,
)


def _job_id_from_path(path: str) -> str:
    if not path.startswith("/api/trip-jobs/"):
        return "-"
    value = path.removeprefix("/api/trip-jobs/").split("/", 1)[0]
    return value[:80] or "-"


@app.middleware("http")
async def production_boundary(request: Request, call_next):
    """Attach correlation IDs and enforce request-size/bot guardrails."""

    request_id = request.headers.get("X-Request-ID", "")
    if not re.fullmatch(r"[A-Za-z0-9._:-]{8,80}", request_id):
        request_id = str(uuid.uuid4())
    job_id = _job_id_from_path(request.url.path)
    tokens = set_request_context(request_id, job_id)
    try:
        mutating = request.method in {"POST", "PUT", "PATCH", "DELETE"}
        content_length = request.headers.get("content-length")
        if content_length and content_length.isdigit() and int(content_length) > settings.max_request_body_bytes:
            return JSONResponse(
                status_code=413,
                content={"detail": "Request body is too large."},
                headers={"X-Request-ID": request_id},
            )

        # Chunked requests do not carry Content-Length; read those bounded
        # mutation bodies before dispatch so the limit cannot be bypassed.
        if mutating and not content_length:
            body = await request.body()
            if len(body) > settings.max_request_body_bytes:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Request body is too large."},
                    headers={"X-Request-ID": request_id},
                )

        protected_path = not request.url.path.startswith(("/health", "/docs", "/openapi.json", "/api/analytics/events"))
        if settings.bot_protection_token and mutating and protected_path:
            supplied = request.headers.get("X-Yatra-Bot-Token", "")
            if not hmac.compare_digest(supplied, settings.bot_protection_token):
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Bot protection verification failed."},
                    headers={"X-Request-ID": request_id},
                )

        with request_span(f"{request.method} {request.url.path}"):
            response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        if job_id != "-":
            response.headers["X-Trip-Job-ID"] = job_id
        return response
    finally:
        reset_request_context(tokens)

# CORS — allow frontend
allowed_origins = {settings.frontend_url.rstrip("/")}
if not settings.is_production:
    allowed_origins.update({"http://localhost:3000", "http://localhost:3001"})
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(allowed_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Accept",
        "Content-Type",
        "Idempotency-Key",
        "If-Match",
        "Last-Event-ID",
        "X-Progress-Token",
        "X-Request-ID",
        "X-Trip-Edit-Token",
        "X-Trip-Share-Token",
        "X-Yatra-Bot-Token",
    ],
    expose_headers=["X-Request-ID", "X-Trip-Job-ID", "X-Trip-Edit-Token", "ETag"],
)

# Register routers
from app.api.trips import router as trips_router
from app.api.search import router as search_router
from app.api.transport import router as transport_router
from app.api.trip_jobs import router as trip_jobs_router
from app.api.multi_city import router as multi_city_router
from app.api.analytics import router as analytics_router
from app.api.collaboration import router as collaboration_router

app.include_router(trips_router)
app.include_router(search_router)
app.include_router(transport_router)
app.include_router(trip_jobs_router)
app.include_router(multi_city_router)
app.include_router(analytics_router)
app.include_router(collaboration_router)


@app.get("/")
async def root():
    return {
        "name": "AI Travel Itinerary Planner — India",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    durable_ready = True
    if settings.require_durable_storage:
        try:
            await ensure_durable_storage_ready()
            await ensure_collaboration_storage_ready()
        except RuntimeError:
            durable_ready = False
    redis_status = get_cache().health()
    ready = durable_ready and (not settings.require_redis or redis_status == "redis")
    payload = {
        "status": "healthy" if ready else "not_ready",
        "ready": ready,
        "services": {
            "gemini": "configured" if settings.gemini_api_key else "not_configured",
            "skyscanner": "configured" if settings.skyscanner_rapidapi_key else "not_configured",
            "weather": "configured" if settings.openweathermap_api_key else "not_configured",
            "railradar": "configured" if settings.railradar_api_key else "not_configured",
            "provider_selection": get_provider_gateway().selected_providers(),
            "database": "neon" if settings.database_url else "in_memory",
            "redis": redis_status,
            "durable_storage_required": settings.require_durable_storage,
            "environment": settings.environment,
            "job_queue": {"pending": queue_depth()},
        },
    }
    if not ready:
        return JSONResponse(status_code=503, content=payload)
    return payload
