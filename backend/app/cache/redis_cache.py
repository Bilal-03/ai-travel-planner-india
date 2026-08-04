"""
Caching layer — Upstash Redis when available, in-memory dict fallback.
Decorator-based caching with configurable TTL for each external API.
"""

import json
import hashlib
import logging
import threading
import time
from functools import wraps
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── In-memory fallback cache ──────────────────────────────────────────

_memory_cache: dict[str, tuple[Any, float]] = {}  # key → (value, expire_timestamp)
_memory_lists: dict[str, list[str]] = {}
_memory_list_expiry: dict[str, float] = {}
_memory_counters: dict[str, tuple[int, float]] = {}
_memory_lock = threading.RLock()


class CacheClient:
    """Unified cache interface — Redis or in-memory."""

    def __init__(self):
        self._redis = None
        self._try_connect_redis()

    def _try_connect_redis(self):
        """Attempt to connect to Upstash Redis. Fall back silently."""
        try:
            from app.config import settings

            if settings.upstash_redis_url and settings.upstash_redis_token:
                import redis as redis_lib

                self._redis = redis_lib.from_url(
                    settings.upstash_redis_url,
                    password=settings.upstash_redis_token,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5,
                )
                self._redis.ping()
                logger.info("✅ Connected to Upstash Redis")
            else:
                logger.info("ℹ️  No Redis config — using in-memory cache")
        except Exception as e:
            logger.warning(f"⚠️  Redis connection failed, using in-memory cache: {e}")
            self._redis = None

    @property
    def is_distributed(self) -> bool:
        """Whether this client is backed by Redis rather than process memory."""

        return self._redis is not None

    def health(self) -> str:
        """Return a small health label suitable for readiness responses."""

        return "redis" if self.is_distributed else "in_memory"

    def get(self, key: str) -> Optional[str]:
        if self._redis:
            try:
                return self._redis.get(key)
            except Exception:
                pass

        # In-memory fallback
        if key in _memory_cache:
            value, expires = _memory_cache[key]
            if time.time() < expires:
                return value
            del _memory_cache[key]
        return None

    def set_if_absent(self, key: str, value: str, ttl_seconds: int = 3600) -> bool:
        """Set a value only when the key does not already exist."""

        if self._redis:
            try:
                return bool(self._redis.set(key, value, ex=ttl_seconds, nx=True))
            except Exception:
                pass

        with _memory_lock:
            existing = _memory_cache.get(key)
            if existing and time.time() < existing[1]:
                return False
            _memory_cache[key] = (value, time.time() + ttl_seconds)
            return True

    def set(self, key: str, value: str, ttl_seconds: int = 3600):
        if self._redis:
            try:
                self._redis.setex(key, ttl_seconds, value)
                return
            except Exception:
                pass

        # In-memory fallback
        _memory_cache[key] = (value, time.time() + ttl_seconds)

    def delete(self, key: str):
        if self._redis:
            try:
                self._redis.delete(key)
                return
            except Exception:
                pass
        with _memory_lock:
            _memory_cache.pop(key, None)
            _memory_lists.pop(key, None)
            _memory_list_expiry.pop(key, None)
            _memory_counters.pop(key, None)

    def increment(self, key: str, ttl_seconds: int = 3600, *, require_distributed: bool = False) -> int:
        """Increment a counter and apply a TTL when it is first created.

        Rate-limit callers can require Redis explicitly so a mid-request Redis
        outage cannot silently turn a distributed guard into a per-process one.
        """

        if self._redis:
            try:
                value = int(self._redis.incr(key))
                if value == 1:
                    self._redis.expire(key, ttl_seconds)
                return value
            except Exception as error:
                if require_distributed:
                    raise RuntimeError("Redis is unavailable for a distributed counter") from error

        if require_distributed:
            raise RuntimeError("A distributed Redis counter is required")

        with _memory_lock:
            current = _memory_counters.get(key)
            now = time.time()
            if not current or now >= current[1]:
                value = 1
            else:
                value = current[0] + 1
            _memory_counters[key] = (value, now + ttl_seconds)
            return value

    def list_push(self, key: str, value: str, ttl_seconds: int = 3600) -> int:
        """Append to a Redis list or its process-local equivalent."""

        if self._redis:
            try:
                pipe = self._redis.pipeline(transaction=True)
                pipe.rpush(key, value)
                pipe.expire(key, ttl_seconds)
                result = pipe.execute()
                return int(result[0])
            except Exception:
                pass

        with _memory_lock:
            _memory_lists.setdefault(key, []).append(value)
            _memory_list_expiry[key] = time.time() + ttl_seconds
            return len(_memory_lists[key])

    def list_range(self, key: str, start: int = 0, end: int = -1) -> list[str]:
        """Read a list range for replay or pending-job recovery."""

        if self._redis:
            try:
                return list(self._redis.lrange(key, start, end))
            except Exception:
                pass

        with _memory_lock:
            expires = _memory_list_expiry.get(key)
            if expires and time.time() >= expires:
                _memory_lists.pop(key, None)
                _memory_list_expiry.pop(key, None)
                return []
            values = _memory_lists.get(key, [])
            if end == -1:
                return list(values[start:])
            return list(values[start:end + 1])

    def list_pop_left(self, key: str) -> Optional[str]:
        """Pop one queue item without blocking the event loop."""

        if self._redis:
            try:
                return self._redis.lpop(key)
            except Exception:
                pass

        with _memory_lock:
            values = _memory_lists.get(key, [])
            if not values:
                return None
            return values.pop(0)


# ── Singleton ─────────────────────────────────────────────────────────

_cache_client: Optional[CacheClient] = None


def get_cache() -> CacheClient:
    global _cache_client
    if _cache_client is None:
        _cache_client = CacheClient()
    return _cache_client


# ── Decorator ─────────────────────────────────────────────────────────

def cached(prefix: str, ttl_seconds: int = 3600):
    """
    Decorator that caches function results.

    Usage:
        @cached("geocode", ttl_seconds=86400 * 30)
        async def geocode_city(city: str) -> dict:
            ...
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key from function args
            key_data = f"{prefix}:{args}:{sorted(kwargs.items())}"
            cache_key = f"travel:{prefix}:{hashlib.md5(key_data.encode()).hexdigest()}"

            cache = get_cache()
            hit = cache.get(cache_key)
            if hit:
                logger.debug(f"Cache HIT: {cache_key}")
                return json.loads(hit)

            logger.debug(f"Cache MISS: {cache_key}")
            result = await func(*args, **kwargs)

            if result is not None:
                try:
                    cache.set(cache_key, json.dumps(result, default=str), ttl_seconds)
                except (TypeError, ValueError) as e:
                    logger.warning(f"Failed to cache result for {cache_key}: {e}")

            return result

        return wrapper

    return decorator
