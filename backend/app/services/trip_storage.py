"""Trip storage service — Neon-compatible PostgreSQL with in-memory fallback."""

import asyncio
import json
import logging
import threading
import uuid
from datetime import datetime
from typing import Optional

from app.config import settings
from app.models.collaboration import TripKind
from app.models.trip import Itinerary, Trip
from app.services.collaboration_service import record_trip_version

logger = logging.getLogger(__name__)
_memory_store: dict[str, dict] = {}
_memory_multi_city_store: dict[str, dict] = {}
_schema_ready = False
_schema_lock = threading.Lock()


def _fallback_or_raise(operation: str) -> None:
    """Production must fail closed when durable storage is unavailable."""

    if settings.require_durable_storage:
        raise RuntimeError(f"Durable storage is unavailable during {operation}")

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

_MULTI_CITY_SCHEMA = """
CREATE TABLE IF NOT EXISTS multi_city_trips (
    id VARCHAR(12) PRIMARY KEY,
    trip_json JSONB NOT NULL,
    origin TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    budget INTEGER NOT NULL,
    owner_token_hash TEXT,
    previous_trip_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS multi_city_destination_stays (
    trip_id VARCHAR(12) NOT NULL REFERENCES multi_city_trips(id) ON DELETE CASCADE,
    stay_id VARCHAR(64) NOT NULL,
    position INTEGER NOT NULL,
    city_json JSONB NOT NULL,
    arrival_date DATE NOT NULL,
    departure_date DATE NOT NULL,
    nights INTEGER NOT NULL,
    notes TEXT,
    provenance_json JSONB NOT NULL,
    PRIMARY KEY (trip_id, stay_id)
);
CREATE TABLE IF NOT EXISTS multi_city_travel_legs (
    trip_id VARCHAR(12) NOT NULL REFERENCES multi_city_trips(id) ON DELETE CASCADE,
    leg_id VARCHAR(64) NOT NULL,
    leg_position INTEGER NOT NULL,
    origin_json JSONB NOT NULL,
    destination_json JSONB NOT NULL,
    travel_date DATE NOT NULL,
    mode TEXT NOT NULL,
    selected_offer_json JSONB,
    alternatives_json JSONB NOT NULL,
    duration_minutes INTEGER NOT NULL,
    fare INTEGER NOT NULL,
    provenance_json JSONB NOT NULL,
    PRIMARY KEY (trip_id, leg_id)
);
CREATE TABLE IF NOT EXISTS multi_city_visits (
    trip_id VARCHAR(12) NOT NULL REFERENCES multi_city_trips(id) ON DELETE CASCADE,
    visit_id VARCHAR(64) NOT NULL,
    stay_id VARCHAR(64) NOT NULL,
    visit_date DATE NOT NULL,
    visit_json JSONB NOT NULL,
    PRIMARY KEY (trip_id, visit_id)
);
CREATE TABLE IF NOT EXISTS multi_city_itinerary_days (
    trip_id VARCHAR(12) NOT NULL REFERENCES multi_city_trips(id) ON DELETE CASCADE,
    day_number INTEGER NOT NULL,
    day_date DATE NOT NULL,
    day_json JSONB NOT NULL,
    PRIMARY KEY (trip_id, day_number)
);
CREATE TABLE IF NOT EXISTS multi_city_transport_selections (
    trip_id VARCHAR(12) NOT NULL REFERENCES multi_city_trips(id) ON DELETE CASCADE,
    leg_id VARCHAR(64) NOT NULL,
    selection_json JSONB NOT NULL,
    PRIMARY KEY (trip_id, leg_id)
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
                    cursor.execute(_MULTI_CITY_SCHEMA)
                    # Existing installations predate edit-token protection.
                    # Keep this migration additive so shared links remain readable.
                    cursor.execute("ALTER TABLE trips ADD COLUMN IF NOT EXISTS owner_token_hash TEXT")
                    cursor.execute("ALTER TABLE trips ADD COLUMN IF NOT EXISTS previous_itinerary_json JSONB")
                    cursor.execute("ALTER TABLE multi_city_trips ADD COLUMN IF NOT EXISTS previous_trip_json JSONB")
            _schema_ready = True
            logger.info("Connected to Neon PostgreSQL; trips table is ready")
            return True
        except Exception as error:
            if settings.require_durable_storage:
                raise RuntimeError("Durable PostgreSQL storage could not be initialised") from error
            logger.warning("Neon setup failed; using in-memory trips: %s", error)
            return False


async def _ensure_schema() -> bool:
    if not settings.database_url:
        if settings.require_durable_storage:
            raise RuntimeError("DATABASE_URL is required when durable storage is enabled")
        return False
    return await asyncio.to_thread(_ensure_schema_sync)


async def ensure_durable_storage_ready() -> None:
    """Fail startup rather than serving a process-local database in production."""

    if settings.require_durable_storage and not await _ensure_schema():
        raise RuntimeError("Durable PostgreSQL storage is not ready")


def _write_multi_city_projections(cursor, trip_id: str, trip: Trip) -> None:
    """Keep queryable stay/leg/day projections beside the aggregate JSON."""
    projection_tables = (
        "multi_city_destination_stays",
        "multi_city_travel_legs",
        "multi_city_visits",
        "multi_city_itinerary_days",
        "multi_city_transport_selections",
    )
    for table in projection_tables:
        cursor.execute(f"DELETE FROM {table} WHERE trip_id = %s", (trip_id,))
    for stay in trip.destination_stays:
        cursor.execute(
            """INSERT INTO multi_city_destination_stays
            (trip_id, stay_id, position, city_json, arrival_date, departure_date, nights, notes, provenance_json)
            VALUES (%s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s::jsonb)""",
            (trip_id, stay.id, stay.position, json.dumps(stay.city.model_dump(mode="json")), stay.arrival_date,
             stay.departure_date, stay.nights, stay.notes, json.dumps(stay.provenance.model_dump(mode="json"))),
        )
    for position, leg in enumerate(trip.travel_legs):
        cursor.execute(
            """INSERT INTO multi_city_travel_legs
            (trip_id, leg_id, leg_position, origin_json, destination_json, travel_date, mode, selected_offer_json, alternatives_json, duration_minutes, fare, provenance_json)
            VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s::jsonb)""",
            (trip_id, leg.id, position, json.dumps(leg.origin.model_dump(mode="json")), json.dumps(leg.destination.model_dump(mode="json")),
             leg.date, leg.mode.value, json.dumps(leg.selected_offer.model_dump(mode="json")) if leg.selected_offer else None,
             json.dumps([option.model_dump(mode="json") for option in leg.alternatives]), leg.duration_minutes, leg.fare,
             json.dumps(leg.provenance.model_dump(mode="json"))),
        )
    for visit in trip.visits:
        cursor.execute(
            "INSERT INTO multi_city_visits (trip_id, visit_id, stay_id, visit_date, visit_json) VALUES (%s, %s, %s, %s, %s::jsonb)",
            (trip_id, visit.id, visit.stay_id, visit.date, json.dumps(visit.model_dump(mode="json"))),
        )
    for day in trip.itinerary_days:
        cursor.execute(
            "INSERT INTO multi_city_itinerary_days (trip_id, day_number, day_date, day_json) VALUES (%s, %s, %s, %s::jsonb)",
            (trip_id, day.day_number, day.date, json.dumps(day.model_dump(mode="json"))),
        )
    for selection in trip.transport_selections:
        cursor.execute(
            "INSERT INTO multi_city_transport_selections (trip_id, leg_id, selection_json) VALUES (%s, %s, %s::jsonb)",
            (trip_id, selection.leg_id, json.dumps(selection.model_dump(mode="json"))),
        )


async def save_trip(
    itinerary: Itinerary,
    owner_token_hash: str | None = None,
) -> str:
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
        except Exception as error:
            _fallback_or_raise("save_trip")
            logger.error("Neon save failed; using memory: %s", error)
    else:
        _fallback_or_raise("save_trip")
    _memory_store[trip_id] = {
        "itinerary": data,
        "previous_itinerary": None,
        "owner_token_hash": owner_token_hash,
        "created_at": created_at,
    }
    await record_trip_version(trip_id, TripKind.SINGLE, itinerary.model_dump(mode="json"), action="created")
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
            _fallback_or_raise("get_trip")
            logger.error("Neon read failed: %s", error)
    else:
        _fallback_or_raise("get_trip")
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
            _fallback_or_raise("get_trip_owner_token_hash")
            logger.error("Neon owner-token lookup failed; using memory: %s", error)
    else:
        _fallback_or_raise("get_trip_owner_token_hash")
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
        except Exception as error:
            _fallback_or_raise("update_trip")
            logger.error("Neon update failed; using memory: %s", error)
    else:
        _fallback_or_raise("update_trip")
    existing = _memory_store.get(itinerary.id, {})
    _memory_store[itinerary.id] = {
        "itinerary": data,
        "previous_itinerary": existing.get("itinerary"),
        "owner_token_hash": existing.get("owner_token_hash"),
        "created_at": datetime.utcnow().isoformat(),
    }
    await record_trip_version(itinerary.id, TripKind.SINGLE, itinerary.model_dump(mode="json"), action="updated")


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
                restored = await get_trip(trip_id)
                if restored:
                    await record_trip_version(trip_id, TripKind.SINGLE, restored.model_dump(mode="json"), action="undo")
                return restored
        except Exception as error:
            _fallback_or_raise("undo_trip")
            logger.error("Neon undo failed; using memory: %s", error)
    else:
        _fallback_or_raise("undo_trip")

    existing = _memory_store.get(trip_id)
    if not existing or not existing.get("previous_itinerary"):
        return None
    current = existing["itinerary"]
    existing["itinerary"] = existing["previous_itinerary"]
    existing["previous_itinerary"] = current
    restored = Itinerary.model_validate_json(existing["itinerary"])
    await record_trip_version(trip_id, TripKind.SINGLE, restored.model_dump(mode="json"), action="undo")
    return restored


async def save_multi_city_trip(
    trip: Trip,
    owner_token_hash: str | None = None,
) -> str:
    """Persist a canonical multi-city aggregate without changing single-trip JSON."""
    trip_id = str(uuid.uuid4())[:12]
    trip.id = trip_id
    data = trip.model_dump_json()
    created_at = datetime.utcnow().isoformat()
    if await _ensure_schema():
        try:
            def insert() -> None:
                with _connect() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            """INSERT INTO multi_city_trips
                            (id, trip_json, origin, start_date, end_date, budget, owner_token_hash, previous_trip_json, created_at)
                            VALUES (%s, %s::jsonb, %s, %s, %s, %s, %s, NULL, %s)""",
                            (trip_id, data, trip.origin.name, trip.start_date, trip.end_date,
                             trip.budget.total_estimated, owner_token_hash, created_at),
                        )
                        _write_multi_city_projections(cursor, trip_id, trip)
            await asyncio.to_thread(insert)
        except Exception as error:
            _fallback_or_raise("save_multi_city_trip")
            logger.error("Neon multi-city save failed; using memory: %s", error)
    else:
        _fallback_or_raise("save_multi_city_trip")
    _memory_multi_city_store[trip_id] = {
        "trip": data,
        "previous_trip": None,
        "owner_token_hash": owner_token_hash,
        "created_at": created_at,
    }
    await record_trip_version(trip_id, TripKind.MULTI_CITY, trip.model_dump(mode="json"), action="created")
    return trip_id


async def get_multi_city_trip(trip_id: str) -> Optional[Trip]:
    if await _ensure_schema():
        try:
            def fetch() -> Optional[str]:
                with _connect() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT trip_json::text FROM multi_city_trips WHERE id = %s", (trip_id,))
                        row = cursor.fetchone()
                        return row[0] if row else None
            data = await asyncio.to_thread(fetch)
            if data:
                return Trip.model_validate_json(data)
        except Exception as error:
            _fallback_or_raise("get_multi_city_trip")
            logger.error("Neon multi-city read failed: %s", error)
    else:
        _fallback_or_raise("get_multi_city_trip")
    cached = _memory_multi_city_store.get(trip_id)
    return Trip.model_validate_json(cached["trip"]) if cached else None


async def get_multi_city_trip_owner_token_hash(trip_id: str) -> Optional[str]:
    if await _ensure_schema():
        try:
            def fetch() -> Optional[str]:
                with _connect() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT owner_token_hash FROM multi_city_trips WHERE id = %s", (trip_id,))
                        row = cursor.fetchone()
                        return row[0] if row else None
            return await asyncio.to_thread(fetch)
        except Exception as error:
            _fallback_or_raise("get_multi_city_trip_owner_token_hash")
            logger.error("Neon multi-city owner-token lookup failed; using memory: %s", error)
    else:
        _fallback_or_raise("get_multi_city_trip_owner_token_hash")
    cached = _memory_multi_city_store.get(trip_id)
    return cached.get("owner_token_hash") if cached else None


async def update_multi_city_trip(trip: Trip) -> None:
    data = trip.model_dump_json()
    if await _ensure_schema():
        try:
            def update() -> None:
                with _connect() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "UPDATE multi_city_trips SET previous_trip_json = trip_json, trip_json = %s::jsonb, start_date = %s, end_date = %s, budget = %s WHERE id = %s",
                            (data, trip.start_date, trip.end_date, trip.budget.total_estimated, trip.id),
                        )
                        _write_multi_city_projections(cursor, trip.id, trip)
            await asyncio.to_thread(update)
        except Exception as error:
            _fallback_or_raise("update_multi_city_trip")
            logger.error("Neon multi-city update failed; using memory: %s", error)
    else:
        _fallback_or_raise("update_multi_city_trip")
    existing = _memory_multi_city_store.get(trip.id, {})
    _memory_multi_city_store[trip.id] = {
        "trip": data,
        "previous_trip": existing.get("trip"),
        "owner_token_hash": existing.get("owner_token_hash"),
        "created_at": existing.get("created_at", datetime.utcnow().isoformat()),
    }
    await record_trip_version(trip.id, TripKind.MULTI_CITY, trip.model_dump(mode="json"), action="updated")
