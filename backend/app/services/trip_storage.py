"""
Trip storage service — Supabase (Postgres).
Saves and retrieves generated itineraries for sharing.
Falls back to in-memory storage when Supabase is not configured.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Optional

from app.config import settings
from app.models.trip import Itinerary, TripShare

logger = logging.getLogger(__name__)

# In-memory fallback when Supabase is not configured
_memory_store: dict[str, dict] = {}

_supabase_client = None


def _get_supabase():
    """Lazy-init Supabase client."""
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    if not settings.supabase_url or not settings.supabase_key:
        logger.info("ℹ️  No Supabase config — using in-memory trip storage")
        return None

    try:
        from supabase import create_client
        _supabase_client = create_client(settings.supabase_url, settings.supabase_key)
        logger.info("✅ Connected to Supabase")
        return _supabase_client
    except Exception as e:
        logger.warning(f"⚠️  Supabase connection failed: {e}")
        return None


async def save_trip(itinerary: Itinerary) -> str:
    """
    Save an itinerary and return a shareable ID.
    """
    trip_id = str(uuid.uuid4())[:12]
    data = {
        "id": trip_id,
        "itinerary": itinerary.model_dump_json(),
        "created_at": datetime.utcnow().isoformat(),
    }

    client = _get_supabase()
    if client:
        try:
            client.table("trips").insert({
                "id": trip_id,
                "itinerary_json": data["itinerary"],
                "origin": itinerary.origin.name,
                "destination": itinerary.destination.name,
                "start_date": itinerary.start_date.isoformat(),
                "end_date": itinerary.end_date.isoformat(),
                "budget": itinerary.budget.total_estimated,
                "created_at": data["created_at"],
            }).execute()
            logger.info(f"✅ Trip saved to Supabase: {trip_id}")
        except Exception as e:
            logger.error(f"Supabase save failed, using memory: {e}")
            _memory_store[trip_id] = data
    else:
        _memory_store[trip_id] = data

    return trip_id


async def get_trip(trip_id: str) -> Optional[Itinerary]:
    """Retrieve a saved trip by ID."""
    client = _get_supabase()

    if client:
        try:
            result = client.table("trips").select("itinerary_json").eq("id", trip_id).single().execute()
            if result.data:
                return Itinerary.model_validate_json(result.data["itinerary_json"])
        except Exception as e:
            logger.error(f"Supabase get failed: {e}")

    # Fallback to memory
    if trip_id in _memory_store:
        data = _memory_store[trip_id]
        return Itinerary.model_validate_json(data["itinerary"])

    return None
