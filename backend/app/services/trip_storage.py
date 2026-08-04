"""Trip storage service — Neon-compatible PostgreSQL with in-memory fallback."""

import asyncio
import logging
import threading
import uuid
from datetime import datetime
from typing import Optional

from app.config import settings
from app.models.trip import Itinerary

logger = logging.getLogger(__name__)
_memory_store: dict[str, dict] = {}
_schema_ready = False
_schema_lock = threading.Lock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS trips (
    id VARCHAR(12) PRIMARY KEY,
    itinerary_json JSONB NOT NULL,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    budget INTEGER NOT NULL,
    owner_token_hash TEXT,
    previous_itinerary_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""


def _connect():
    """Open a short-lived connection; Neon pooling handles reuse upstream."""
    if not settings.database_url:
        return None
    import psycopg
    return psycopg.connect(settings.database_url, connect_timeout=10, autocommit=True)


def _ensure_schema_sync() -> bool:
    global _schema_ready
    if _schema_ready:
        return True
    with _schema_lock:
        if _schema_ready:
            return True
        try:
            with _connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(_SCHEMA)
                    # Existing installations predate edit-token protection.
                    # Keep this migration additive so shared links remain readable.
                    cursor.execute("ALTER TABLE trips ADD COLUMN IF NOT EXISTS owner_token_hash TEXT")
                    cursor.execute("ALTER TABLE trips ADD COLUMN IF NOT EXISTS previous_itinerary_json JSONB")
            _schema_ready = True
            logger.info("Connected to Neon PostgreSQL; trips table is ready")
            return True
        except Exception as error:
            logger.warning("Neon setup failed; using in-memory trips: %s", error)
            return False


async def _ensure_schema() -> bool:
    return bool(settings.database_url) and await asyncio.to_thread(_ensure_schema_sync)


async def save_trip(itinerary: Itinerary, owner_token_hash: str | None = None) -> str:
    """Save an itinerary and return its stable, shareable ID."""
    trip_id = str(uuid.uuid4())[:12]
    itinerary.id = trip_id
    data = itinerary.model_dump_json()
    created_at = datetime.utcnow().isoformat()
    if await _ensure_schema():
        try:
            def insert() -> None:
                with _connect() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            """INSERT INTO trips (id, itinerary_json, origin, destination, start_date, end_date, budget, owner_token_hash, previous_itinerary_json, created_at)
                            VALUES (%s, %s::jsonb, %s, %s, %s, %s, %s, %s, NULL, %s)""",
                            (trip_id, data, itinerary.origin.name, itinerary.destination.name,
                             itinerary.start_date, itinerary.end_date, itinerary.budget.total_estimated,
                             owner_token_hash, created_at),
                        )
            await asyncio.to_thread(insert)
            return trip_id
        except Exception as error:
            logger.error("Neon save failed; using memory: %s", error)
    _memory_store[trip_id] = {
        "itinerary": data,
        "previous_itinerary": None,
        "owner_token_hash": owner_token_hash,
        "created_at": created_at,
    }
    return trip_id


async def get_trip(trip_id: str) -> Optional[Itinerary]:
    """Retrieve a saved itinerary from Neon or the local fallback."""
    if await _ensure_schema():
        try:
            def fetch() -> Optional[str]:
                with _connect() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT itinerary_json::text FROM trips WHERE id = %s", (trip_id,))
                        row = cursor.fetchone()
                        return row[0] if row else None
            data = await asyncio.to_thread(fetch)
            if data:
                return Itinerary.model_validate_json(data)
        except Exception as error:
            logger.error("Neon read failed: %s", error)
    cached = _memory_store.get(trip_id)
    return Itinerary.model_validate_json(cached["itinerary"]) if cached else None


async def get_trip_owner_token_hash(trip_id: str) -> Optional[str]:
    """Return the write capability hash without ever including it in shared JSON."""
    if await _ensure_schema():
        try:
            def fetch() -> Optional[str]:
                with _connect() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT owner_token_hash FROM trips WHERE id = %s", (trip_id,))
                        row = cursor.fetchone()
                        return row[0] if row else None
            return await asyncio.to_thread(fetch)
        except Exception as error:
            logger.error("Neon owner-token lookup failed; using memory: %s", error)
    cached = _memory_store.get(trip_id)
    return cached.get("owner_token_hash") if cached else None


async def update_trip(itinerary: Itinerary) -> None:
    """Persist refinements and packing-list changes without changing the share URL."""
    data = itinerary.model_dump_json()
    if await _ensure_schema():
        try:
            def update() -> None:
                with _connect() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute("UPDATE trips SET previous_itinerary_json = itinerary_json, itinerary_json = %s::jsonb, budget = %s WHERE id = %s", (data, itinerary.budget.total_estimated, itinerary.id))
            await asyncio.to_thread(update)
            return
        except Exception as error:
            logger.error("Neon update failed; using memory: %s", error)
    existing = _memory_store.get(itinerary.id, {})
    _memory_store[itinerary.id] = {
        "itinerary": data,
        "previous_itinerary": existing.get("itinerary"),
        "owner_token_hash": existing.get("owner_token_hash"),
        "created_at": datetime.utcnow().isoformat(),
    }


async def undo_trip(trip_id: str) -> Optional[Itinerary]:
    """Restore the last server-saved version of a trip, if one exists."""
    if await _ensure_schema():
        try:
            def swap() -> bool:
                with _connect() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            """UPDATE trips
                            SET itinerary_json = previous_itinerary_json,
                                previous_itinerary_json = itinerary_json
                            WHERE id = %s AND previous_itinerary_json IS NOT NULL""",
                            (trip_id,),
                        )
                        return cursor.rowcount > 0
            if await asyncio.to_thread(swap):
                return await get_trip(trip_id)
        except Exception as error:
            logger.error("Neon undo failed; using memory: %s", error)

    existing = _memory_store.get(trip_id)
    if not existing or not existing.get("previous_itinerary"):
        return None
    current = existing["itinerary"]
    existing["itinerary"] = existing["previous_itinerary"]
    existing["previous_itinerary"] = current
    return Itinerary.model_validate_json(existing["itinerary"])
