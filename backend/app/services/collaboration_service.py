"""Durable collaboration, immutable version history, audit, and analytics storage."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import secrets
import threading
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from app.config import settings
from app.models.collaboration import (
    AnalyticsEventRequest,
    CollaborationRole,
    CollaboratorResponse,
    ShareLinkResponse,
    TripActivityResponse,
    TripKind,
    TripVersionResponse,
)

logger = logging.getLogger(__name__)

ALLOWED_ANALYTICS_EVENTS = {
    "planner_started",
    "planner_completed",
    "generation_started",
    "generation_completed",
    "generation_failed",
    "trip_shared",
    "trip_exported",
    "activity_replaced",
    "day_regenerated",
    "transport_selected",
    "provider_link_clicked",
}
_ALLOWED_METADATA_KEYS = {
    "kind",
    "source",
    "status",
    "provider",
    "freshness_status",
    "estimated_data",
    "invalid_itinerary",
    "accepted",
    "days",
    "cost_inr",
    "cost_usd",
    "duration_ms",
}

_schema_ready = False
_schema_lock = threading.Lock()
_memory_links: dict[str, dict[str, Any]] = {}
_memory_collaborators: dict[str, dict[str, Any]] = {}
_memory_versions: dict[tuple[str, str], list[dict[str, Any]]] = {}
_memory_activity: dict[tuple[str, str], list[dict[str, Any]]] = {}
_memory_analytics: list[dict[str, Any]] = []
_memory_audit: list[dict[str, Any]] = []
_memory_lock = threading.RLock()

_SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS itinerary_versions (
        id UUID PRIMARY KEY,
        trip_id VARCHAR(64) NOT NULL,
        kind TEXT NOT NULL CHECK (kind IN ('single', 'multi_city')),
        version INTEGER NOT NULL,
        action TEXT NOT NULL,
        actor_id VARCHAR(128),
        snapshot_json JSONB NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (trip_id, kind, version)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS trip_edits (
        id UUID PRIMARY KEY,
        trip_id VARCHAR(64) NOT NULL,
        kind TEXT NOT NULL CHECK (kind IN ('single', 'multi_city')),
        action TEXT NOT NULL,
        actor_id VARCHAR(128),
        version INTEGER,
        metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS share_links (
        id UUID PRIMARY KEY,
        trip_id VARCHAR(64) NOT NULL,
        kind TEXT NOT NULL CHECK (kind IN ('single', 'multi_city')),
        role TEXT NOT NULL CHECK (role IN ('editor', 'viewer')),
        token_hash TEXT NOT NULL UNIQUE,
        invite_email TEXT,
        created_by VARCHAR(128),
        expires_at TIMESTAMPTZ NOT NULL,
        revoked_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS collaborators (
        id UUID PRIMARY KEY,
        trip_id VARCHAR(64) NOT NULL,
        kind TEXT NOT NULL CHECK (kind IN ('single', 'multi_city')),
        email TEXT NOT NULL,
        role TEXT NOT NULL CHECK (role IN ('editor', 'viewer')),
        created_by VARCHAR(128),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (trip_id, kind, email)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS analytics_events (
        id UUID PRIMARY KEY,
        event_name TEXT NOT NULL,
        trip_id_hash TEXT,
        kind TEXT,
        duration_ms INTEGER,
        metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_logs (
        id UUID PRIMARY KEY,
        action TEXT NOT NULL,
        trip_id VARCHAR(64),
        actor_hash TEXT,
        metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS itinerary_versions_trip_idx ON itinerary_versions (trip_id, kind, version DESC)",
    "CREATE INDEX IF NOT EXISTS trip_edits_trip_idx ON trip_edits (trip_id, kind, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS analytics_events_name_idx ON analytics_events (event_name, created_at DESC)",
)


def _connect():
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
                    for statement in _SCHEMA_STATEMENTS:
                        cursor.execute(statement)
            _schema_ready = True
            return True
        except Exception as error:
            if settings.require_durable_storage:
                raise RuntimeError("Phase 7 collaboration storage could not be initialised") from error
            logger.warning("Collaboration storage unavailable; using local development memory: %s", error)
            return False


async def ensure_collaboration_storage_ready() -> None:
    if settings.require_durable_storage:
        if not settings.database_url:
            raise RuntimeError("DATABASE_URL is required for collaboration history in production")
        if not await asyncio.to_thread(_ensure_schema_sync):
            raise RuntimeError("Collaboration storage is not ready")


async def _db_ready() -> bool:
    if not settings.database_url:
        if settings.require_durable_storage:
            raise RuntimeError("DATABASE_URL is required for Phase 7 storage")
        return False
    return await asyncio.to_thread(_ensure_schema_sync)


def _fallback_or_raise(operation: str) -> None:
    if settings.require_durable_storage:
        raise RuntimeError(f"Durable collaboration storage is unavailable during {operation}")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash(value: str | None) -> str | None:
    if not value:
        return None
    return hashlib.sha256(f"{settings.analytics_hash_salt}:{value}".encode()).hexdigest()


def _clean_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for key, value in list(metadata.items())[:12]:
        if key not in _ALLOWED_METADATA_KEYS:
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            clean[key] = str(value)[:120] if isinstance(value, str) else value
    return clean


def _trip_key(trip_id: str, kind: TripKind) -> tuple[str, str]:
    return trip_id, kind.value


class VersionConflictError(ValueError):
    """Raised when a mutation was based on a stale itinerary revision."""

    def __init__(self, expected: int, current: int):
        self.expected = expected
        self.current = current
        super().__init__(f"Trip changed since version {expected}; current version is {current}.")


def _link_response(row: dict[str, Any], share_url: str) -> ShareLinkResponse:
    return ShareLinkResponse(
        id=row["id"],
        trip_id=row["trip_id"],
        kind=TripKind(row["kind"]),
        role=CollaborationRole(row["role"]),
        share_url=share_url,
        invite_email=row.get("invite_email"),
        expires_at=row["expires_at"],
        revoked_at=row.get("revoked_at"),
    )


async def create_share_link(
    trip_id: str,
    kind: TripKind,
    role: CollaborationRole,
    *,
    share_url: str,
    created_by: str | None = None,
    invite_email: str | None = None,
    expires_in_hours: int = 168,
) -> tuple[ShareLinkResponse, str]:
    if role == CollaborationRole.OWNER:
        raise ValueError("Share links can only grant editor or viewer access")
    raw_token = secrets.token_urlsafe(32)
    row: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "trip_id": trip_id,
        "kind": kind.value,
        "role": role.value,
        "token_hash": hashlib.sha256(raw_token.encode()).hexdigest(),
        "invite_email": invite_email.strip().casefold() if invite_email else None,
        "created_by": created_by,
        "expires_at": _now() + timedelta(hours=expires_in_hours),
        "revoked_at": None,
    }
    if await _db_ready():
        try:
            def insert() -> None:
                with _connect() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            """INSERT INTO share_links
                            (id, trip_id, kind, role, token_hash, invite_email, created_by, expires_at)
                            VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, %s)""",
                            (row["id"], trip_id, kind.value, role.value, row["token_hash"], row["invite_email"], created_by, row["expires_at"]),
                        )
            await asyncio.to_thread(insert)
        except Exception as error:
            _fallback_or_raise("create_share_link")
            logger.error("Share-link persistence failed; using memory: %s", error)
    else:
        _fallback_or_raise("create_share_link")
    with _memory_lock:
        _memory_links[row["token_hash"]] = row
    await record_audit("share_link_created", trip_id, created_by, {"kind": kind.value, "role": role.value})
    return _link_response(row, share_url), raw_token


async def resolve_share_token(raw_token: str, trip_id: str, kind: TripKind) -> CollaborationRole | None:
    if not raw_token or len(raw_token) > 256:
        return None
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    now = _now()
    row: dict[str, Any] | None = None
    if await _db_ready():
        try:
            def fetch() -> dict[str, Any] | None:
                with _connect() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "SELECT trip_id, kind, role, expires_at, revoked_at FROM share_links WHERE token_hash = %s",
                            (token_hash,),
                        )
                        value = cursor.fetchone()
                        if not value:
                            return None
                        return {"trip_id": value[0], "kind": value[1], "role": value[2], "expires_at": value[3], "revoked_at": value[4]}
            row = await asyncio.to_thread(fetch)
        except Exception as error:
            _fallback_or_raise("resolve_share_token")
            logger.error("Share-link lookup failed; using memory: %s", error)
    else:
        _fallback_or_raise("resolve_share_token")
    if row is None:
        with _memory_lock:
            row = _memory_links.get(token_hash)
    if not row or row.get("trip_id") != trip_id or row.get("kind") != kind.value:
        return None
    expires_at = row.get("expires_at")
    if row.get("revoked_at") or not isinstance(expires_at, datetime) or expires_at <= now:
        return None
    return CollaborationRole(row["role"])


async def list_share_links(trip_id: str, kind: TripKind, *, share_url_builder) -> list[ShareLinkResponse]:
    rows: list[dict[str, Any]] = []
    if await _db_ready():
        try:
            def fetch() -> list[dict[str, Any]]:
                with _connect() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "SELECT id::text, trip_id, kind, role, invite_email, expires_at, revoked_at FROM share_links WHERE trip_id = %s AND kind = %s ORDER BY created_at DESC",
                            (trip_id, kind.value),
                        )
                        return [
                            {"id": item[0], "trip_id": item[1], "kind": item[2], "role": item[3], "invite_email": item[4], "expires_at": item[5], "revoked_at": item[6]}
                            for item in cursor.fetchall()
                        ]
            rows = await asyncio.to_thread(fetch)
        except Exception as error:
            _fallback_or_raise("list_share_links")
            logger.error("Share-link listing failed; using memory: %s", error)
    else:
        _fallback_or_raise("list_share_links")
    if not rows:
        with _memory_lock:
            rows = [row for row in _memory_links.values() if row["trip_id"] == trip_id and row["kind"] == kind.value]
    return [_link_response(row, share_url_builder(row["id"])) for row in rows]


async def revoke_share_link(trip_id: str, kind: TripKind, link_id: str, actor_id: str | None = None) -> bool:
    revoked_at = _now()
    changed = False
    if await _db_ready():
        try:
            def revoke() -> bool:
                with _connect() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "UPDATE share_links SET revoked_at = %s WHERE id = %s::uuid AND trip_id = %s AND kind = %s AND revoked_at IS NULL",
                            (revoked_at, link_id, trip_id, kind.value),
                        )
                        return cursor.rowcount > 0
            changed = await asyncio.to_thread(revoke)
        except Exception as error:
            _fallback_or_raise("revoke_share_link")
            logger.error("Share-link revoke failed; using memory: %s", error)
    else:
        _fallback_or_raise("revoke_share_link")
    with _memory_lock:
        for row in _memory_links.values():
            if row["id"] == link_id and row["trip_id"] == trip_id and row["kind"] == kind.value and not row.get("revoked_at"):
                row["revoked_at"] = revoked_at
                changed = True
    if changed:
        await record_audit("share_link_revoked", trip_id, actor_id, {"kind": kind.value})
    return changed


async def add_collaborator(trip_id: str, kind: TripKind, email: str, role: CollaborationRole, created_by: str | None) -> CollaboratorResponse:
    if role == CollaborationRole.OWNER:
        raise ValueError("Owner is not an assignable collaborator role")
    normalized = email.strip().casefold()
    row = {"id": str(uuid.uuid4()), "trip_id": trip_id, "kind": kind.value, "email": normalized, "role": role.value, "created_at": _now()}
    if await _db_ready():
        try:
            def insert() -> None:
                with _connect() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            """INSERT INTO collaborators (id, trip_id, kind, email, role, created_by)
                            VALUES (%s::uuid, %s, %s, %s, %s, %s)
                            ON CONFLICT (trip_id, kind, email) DO UPDATE SET role = EXCLUDED.role""",
                            (row["id"], trip_id, kind.value, normalized, role.value, created_by),
                        )
            await asyncio.to_thread(insert)
        except Exception as error:
            _fallback_or_raise("add_collaborator")
            logger.error("Collaborator persistence failed; using memory: %s", error)
    else:
        _fallback_or_raise("add_collaborator")
    with _memory_lock:
        _memory_collaborators[f"{kind.value}:{trip_id}:{normalized}"] = row
    await record_audit("collaborator_invited", trip_id, created_by, {"kind": kind.value, "role": role.value})
    return CollaboratorResponse(**row)


async def list_collaborators(trip_id: str, kind: TripKind) -> list[CollaboratorResponse]:
    rows: list[dict[str, Any]] = []
    if await _db_ready():
        try:
            def fetch() -> list[dict[str, Any]]:
                with _connect() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "SELECT id::text, trip_id, kind, email, role, created_at FROM collaborators WHERE trip_id = %s AND kind = %s ORDER BY created_at",
                            (trip_id, kind.value),
                        )
                        return [{"id": item[0], "trip_id": item[1], "kind": item[2], "email": item[3], "role": item[4], "created_at": item[5]} for item in cursor.fetchall()]
            rows = await asyncio.to_thread(fetch)
        except Exception as error:
            _fallback_or_raise("list_collaborators")
            logger.error("Collaborator listing failed; using memory: %s", error)
    else:
        _fallback_or_raise("list_collaborators")
    if not rows:
        with _memory_lock:
            rows = [row for row in _memory_collaborators.values() if row["trip_id"] == trip_id and row["kind"] == kind.value]
    return [CollaboratorResponse(id=row["id"], trip_id=row["trip_id"], kind=TripKind(row["kind"]), email=row["email"], role=CollaborationRole(row["role"]), created_at=row["created_at"]) for row in rows]


async def record_trip_version(trip_id: str, kind: TripKind, snapshot: dict[str, Any], *, action: str, actor_id: str | None = None) -> int:
    version = 1
    if await _db_ready():
        try:
            def insert() -> int:
                with _connect() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT COALESCE(MAX(version), 0) + 1 FROM itinerary_versions WHERE trip_id = %s AND kind = %s", (trip_id, kind.value))
                        next_version = int(cursor.fetchone()[0])
                        cursor.execute(
                            "INSERT INTO itinerary_versions (id, trip_id, kind, version, action, actor_id, snapshot_json) VALUES (%s::uuid, %s, %s, %s, %s, %s, %s::jsonb)",
                            (str(uuid.uuid4()), trip_id, kind.value, next_version, action, actor_id, json.dumps(snapshot, default=str)),
                        )
                        return next_version
            version = await asyncio.to_thread(insert)
        except Exception as error:
            _fallback_or_raise("record_trip_version")
            logger.error("Version persistence failed; using memory: %s", error)
    else:
        _fallback_or_raise("record_trip_version")
    if not settings.require_durable_storage or not settings.database_url:
        with _memory_lock:
            versions = _memory_versions.setdefault(_trip_key(trip_id, kind), [])
            version = len(versions) + 1
            row = {"id": str(uuid.uuid4()), "trip_id": trip_id, "kind": kind.value, "version": version, "action": action, "actor_id": actor_id, "snapshot": snapshot, "created_at": _now()}
            versions.append(row)
    await record_activity(trip_id, kind, action, actor_id=actor_id, version=version)
    return version


async def current_version(trip_id: str, kind: TripKind) -> int:
    if await _db_ready():
        try:
            def fetch() -> int:
                with _connect() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT COALESCE(MAX(version), 0) FROM itinerary_versions WHERE trip_id = %s AND kind = %s", (trip_id, kind.value))
                        return int(cursor.fetchone()[0])
            return await asyncio.to_thread(fetch)
        except Exception as error:
            _fallback_or_raise("current_version")
            logger.error("Version lookup failed; using memory: %s", error)
    else:
        _fallback_or_raise("current_version")
    with _memory_lock:
        return len(_memory_versions.get(_trip_key(trip_id, kind), []))


async def assert_version(trip_id: str, kind: TripKind, if_match: str | None) -> None:
    """Apply an optional HTTP If-Match check without breaking old clients."""

    if if_match is None:
        return
    normalized = if_match.strip().removeprefix("W/").strip('"')
    try:
        expected = int(normalized)
    except ValueError as error:
        raise ValueError("If-Match must contain a numeric itinerary version") from error
    actual = await current_version(trip_id, kind)
    if expected != actual:
        raise VersionConflictError(expected, actual)


async def list_versions(trip_id: str, kind: TripKind, *, include_snapshot: bool = False) -> list[TripVersionResponse]:
    rows: list[dict[str, Any]] = []
    if await _db_ready():
        try:
            def fetch() -> list[dict[str, Any]]:
                with _connect() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "SELECT id::text, trip_id, kind, version, action, actor_id, created_at, snapshot_json FROM itinerary_versions WHERE trip_id = %s AND kind = %s ORDER BY version DESC",
                            (trip_id, kind.value),
                        )
                        return [{"id": item[0], "trip_id": item[1], "kind": item[2], "version": item[3], "action": item[4], "actor_id": item[5], "created_at": item[6], "snapshot": item[7] if include_snapshot else None} for item in cursor.fetchall()]
            rows = await asyncio.to_thread(fetch)
        except Exception as error:
            _fallback_or_raise("list_versions")
            logger.error("Version history lookup failed; using memory: %s", error)
    else:
        _fallback_or_raise("list_versions")
    if not rows:
        with _memory_lock:
            rows = list(reversed(_memory_versions.get(_trip_key(trip_id, kind), [])))
        if not include_snapshot:
            rows = [{**row, "snapshot": None} for row in rows]
    return [TripVersionResponse(id=row["id"], trip_id=row["trip_id"], kind=TripKind(row["kind"]), version=row["version"], action=row["action"], actor_id=row.get("actor_id"), created_at=row["created_at"], snapshot=row.get("snapshot")) for row in rows]


async def record_activity(trip_id: str, kind: TripKind, action: str, *, actor_id: str | None = None, version: int | None = None, metadata: dict[str, Any] | None = None) -> None:
    clean = _clean_metadata(metadata or {})
    row = {"id": str(uuid.uuid4()), "trip_id": trip_id, "kind": kind.value, "action": action, "actor_id": actor_id, "version": version, "metadata": clean, "created_at": _now()}
    if await _db_ready():
        try:
            def insert() -> None:
                with _connect() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "INSERT INTO trip_edits (id, trip_id, kind, action, actor_id, version, metadata_json) VALUES (%s::uuid, %s, %s, %s, %s, %s, %s::jsonb)",
                            (row["id"], trip_id, kind.value, action, actor_id, version, json.dumps(clean)),
                        )
            await asyncio.to_thread(insert)
        except Exception as error:
            _fallback_or_raise("record_activity")
            logger.error("Activity persistence failed; using memory: %s", error)
    else:
        _fallback_or_raise("record_activity")
    if not settings.require_durable_storage or not settings.database_url:
        with _memory_lock:
            _memory_activity.setdefault(_trip_key(trip_id, kind), []).append(row)


async def list_activity(trip_id: str, kind: TripKind, limit: int = 100) -> list[TripActivityResponse]:
    rows: list[dict[str, Any]] = []
    if await _db_ready():
        try:
            def fetch() -> list[dict[str, Any]]:
                with _connect() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "SELECT id::text, trip_id, kind, action, actor_id, version, metadata_json, created_at FROM trip_edits WHERE trip_id = %s AND kind = %s ORDER BY created_at DESC LIMIT %s",
                            (trip_id, kind.value, limit),
                        )
                        return [{"id": item[0], "trip_id": item[1], "kind": item[2], "action": item[3], "actor_id": item[4], "version": item[5], "metadata": item[6] or {}, "created_at": item[7]} for item in cursor.fetchall()]
            rows = await asyncio.to_thread(fetch)
        except Exception as error:
            _fallback_or_raise("list_activity")
            logger.error("Activity history lookup failed; using memory: %s", error)
    else:
        _fallback_or_raise("list_activity")
    if not rows:
        with _memory_lock:
            rows = list(reversed(_memory_activity.get(_trip_key(trip_id, kind), [])))[:limit]
    return [TripActivityResponse(id=row["id"], trip_id=row["trip_id"], kind=TripKind(row["kind"]), action=row["action"], actor_id=row.get("actor_id"), version=row.get("version"), metadata=row.get("metadata", {}), created_at=row["created_at"]) for row in rows]


async def record_audit(action: str, trip_id: str | None, actor_id: str | None, metadata: dict[str, Any] | None = None) -> None:
    clean = _clean_metadata(metadata or {})
    row = {"id": str(uuid.uuid4()), "action": action, "trip_id": trip_id, "actor_hash": _hash(actor_id), "metadata": clean, "created_at": _now()}
    if await _db_ready():
        try:
            def insert() -> None:
                with _connect() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute("INSERT INTO audit_logs (id, action, trip_id, actor_hash, metadata_json) VALUES (%s::uuid, %s, %s, %s, %s::jsonb)", (row["id"], action, trip_id, row["actor_hash"], json.dumps(clean)))
            await asyncio.to_thread(insert)
        except Exception as error:
            _fallback_or_raise("record_audit")
            logger.error("Audit log persistence failed; using memory: %s", error)
    else:
        _fallback_or_raise("record_audit")
    if not settings.require_durable_storage or not settings.database_url:
        with _memory_lock:
            _memory_audit.append(row)


async def record_analytics(event: AnalyticsEventRequest, *, client_id: str | None = None) -> None:
    if event.event not in ALLOWED_ANALYTICS_EVENTS:
        raise ValueError("Unsupported analytics event")
    clean = _clean_metadata(event.metadata)
    if event.kind:
        clean.setdefault("kind", event.kind.value)
    row = {
        "id": str(uuid.uuid4()),
        "event_name": event.event,
        "trip_id_hash": _hash(event.trip_id),
        "kind": event.kind.value if event.kind else None,
        "duration_ms": event.duration_ms,
        "metadata": clean,
        "created_at": _now(),
    }
    if await _db_ready():
        try:
            def insert() -> None:
                with _connect() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute("INSERT INTO analytics_events (id, event_name, trip_id_hash, kind, duration_ms, metadata_json) VALUES (%s::uuid, %s, %s, %s, %s, %s::jsonb)", (row["id"], event.event, row["trip_id_hash"], row["kind"], event.duration_ms, json.dumps(clean)))
            await asyncio.to_thread(insert)
        except Exception as error:
            _fallback_or_raise("record_analytics")
            logger.error("Analytics persistence failed; using memory: %s", error)
    else:
        _fallback_or_raise("record_analytics")
    if not settings.require_durable_storage or not settings.database_url:
        with _memory_lock:
            _memory_analytics.append(row)


async def analytics_summary() -> dict[str, Any]:
    rows: list[dict[str, Any]]
    if await _db_ready():
        try:
            def fetch() -> list[dict[str, Any]]:
                with _connect() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT event_name, duration_ms, metadata_json FROM analytics_events WHERE created_at >= NOW() - INTERVAL '30 days'")
                        return [{"event_name": item[0], "duration_ms": item[1], "metadata": item[2] or {}} for item in cursor.fetchall()]
            rows = await asyncio.to_thread(fetch)
        except Exception as error:
            _fallback_or_raise("analytics_summary")
            logger.error("Analytics summary lookup failed; using memory: %s", error)
            rows = []
    else:
        _fallback_or_raise("analytics_summary")
        with _memory_lock:
            rows = list(_memory_analytics)
    counts = Counter(row["event_name"] for row in rows)
    completed = counts["generation_completed"]
    failed = counts["generation_failed"]
    started = counts["planner_started"]
    durations = [row["duration_ms"] for row in rows if row.get("event_name") == "generation_completed" and isinstance(row.get("duration_ms"), int)]
    estimated = sum(1 for row in rows if row.get("metadata", {}).get("estimated_data") is True or row.get("metadata", {}).get("estimated_data") == "true")
    freshness = Counter(str(row.get("metadata", {}).get("freshness_status")) for row in rows if row.get("metadata", {}).get("freshness_status"))
    return {
        "window_days": 30,
        "events": dict(counts),
        "planner_completion_rate": round(completed / started, 4) if started else None,
        "generation_success_rate": round(completed / (completed + failed), 4) if completed + failed else None,
        "average_generation_time_ms": round(sum(durations) / len(durations)) if durations else None,
        "refinement_acceptance": round((counts["activity_replaced"] + counts["day_regenerated"] + counts["transport_selected"]) / max(1, completed), 4),
        "share_rate": round(counts["trip_shared"] / max(1, completed), 4),
        "export_rate": round(counts["trip_exported"] / max(1, completed), 4),
        "estimated_data_usage": round(estimated / max(1, completed), 4),
        "provider_freshness": dict(freshness),
        "invalid_itinerary_rate": round(sum(1 for row in rows if row.get("metadata", {}).get("invalid_itinerary") in {True, "true"}) / max(1, completed), 4),
        "cost_per_completed_trip": round(sum(float(row.get("metadata", {}).get("cost_inr", 0) or 0) for row in rows) / max(1, completed), 2),
    }
