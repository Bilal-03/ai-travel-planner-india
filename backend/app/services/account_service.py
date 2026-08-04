"""Provider-neutral account service with Supabase JWT and local fallback support."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import secrets
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.config import settings
from app.models.account import (
    Account,
    AccountRegistrationRequest,
    AccountSession,
    PreferenceMemory,
    PreferenceMemoryUpdate,
)

logger = logging.getLogger(__name__)

_memory_accounts: dict[str, Account] = {}
_memory_sessions: dict[str, tuple[str, datetime]] = {}
_memory_preferences: dict[str, PreferenceMemory] = {}
_schema_ready = False
_schema_lock = threading.Lock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS yatra_accounts (
    id VARCHAR(36) PRIMARY KEY,
    email TEXT UNIQUE,
    display_name TEXT,
    is_anonymous BOOLEAN NOT NULL DEFAULT TRUE,
    memory_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS yatra_account_sessions (
    token_hash TEXT PRIMARY KEY,
    account_id VARCHAR(36) NOT NULL REFERENCES yatra_accounts(id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS yatra_account_preferences (
    account_id VARCHAR(36) PRIMARY KEY REFERENCES yatra_accounts(id) ON DELETE CASCADE,
    memory_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    preferred_transport TEXT,
    hotel_category TEXT,
    typical_budget_min INTEGER,
    typical_budget_max INTEGER,
    dietary_preference TEXT,
    travel_pace TEXT,
    accessibility_requirements TEXT,
    preferred_departure_times JSONB NOT NULL DEFAULT '[]'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


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
                    cursor.execute(_SCHEMA)
            _schema_ready = True
            return True
        except Exception as error:
            logger.warning("Account database setup failed; using in-memory accounts: %s", error)
            return False


async def _ensure_schema() -> bool:
    import asyncio

    return bool(settings.database_url) and await asyncio.to_thread(_ensure_schema_sync)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _secret() -> str:
    return settings.trip_job_secret or "yatraai-development-account-secret"


def _b64_json(payload: dict) -> str:
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(encoded).decode("ascii").rstrip("=")


def _unb64_json(value: str) -> dict:
    padded = value + "=" * (-len(value) % 4)
    return json.loads(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))


def _issue_local_token(account_id: str) -> tuple[str, datetime]:
    expires_at = _now() + timedelta(seconds=settings.account_session_ttl_seconds)
    payload = {"sub": account_id, "exp": int(expires_at.timestamp()), "nonce": secrets.token_urlsafe(12)}
    body = _b64_json(payload)
    signature = hmac.new(_secret().encode("utf-8"), body.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{body}.{signature}", expires_at


def _decode_local_token(token: str) -> tuple[str, datetime] | None:
    try:
        body, signature = token.split(".", 1)
        expected = hmac.new(_secret().encode("utf-8"), body.encode("ascii"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return None
        payload = _unb64_json(body)
        expires_at = datetime.fromtimestamp(int(payload["exp"]), timezone.utc)
        if expires_at <= _now() or not payload.get("sub"):
            return None
        return str(payload["sub"]), expires_at
    except (ValueError, KeyError, TypeError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def _decode_supabase_token(token: str) -> tuple[str, dict] | None:
    """Verify HS256 Supabase tokens when the managed provider is configured."""
    if not settings.supabase_jwt_secret:
        return None
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
        header = _unb64_json(header_b64)
        payload = _unb64_json(payload_b64)
        if header.get("alg") != "HS256":
            return None
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected = hmac.new(settings.supabase_jwt_secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        provided = base64.urlsafe_b64decode(signature_b64 + "=" * (-len(signature_b64) % 4))
        if not hmac.compare_digest(provided, expected):
            return None
        if datetime.fromtimestamp(int(payload["exp"]), timezone.utc) <= _now():
            return None
        subject = str(payload.get("sub") or "")
        return (subject, payload) if subject else None
    except (ValueError, KeyError, TypeError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _new_account(*, email: str | None, display_name: str | None, is_anonymous: bool) -> Account:
    return Account(
        id=str(uuid.uuid4()),
        email=email,
        display_name=display_name,
        is_anonymous=is_anonymous,
        memory_enabled=True,
    )


async def _persist_account(account: Account) -> None:
    if await _ensure_schema():
        try:
            import asyncio

            def persist() -> None:
                with _connect() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            """INSERT INTO yatra_accounts (id, email, display_name, is_anonymous, memory_enabled, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email, display_name = EXCLUDED.display_name,
                            is_anonymous = EXCLUDED.is_anonymous, memory_enabled = EXCLUDED.memory_enabled""",
                            (account.id, account.email, account.display_name, account.is_anonymous, account.memory_enabled, account.created_at),
                        )
            await asyncio.to_thread(persist)
        except Exception as error:
            logger.error("Account persistence failed; keeping memory copy: %s", error)
    _memory_accounts[account.id] = account


async def _persist_session(token: str, account_id: str, expires_at: datetime) -> None:
    digest = _token_hash(token)
    _memory_sessions[digest] = (account_id, expires_at)
    if await _ensure_schema():
        try:
            import asyncio

            def persist() -> None:
                with _connect() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "INSERT INTO yatra_account_sessions (token_hash, account_id, expires_at) VALUES (%s, %s, %s) ON CONFLICT (token_hash) DO UPDATE SET expires_at = EXCLUDED.expires_at",
                            (digest, account_id, expires_at),
                        )
            await asyncio.to_thread(persist)
        except Exception as error:
            logger.error("Account session persistence failed; keeping memory copy: %s", error)


async def _load_account(account_id: str) -> Account | None:
    account = _memory_accounts.get(account_id)
    if account:
        return account
    if await _ensure_schema():
        try:
            import asyncio

            def fetch():
                with _connect() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "SELECT id, email, display_name, is_anonymous, memory_enabled, created_at FROM yatra_accounts WHERE id = %s",
                            (account_id,),
                        )
                        return cursor.fetchone()
            row = await asyncio.to_thread(fetch)
            if row:
                account = Account(
                    id=row[0], email=row[1], display_name=row[2], is_anonymous=row[3],
                    memory_enabled=row[4], created_at=row[5],
                )
                _memory_accounts[account.id] = account
                return account
        except Exception as error:
            logger.error("Account lookup failed: %s", error)
    return None


async def _find_account_by_email(email: str) -> Account | None:
    normalized = email.strip().casefold()
    for account in _memory_accounts.values():
        if account.email and account.email.casefold() == normalized:
            return account
    if await _ensure_schema():
        try:
            import asyncio

            def fetch():
                with _connect() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "SELECT id, email, display_name, is_anonymous, memory_enabled, created_at FROM yatra_accounts WHERE lower(email) = lower(%s)",
                            (email,),
                        )
                        return cursor.fetchone()
            row = await asyncio.to_thread(fetch)
            if row:
                account = Account(id=row[0], email=row[1], display_name=row[2], is_anonymous=row[3], memory_enabled=row[4], created_at=row[5])
                _memory_accounts[account.id] = account
                return account
        except Exception as error:
            logger.error("Account email lookup failed: %s", error)
    return None


async def create_anonymous_session() -> AccountSession:
    account = _new_account(email=None, display_name=None, is_anonymous=True)
    await _persist_account(account)
    token, expires_at = _issue_local_token(account.id)
    await _persist_session(token, account.id, expires_at)
    return AccountSession(access_token=token, expires_at=expires_at, account=account)


async def register_account(
    request: AccountRegistrationRequest,
    existing_token: str | None = None,
) -> AccountSession:
    existing = await get_account_for_token(existing_token) if existing_token else None
    by_email = await _find_account_by_email(request.email)
    if by_email and (not existing or by_email.id != existing.id):
        raise ValueError("An account with that email already exists")
    account = existing or _new_account(email=request.email.strip(), display_name=request.display_name, is_anonymous=False)
    account.email = request.email.strip()
    account.display_name = request.display_name or account.display_name
    account.is_anonymous = False
    await _persist_account(account)
    token, expires_at = _issue_local_token(account.id)
    await _persist_session(token, account.id, expires_at)
    return AccountSession(access_token=token, expires_at=expires_at, account=account)


async def get_account_for_token(token: str | None) -> Account | None:
    if not token:
        return None
    local = _decode_local_token(token)
    if local:
        account_id, expires_at = local
        digest = _token_hash(token)
        session = _memory_sessions.get(digest)
        if session and session[1] <= _now():
            return None
        if await _ensure_schema() and not session:
            try:
                import asyncio

                def fetch():
                    with _connect() as connection:
                        with connection.cursor() as cursor:
                            cursor.execute(
                                "SELECT account_id, expires_at FROM yatra_account_sessions WHERE token_hash = %s",
                                (digest,),
                            )
                            return cursor.fetchone()
                row = await asyncio.to_thread(fetch)
                if not row or row[1] <= _now():
                    return None
            except Exception as error:
                logger.error("Account session lookup failed: %s", error)
                return None
        return await _load_account(account_id)

    external = _decode_supabase_token(token)
    if external:
        account_id, payload = external
        account = await _load_account(account_id)
        if account:
            return account
        account = Account(
            id=account_id,
            email=payload.get("email"),
            display_name=(payload.get("user_metadata") or {}).get("full_name"),
            is_anonymous=False,
        )
        await _persist_account(account)
        return account
    return None


async def get_preferences(account_id: str) -> PreferenceMemory:
    preference = _memory_preferences.get(account_id)
    if preference:
        return preference
    if await _ensure_schema():
        try:
            import asyncio

            def fetch():
                with _connect() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "SELECT memory_enabled, preferred_transport, hotel_category, typical_budget_min, typical_budget_max, dietary_preference, travel_pace, accessibility_requirements, preferred_departure_times, updated_at FROM yatra_account_preferences WHERE account_id = %s",
                            (account_id,),
                        )
                        return cursor.fetchone()
            row = await asyncio.to_thread(fetch)
            if row:
                value = PreferenceMemory(
                    memory_enabled=row[0], preferred_transport=row[1], hotel_category=row[2],
                    typical_budget_min=row[3], typical_budget_max=row[4], dietary_preference=row[5],
                    travel_pace=row[6], accessibility_requirements=row[7],
                    preferred_departure_times=row[8] or [], updated_at=row[9],
                )
                _memory_preferences[account_id] = value
                return value
        except Exception as error:
            logger.error("Preference lookup failed: %s", error)
    return PreferenceMemory(memory_enabled=True)


async def update_preferences(account_id: str, update: PreferenceMemoryUpdate) -> PreferenceMemory:
    current = await get_preferences(account_id)
    changes = update.model_dump(exclude_unset=True)
    if changes.get("memory_enabled") is False:
        current = PreferenceMemory(memory_enabled=False)
    else:
        current = current.model_copy(update=changes)
        current.updated_at = _now()
    _memory_preferences[account_id] = current
    account = await _load_account(account_id)
    if account:
        account.memory_enabled = current.memory_enabled
        await _persist_account(account)
    if await _ensure_schema():
        try:
            import asyncio

            def persist() -> None:
                with _connect() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            """INSERT INTO yatra_account_preferences
                            (account_id, memory_enabled, preferred_transport, hotel_category, typical_budget_min, typical_budget_max, dietary_preference, travel_pace, accessibility_requirements, preferred_departure_times, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                            ON CONFLICT (account_id) DO UPDATE SET memory_enabled = EXCLUDED.memory_enabled, preferred_transport = EXCLUDED.preferred_transport, hotel_category = EXCLUDED.hotel_category, typical_budget_min = EXCLUDED.typical_budget_min, typical_budget_max = EXCLUDED.typical_budget_max, dietary_preference = EXCLUDED.dietary_preference, travel_pace = EXCLUDED.travel_pace, accessibility_requirements = EXCLUDED.accessibility_requirements, preferred_departure_times = EXCLUDED.preferred_departure_times, updated_at = EXCLUDED.updated_at""",
                            (account_id, current.memory_enabled, current.preferred_transport.value if current.preferred_transport else None,
                             current.hotel_category.value if current.hotel_category else None, current.typical_budget_min,
                             current.typical_budget_max, current.dietary_preference.value if current.dietary_preference else None,
                             current.travel_pace.value if current.travel_pace else None, current.accessibility_requirements,
                             json.dumps(current.preferred_departure_times), current.updated_at),
                        )
            await asyncio.to_thread(persist)
        except Exception as error:
            logger.error("Preference persistence failed; keeping memory copy: %s", error)
    return current


async def delete_preferences(account_id: str) -> PreferenceMemory:
    _memory_preferences.pop(account_id, None)
    account = await _load_account(account_id)
    if account:
        account.memory_enabled = True
        await _persist_account(account)
    if await _ensure_schema():
        try:
            import asyncio

            def delete() -> None:
                with _connect() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute("DELETE FROM yatra_account_preferences WHERE account_id = %s", (account_id,))
            await asyncio.to_thread(delete)
        except Exception as error:
            logger.error("Preference delete failed: %s", error)
    return PreferenceMemory(memory_enabled=True)


async def delete_account(account_id: str) -> None:
    _memory_accounts.pop(account_id, None)
    _memory_preferences.pop(account_id, None)
    for digest, session in list(_memory_sessions.items()):
        if session[0] == account_id:
            _memory_sessions.pop(digest, None)
    if await _ensure_schema():
        try:
            import asyncio

            def delete() -> None:
                with _connect() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute("DELETE FROM yatra_accounts WHERE id = %s", (account_id,))
            await asyncio.to_thread(delete)
        except Exception as error:
            logger.error("Account delete failed: %s", error)
