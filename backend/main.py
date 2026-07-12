"""
AI Travel Itinerary Planner — FastAPI Backend
Domestic India travel planning powered by Gemini AI, OSM, and free-tier APIs.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("🚀 AI Travel Planner backend starting...")
    logger.info(f"   Gemini API: {'✅ configured' if settings.gemini_api_key else '❌ not set'}")
    logger.info(f"   Skyscanner API: {'✅ configured' if settings.skyscanner_rapidapi_key else '❌ not set'}")
    logger.info(f"   OpenWeatherMap: {'✅ configured' if settings.openweathermap_api_key else '❌ not set'}")
    logger.info(f"   RailRadar API: {'✅ configured' if settings.railradar_api_key else '❌ not set'}")
    logger.info(f"   Supabase: {'✅ configured' if settings.supabase_url else '❌ not set (using in-memory)'}")
    logger.info(f"   Redis: {'✅ configured' if settings.upstash_redis_url else '❌ not set (using in-memory)'}")
    yield
    logger.info("👋 AI Travel Planner shutting down")


app = FastAPI(
    title="AI Travel Itinerary Planner — India",
    description="Generate AI-powered domestic travel itineraries across India",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
from app.api.trips import router as trips_router
from app.api.search import router as search_router
from app.api.transport import router as transport_router

app.include_router(trips_router)
app.include_router(search_router)
app.include_router(transport_router)


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
    return {
        "status": "healthy",
        "services": {
            "gemini": "configured" if settings.gemini_api_key else "not_configured",
            "skyscanner": "configured" if settings.skyscanner_rapidapi_key else "not_configured",
            "weather": "configured" if settings.openweathermap_api_key else "not_configured",
            "railradar": "configured" if settings.railradar_api_key else "not_configured",
            "supabase": "configured" if settings.supabase_url else "in_memory",
            "redis": "configured" if settings.upstash_redis_url else "in_memory",
        },
    }
